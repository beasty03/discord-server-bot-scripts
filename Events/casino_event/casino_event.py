import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import json
import time
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('ce_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

_hr_spec = _ilu.spec_from_file_location('hr_variables', Path(__file__).parent.parent.parent / 'Casino' / 'horseracing' / 'variables.py')
_hr_var = _ilu.module_from_spec(_hr_spec)
_hr_spec.loader.exec_module(_hr_var)

from forge_db import ForgeDB
from utils.config_loader import load_config, save_config

log = logging.getLogger("launcher")

_SETTINGS_FILE = Path(__file__).parent / "casino_settings.json"


def _load_settings() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            return json.loads(_SETTINGS_FILE.read_text("utf-8"))
        except Exception:
            pass
    return {}


def _save_settings(data: dict):
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2), "utf-8")

def _house_tx(db, bot_uid: str, gid: str, amount: int, tx_type: str):
    db.ensure_user(bot_uid, gid, "House")
    db.update_balance(bot_uid, gid, amount, tx_type)

def _record_event_stats(db, uid: str, gid: str, game_type: str, won: bool | None):
    """won=True → win, won=False → loss, won=None → refund (joins only, no win/loss)."""
    db.execute(
        """INSERT INTO casino_event_stats
               (user_id, guild_id, game_type, events_joined, events_won, events_lost)
           VALUES (?, ?, ?, 1, ?, ?)
           ON CONFLICT(user_id, guild_id, game_type) DO UPDATE SET
               events_joined = events_joined + 1,
               events_won    = events_won    + excluded.events_won,
               events_lost   = events_lost   + excluded.events_lost""",
        (uid, gid, game_type, 1 if won is True else 0, 1 if won is False else 0),
    )

# ============================================================================
# INLINE GAME RESOLVERS
# participants: dict[uid -> {"amount": int, "bet": any}]
# Resolvers return (summary_str, [(uid, delta_str, emoji, bet_label), ...])
# Balance was already deducted at join time; resolvers only ADD winnings.
# ============================================================================

# ── Horse racing data (mirrors Casino/horseracing/horseracing.py) ─────────────
_HORSES = _hr_var.HORSES

def _hr_winner() -> int:
    roll = random.randint(1, 100)
    cumul = 0
    for h in _HORSES:
        cumul += h["chance"]
        if roll <= cumul:
            return h["id"]
    return _HORSES[-1]["id"]

# ── Roulette data ─────────────────────────────────────────────────────────────
_RED = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}

def _roulette_color(n: int) -> str:
    return "green" if n == 0 else ("red" if n in _RED else "black")

def _roulette_check(result: int, bet: str) -> tuple[bool, float]:
    c = _roulette_color(result)
    match bet:
        case "red":   return c == "red",                       2.0
        case "black": return c == "black",                     2.0
        case "odd":   return result != 0 and result % 2 == 1,  2.0
        case "even":  return result != 0 and result % 2 == 0,  2.0
    if isinstance(bet, str) and bet.startswith("number:"):
        return result == int(bet.split(":")[1]), 36.0
    return False, 0.0

def _display_bet(bet) -> str:
    if isinstance(bet, int) and 1 <= bet <= 6:
        h = _HORSES[bet - 1]
        return f"{h['emoji']} {h['name']}"
    if not isinstance(bet, str) or not bet:
        return ""
    if bet.startswith("number:"):
        return f"🎯 {bet.split(':')[1]}"
    return bet

def resolve_roulette(participants: dict, db, gid: str, dm_mult: float = 1.0, bot_uid: str = "", prize_pool: int = 0):
    result = random.randint(0, 36)
    emoji  = {"green": "🟢", "red": "🔴", "black": "⚫"}[_roulette_color(result)]
    rows   = []
    for uid, data in participants.items():
        amount = data["amount"]
        bet    = data["bet"]
        won, mult = _roulette_check(result, bet)
        if won:
            payout = int(amount * mult)
            if dm_mult > 1.0:
                payout = amount + int((payout - amount) * dm_mult)
            db.update_balance(uid, gid, payout, 'event_win')
            if bot_uid:
                _house_tx(db, bot_uid, gid, -payout, 'house_payout')
            rows.append((uid, f"+{payout:,}", "✅", bet))
        else:
            rows.append((uid, f"-{amount:,}", "❌", bet))
    return f"{emoji} Ball landed on **{result}**", rows


def resolve_gamble(participants: dict, db, gid: str, dm_mult: float = 1.0, bot_uid: str = "", prize_pool: int = 0):
    winner_uids = [uid for uid, _ in participants.items() if random.random() < var.GAMBLE_WIN_CHANCE / 100]
    n_winners   = len(winner_uids)
    rows        = []
    for uid, data in participants.items():
        if uid in winner_uids and n_winners:
            share = int(prize_pool / n_winners)
            if dm_mult > 1.0:
                share = int(share * dm_mult)
            db.update_balance(uid, gid, share, 'event_win')
            if bot_uid:
                _house_tx(db, bot_uid, gid, -share, 'house_payout')
            rows.append((uid, f"+{share:,}", "✅", ""))
        else:
            rows.append((uid, f"-{data['amount']:,}", "❌", ""))
    return "🎲 Dice rolled!", rows


_BRANK = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
def _bval(r): return 1 if r == "A" else 0 if r in ("10","J","Q","K") else int(r)
def _bhand(): return sum(_bval(random.choice(_BRANK)) for _ in range(2)) % 10

def resolve_baccarat(participants: dict, db, gid: str, dm_mult: float = 1.0, bot_uid: str = "", prize_pool: int = 0):
    pt      = _bhand()
    bt      = _bhand()
    outcome = "player" if pt > bt else ("banker" if bt > pt else "tie")
    mult    = {"player": 2.0, "banker": 1.95, "tie": 9.0}
    rows    = []
    for uid, data in participants.items():
        amount = data["amount"]
        bet    = data["bet"]
        if bet == outcome:
            payout = int(amount * mult[bet])
            if dm_mult > 1.0:
                payout = amount + int((payout - amount) * dm_mult)
            db.update_balance(uid, gid, payout, 'event_win')
            if bot_uid:
                _house_tx(db, bot_uid, gid, -payout, 'house_payout')
            rows.append((uid, f"+{payout:,}", "✅", bet))
        elif outcome == "tie" and bet != "tie":
            db.update_balance(uid, gid, amount, 'refund')
            if bot_uid:
                _house_tx(db, bot_uid, gid, -amount, 'house_refund')
            rows.append((uid, "refund", "↩️", bet))
        else:
            rows.append((uid, f"-{amount:,}", "❌", bet))
    summary = f"👤 Player **{pt}** vs 🏦 Banker **{bt}** → {outcome.capitalize()} wins!"
    return summary, rows


def resolve_horseracing(participants: dict, db, gid: str, dm_mult: float = 1.0, bot_uid: str = "", prize_pool: int = 0):
    winner_id = _hr_winner()
    winner    = _HORSES[winner_id - 1]
    rows      = []
    for uid, data in participants.items():
        amount = data["amount"]
        bet    = data["bet"]
        h      = _HORSES[bet - 1] if isinstance(bet, int) and 1 <= bet <= 6 else winner
        if bet == winner_id:
            payout = amount * winner["odds"]
            if dm_mult > 1.0:
                payout = amount + int((payout - amount) * dm_mult)
            db.update_balance(uid, gid, payout, 'event_win')
            if bot_uid:
                _house_tx(db, bot_uid, gid, -payout, 'house_payout')
            rows.append((uid, f"+{payout:,}", "✅", f"{winner['emoji']} {winner['name']}"))
        else:
            rows.append((uid, f"-{amount:,}", "❌", f"{h['emoji']} {h['name']}"))
    return f"🏆 **{winner['emoji']} {winner['name']}** wins the race!", rows


RESOLVERS = {
    "roulette":    resolve_roulette,
    "gamble":      resolve_gamble,
    "baccarat":    resolve_baccarat,
    "horseracing": resolve_horseracing,
}

# ============================================================================
# BET-SELECTION VIEWS  (ephemeral, shown after /join for games with choices)
# ============================================================================

class _BetView(discord.ui.View):
    def __init__(self, participants: dict, uid: str, timeout: float):
        super().__init__(timeout=timeout)
        self.participants = participants
        self.uid          = uid

    async def _pick(self, interaction: discord.Interaction, bet):
        self.participants[self.uid]["bet"] = bet
        for item in self.children:
            item.disabled = True
        if isinstance(bet, int) and 1 <= bet <= 6:
            h       = _HORSES[bet - 1]
            display = f"{h['emoji']} {h['name']}"
        else:
            display = str(bet)
        await interaction.response.edit_message(
            content=f"✅ Bet updated to **{display}**!", view=self,
        )
        self.stop()


class _RouletteNumberModal(discord.ui.Modal, title="Straight Up Number Bet"):
    number_input = discord.ui.TextInput(
        label="Pick a number (0–36)",
        placeholder="e.g. 17",
        min_length=1,
        max_length=2,
    )

    def __init__(self, view: "_BetView"):
        super().__init__()
        self._view = view

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.number_input.value.strip()
        if not raw.isdigit():
            await interaction.response.send_message(
                "Please enter a whole number between 0 and 36.", ephemeral=True
            )
            return
        n = int(raw)
        if not 0 <= n <= 36:
            await interaction.response.send_message(
                "Number must be between 0 and 36.", ephemeral=True
            )
            return
        self._view.participants[self._view.uid]["bet"] = f"number:{n}"
        self._view.stop()
        await interaction.response.send_message(
            f"✅ Straight Up bet set to **🎯 {n}** (35:1 payout)!", ephemeral=True
        )


class RouletteBetView(_BetView):
    @discord.ui.button(label="🔴 Red",             style=discord.ButtonStyle.danger,    row=0)
    async def red(self,         i: discord.Interaction, _b): await self._pick(i, "red")
    @discord.ui.button(label="⚫ Black",            style=discord.ButtonStyle.secondary, row=0)
    async def black(self,       i: discord.Interaction, _b): await self._pick(i, "black")
    @discord.ui.button(label="Odd",                 style=discord.ButtonStyle.primary,   row=1)
    async def odd(self,         i: discord.Interaction, _b): await self._pick(i, "odd")
    @discord.ui.button(label="Even",                style=discord.ButtonStyle.primary,   row=1)
    async def even(self,        i: discord.Interaction, _b): await self._pick(i, "even")
    @discord.ui.button(label="🎯 Straight Up (35:1)", style=discord.ButtonStyle.success, row=2)
    async def straight_up(self, i: discord.Interaction, _b):
        await i.response.send_modal(_RouletteNumberModal(self))


class BaccaratBetView(_BetView):
    @discord.ui.button(label="👤 Player", style=discord.ButtonStyle.primary, row=0)
    async def player(self, i: discord.Interaction, _b): await self._pick(i, "player")
    @discord.ui.button(label="🏦 Banker", style=discord.ButtonStyle.danger,  row=0)
    async def banker(self, i: discord.Interaction, _b): await self._pick(i, "banker")
    @discord.ui.button(label="🤝 Tie",    style=discord.ButtonStyle.success, row=0)
    async def tie(self,    i: discord.Interaction, _b): await self._pick(i, "tie")


class HorseRacingEventView(_BetView):
    @discord.ui.button(label="⚡ Thunder  (2:1)",  style=discord.ButtonStyle.primary,   row=0)
    async def h1(self, i, _): await self._pick(i, 1)
    @discord.ui.button(label="💧 Splash   (3:1)",  style=discord.ButtonStyle.primary,   row=0)
    async def h2(self, i, _): await self._pick(i, 2)
    @discord.ui.button(label="🔥 Blaze    (5:1)",  style=discord.ButtonStyle.primary,   row=0)
    async def h3(self, i, _): await self._pick(i, 3)
    @discord.ui.button(label="🍀 Lucky    (7:1)",  style=discord.ButtonStyle.success,   row=1)
    async def h4(self, i, _): await self._pick(i, 4)
    @discord.ui.button(label="🌙 Midnight (9:1)",  style=discord.ButtonStyle.success,   row=1)
    async def h5(self, i, _): await self._pick(i, 5)
    @discord.ui.button(label="⭐ Comet    (14:1)", style=discord.ButtonStyle.secondary, row=1)
    async def h6(self, i, _): await self._pick(i, 6)


_BET_VIEWS: dict[str, type[_BetView]] = {
    "roulette":    RouletteBetView,
    "baccarat":    BaccaratBetView,
    "horseracing": HorseRacingEventView,
}

_DEFAULT_BETS: dict[str, callable] = {
    "roulette":    lambda: random.choice(["red", "black", "odd", "even"]),
    "baccarat":    lambda: random.choice(["player", "banker"]),
    "gamble":      lambda: True,
    "horseracing": lambda: random.randint(1, 6),
}

def _build_join_embed(game: dict, min_bet: int, end_ts: int, participants: dict) -> discord.Embed:
    pot_mode         = game.get("pot_mode", False)
    total_player_pot = sum(d["amount"] for d in participants.values())
    count            = len(participants)
    embed = discord.Embed(
        title=f"🎰 Casino Event: {game['label']}!",
        description=(
            f"{game['description']}\n\n"
            f"**Minimum wager:** {var.CURRENCY_SYMBOL} {min_bet:,} {var.CURRENCY_NAME}\n"
            f"⏱️ Closes <t:{end_ts}:R> — use `/join` to enter!"
        ),
        color=game["color"],
    )
    embed.add_field(name="👥 Players", value=str(count), inline=True)
    if pot_mode:
        prize_pool = total_player_pot * 2
        pool_value = f"{var.CURRENCY_SYMBOL} {prize_pool:,} *(house matched!)*" if count else f"{var.CURRENCY_SYMBOL} 0"
        embed.add_field(name="🏆 Prize Pool", value=pool_value, inline=True)
        embed.set_footer(text=f"{var.SERVER_NAME} · House doubles the pot!")
    else:
        wagered_value = f"{var.CURRENCY_SYMBOL} {total_player_pot:,}" if count else f"{var.CURRENCY_SYMBOL} 0"
        embed.add_field(name="💰 Total Wagered", value=wagered_value, inline=True)
        embed.set_footer(text=f"{var.SERVER_NAME} · Winners paid at individual odds!")
    embed.timestamp = datetime.utcnow()
    return embed

# ============================================================================
# COG
# ============================================================================

class CasinoEventCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot              = bot
        self.db               = ForgeDB.get()
        self.event_active     = False
        self._current_game    = None
        self._participants: dict[str, dict] = {}
        self._event_gid: str | None = None
        self._loop_task: asyncio.Task | None = None
        self._event_msg: discord.Message | None = None
        self._event_end_ts: int = 0
        self._event_min_bet: int = 0

    async def cog_load(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS casino_event_stats (
                user_id       TEXT    NOT NULL,
                guild_id      TEXT    NOT NULL,
                game_type     TEXT    NOT NULL,
                events_joined INTEGER DEFAULT 0,
                events_won    INTEGER DEFAULT 0,
                events_lost   INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id, game_type)
            )
        """)

    @commands.Cog.listener()
    async def on_ready(self):
        if self._loop_task is None or self._loop_task.done():
            self._loop_task = asyncio.create_task(self._event_loop())

    def cog_unload(self):
        if self._loop_task:
            self._loop_task.cancel()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_event_channel(self):
        shared = load_config().get('casino_announcement_channel_id')
        if shared:
            ch = self.bot.get_channel(int(shared))
            if ch:
                return ch
        cid = _load_settings().get("channel_id") or var.EVENT_CHANNEL_ID
        return self.bot.get_channel(int(cid)) if cid else None

    # ── Background loop (random interval) ────────────────────────────────────

    async def _event_loop(self):
        await self.bot.wait_until_ready()
        while True:
            cfg   = _load_settings()
            min_m = cfg.get("interval_min", var.EVENT_INTERVAL_MIN)
            max_m = cfg.get("interval_max", var.EVENT_INTERVAL_MAX)
            wait  = random.randint(min_m, max_m)
            log.info("CasinoEvent: next event in %d minutes", wait)
            await asyncio.sleep(wait * 60)
            await self._run_event()

    # ── Core event runner ─────────────────────────────────────────────────────

    async def _run_event(self) -> str | None:
        """Run a casino event. Returns an error string on failure, None on success."""
        if self.event_active:
            return "An event is already running."

        channel = self._get_event_channel()
        if channel is None:
            log.warning("CasinoEvent: event channel not configured — use /set_eventannouncement_channel")
            return "No event channel configured. Use `/set_eventannouncement_channel` first."

        cfg         = _load_settings()
        join_window = cfg.get("join_window", var.JOIN_WINDOW)
        min_bet     = cfg.get("event_bet_min", var.EVENT_BET)

        gid  = str(channel.guild.id)
        game = random.choice(var.CASINO_GAMES)

        self._current_game = game
        self._participants  = {}
        self._event_gid    = gid
        self.event_active  = True

        end_ts = int(time.time()) + join_window
        self._event_end_ts  = end_ts
        self._event_min_bet = min_bet

        msg = await channel.send(embed=_build_join_embed(game, min_bet, end_ts, {}))
        self._event_msg = msg

        await asyncio.sleep(join_window)

        # Close the join window — /join checks self._current_game is not None
        self._current_game = None
        participants = dict(self._participants)

        if not participants:
            cancelled = discord.Embed(
                title=f"🎰 Casino Event: {game['label']}",
                description="*No one joined — event cancelled.*",
                color=game["color"],
            )
            await msg.edit(embed=cancelled)
            self._event_msg = None
            self.event_active = False
            return None

        resolver = RESOLVERS.get(game["id"])
        if resolver is None:
            log.error("CasinoEvent: no resolver for game id '%s'", game["id"])
            self._event_msg = None
            self.event_active = False
            return None

        pot_mode         = game.get("pot_mode", False)
        total_player_pot = sum(d["amount"] for d in participants.values())
        prize_pool       = total_player_pot * 2 if pot_mode else total_player_pot

        dm_mult          = getattr(self.bot, 'multiplier_event_mult', None) or 1.0
        bot_uid          = str(self.bot.user.id) if self.bot.user else ""
        summary, results = resolver(participants, self.db, gid, dm_mult, bot_uid, prize_pool)

        lines     = []
        any_winner = False
        for uid, delta_str, emoji, bet in results:
            try:
                user = await self.bot.fetch_user(int(uid))
                name = user.display_name
            except Exception:
                name = f"<@{uid}>"
            bet_tag = f" `{_display_bet(bet)}`" if _display_bet(bet) else ""
            lines.append(f"{emoji} **{name}**{bet_tag} → {delta_str}")
            won = True if emoji == "✅" else (False if emoji == "❌" else None)
            _record_event_stats(self.db, uid, gid, "casino", won)
            if emoji == "✅":
                any_winner = True

        sym = var.CURRENCY_SYMBOL
        if pot_mode:
            pot_line = f"💰 **Prize Pool:** {sym} {prize_pool:,} *(house matched {sym} {total_player_pot:,})*\n\n"
            if not any_winner:
                pot_line += f"🏦 No winners — house claims {sym} {prize_pool:,}!\n\n"
        else:
            pot_line = f"💰 **Total Wagered:** {sym} {total_player_pot:,}\n\n"
            if not any_winner:
                pot_line += f"🏦 No winners — house keeps all bets!\n\n"
        dm_note      = f"\n💰 **{dm_mult}x** Double Money Event — all payouts boosted!" if dm_mult > 1.0 else ""
        result_embed = discord.Embed(
            title=f"🏆 Event Results: {game['label']}",
            description=f"**{summary}**\n\n{pot_line}" + "\n".join(lines) + dm_note,
            color=game["color"],
        )
        result_embed.set_footer(
            text=f"{len(participants)} player{'s' if len(participants) != 1 else ''} participated · {var.SERVER_NAME}"
        )
        result_embed.timestamp = datetime.utcnow()

        closed = _build_join_embed(game, min_bet, end_ts, participants)
        closed.title = f"🎰 Casino Event: {game['label']} — Closed"
        await msg.edit(embed=closed)
        await channel.send(embed=result_embed)

        self._event_msg = None
        self.event_active = False
        return None

    # ── /join ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="join", description="Join the active casino event with your chosen wager.")
    @app_commands.describe(wage="How many coins to wager")
    async def join(self, interaction: discord.Interaction, wage: int):
        if not self.event_active or self._current_game is None:
            await interaction.response.send_message(
                embed=discord.Embed(description="No event is currently active.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if uid in self._participants:
            await interaction.response.send_message(
                embed=discord.Embed(description="You've already joined this event!", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        cfg     = _load_settings()
        min_bet = cfg.get("event_bet_min", var.EVENT_BET)
        if wage < min_bet:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Minimum wager is {var.CURRENCY_SYMBOL} **{min_bet:,} {var.CURRENCY_NAME}**.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        self.db.ensure_user(uid, gid, interaction.user.display_name)
        balance = self.db.get_balance(uid, gid)
        if balance < wage:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        f"Not enough {var.CURRENCY_NAME}.\n"
                        f"Wager: **{var.CURRENCY_SYMBOL} {wage:,}** · Balance: **{var.CURRENCY_SYMBOL} {balance:,}**"
                    ),
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        bot_uid = str(interaction.client.user.id)
        self.db.update_balance(uid, gid, -wage, 'event_bet')
        _house_tx(self.db, bot_uid, gid, wage, 'house_gain')
        game_id     = self._current_game["id"]
        default_bet = _DEFAULT_BETS.get(game_id, lambda: True)()
        self._participants[uid] = {"amount": wage, "bet": default_bet}

        # Update the live event embed with new participant count and prize pool
        if self._event_msg and self._current_game:
            try:
                await self._event_msg.edit(embed=_build_join_embed(
                    self._current_game, self._event_min_bet,
                    self._event_end_ts, self._participants,
                ))
            except Exception:
                pass

        join_window = cfg.get("join_window", var.JOIN_WINDOW)

        if game_id in _BET_VIEWS:
            bet_label = default_bet if isinstance(default_bet, str) else ""
            view      = _BET_VIEWS[game_id](self._participants, uid, timeout=join_window)
            await interaction.response.send_message(
                content=(
                    f"✅ You're in with **{var.CURRENCY_SYMBOL} {wage:,}**!\n"
                    f"Default bet: **{bet_label}** — change it below if you want:"
                ),
                view=view,
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"✅ You're in! **{var.CURRENCY_SYMBOL} {wage:,} {var.CURRENCY_NAME}** wagered.",
                    color=var.COLOR_WIN,
                ),
                ephemeral=True,
            )

    # ── Admin commands ────────────────────────────────────────────────────────

    @app_commands.command(name="startevent", description="Manually start a server event.")
    @app_commands.describe(event="Which type of event to start")
    @app_commands.choices(event=[
        app_commands.Choice(name="Casino", value="casino"),
        app_commands.Choice(name="Multiplier", value="multiplier"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def startevent(self, interaction: discord.Interaction, event: str):
        if event == "casino":
            await interaction.response.defer(ephemeral=True)
            err = await self._run_event()
            if err:
                await interaction.followup.send(
                    embed=discord.Embed(description=f"❌ {err}", color=var.COLOR_ERROR),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send("✅ Casino event started!", ephemeral=True)
        else:
            cog = self.bot.get_cog("MultiplierEventCog")
            if cog is None:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description="❌ Multiplier Event cog is not loaded.",
                        color=var.COLOR_ERROR,
                    ),
                    ephemeral=True,
                )
                return
            await cog.start_from_startevent(interaction)

    @app_commands.command(name="set_join_window_timer", description="Set how long players have to join a casino event.")
    @app_commands.describe(seconds="Seconds the join window stays open (minimum 10)")
    async def set_join_window_timer(self, interaction: discord.Interaction, seconds: int):
        if seconds < 10:
            await interaction.response.send_message(
                embed=discord.Embed(description="Join window must be at least 10 seconds.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return
        data = _load_settings()
        data["join_window"] = seconds
        _save_settings(data)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Join window set to **{seconds} seconds**.",
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="set_eventannouncement_channel", description="Set the announcement channel for a specific event type.")
    @app_commands.describe(event="Which event to configure", channel="Channel to post announcements in")
    @app_commands.choices(event=[
        app_commands.Choice(name="Casino", value="casino"),
        app_commands.Choice(name="Multiplier", value="multiplier"),
    ])
    async def set_eventannouncement_channel(self, interaction: discord.Interaction, event: str, channel: discord.TextChannel):
        cfg = load_config()
        key  = 'casino_announcement_channel_id' if event == 'casino' else 'multiplier_announcement_channel_id'
        name = "Casino Event" if event == 'casino' else "Multiplier Event"
        cfg[key] = channel.id
        save_config(cfg)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ {name} announcements will be posted in {channel.mention}.",
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="set_casino_event_downtime", description="Set the random interval between casino events.")
    @app_commands.describe(
        min_minutes="Minimum minutes between events",
        max_minutes="Maximum minutes between events",
    )
    async def set_casino_event_downtime(
        self,
        interaction: discord.Interaction,
        min_minutes: int,
        max_minutes: int,
    ):
        if min_minutes < 1:
            await interaction.response.send_message(
                embed=discord.Embed(description="Minimum must be at least 1 minute.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return
        if max_minutes < min_minutes:
            await interaction.response.send_message(
                embed=discord.Embed(description="Maximum must be ≥ minimum.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return
        data = _load_settings()
        data["interval_min"] = min_minutes
        data["interval_max"] = max_minutes
        _save_settings(data)

        # Restart the loop so the new interval takes effect immediately
        # (only if no event is currently running — restarting mid-event would cut it short)
        restarted = False
        if not self.event_active:
            if self._loop_task and not self._loop_task.done():
                self._loop_task.cancel()
            self._loop_task = asyncio.create_task(self._event_loop())
            restarted = True

        note = (
            f"Next event will fire in **{min_minutes}–{max_minutes} minutes**."
            if restarted else
            f"Takes effect after the current event ends."
        )
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Event interval set to **{min_minutes}–{max_minutes} minutes**. {note}",
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(CasinoEventCog(bot))
    log.info("✅ Events/CasinoEvent cog loaded")
