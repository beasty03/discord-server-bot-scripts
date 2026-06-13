import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('ce_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

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

# ============================================================================
# INLINE GAME RESOLVERS
# Each resolver signature: (participants, event_bet, db, gid) -> (summary_str, results)
# participants: dict[uid_str -> bet_choice]  (gamble uses True as placeholder)
# results:      list of (uid_str, delta_str, emoji_str)
# Balance was already deducted at join time; resolvers only ADD winnings.
# ============================================================================

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
    return False, 0.0

def resolve_roulette(participants: dict, event_bet: int, db, gid: str):
    result = random.randint(0, 36)
    emoji  = {"green": "🟢", "red": "🔴", "black": "⚫"}[_roulette_color(result)]
    rows   = []
    for uid, bet in participants.items():
        won, mult = _roulette_check(result, bet)
        if won:
            payout = int(event_bet * mult)
            db.update_balance(uid, gid, payout, 'event_win')
            rows.append((uid, f"+{payout:,}", "✅", bet))
        else:
            rows.append((uid, f"-{event_bet:,}", "❌", bet))
    return f"{emoji} Ball landed on **{result}**", rows


def resolve_gamble(participants: dict, event_bet: int, db, gid: str):
    rows = []
    for uid in participants:
        if random.random() < var.GAMBLE_WIN_CHANCE / 100:
            payout = int(event_bet * var.GAMBLE_WIN_MULTIPLIER)
            db.update_balance(uid, gid, payout, 'event_win')
            rows.append((uid, f"+{payout:,}", "✅", ""))
        else:
            rows.append((uid, f"-{event_bet:,}", "❌", ""))
    return "🎲 Dice rolled!", rows


_BRANK = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
def _bval(r): return 1 if r == "A" else 0 if r in ("10","J","Q","K") else int(r)
def _bhand(): return sum(_bval(random.choice(_BRANK)) for _ in range(2)) % 10

def resolve_baccarat(participants: dict, event_bet: int, db, gid: str):
    pt = _bhand()
    bt = _bhand()
    outcome = "player" if pt > bt else ("banker" if bt > pt else "tie")
    mult    = {"player": 2.0, "banker": 1.95, "tie": 9.0}
    rows    = []
    for uid, bet in participants.items():
        if bet == outcome:
            payout = int(event_bet * mult[bet])
            db.update_balance(uid, gid, payout, 'event_win')
            rows.append((uid, f"+{payout:,}", "✅", bet))
        elif outcome == "tie" and bet != "tie":
            db.update_balance(uid, gid, event_bet, 'refund')
            rows.append((uid, "refund", "↩️", bet))
        else:
            rows.append((uid, f"-{event_bet:,}", "❌", bet))
    summary = f"👤 Player **{pt}** vs 🏦 Banker **{bt}** → {outcome.capitalize()} wins!"
    return summary, rows


RESOLVERS = {
    "roulette": resolve_roulette,
    "gamble":   resolve_gamble,
    "baccarat": resolve_baccarat,
}

# ============================================================================
# BET-SELECTION VIEWS  (ephemeral, shown after clicking Join)
# ============================================================================

class _BetView(discord.ui.View):
    def __init__(self, participants: dict, uid: str):
        super().__init__(timeout=var.JOIN_WINDOW)
        self.participants = participants
        self.uid          = uid

    async def _pick(self, interaction: discord.Interaction, bet: str):
        self.participants[self.uid] = bet
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"✅ Bet updated to **{bet}**!", view=self,
        )
        self.stop()


class RouletteBetView(_BetView):
    @discord.ui.button(label="🔴 Red",   style=discord.ButtonStyle.danger,    row=0)
    async def red(self,   i: discord.Interaction, _b): await self._pick(i, "red")
    @discord.ui.button(label="⚫ Black", style=discord.ButtonStyle.secondary, row=0)
    async def black(self, i: discord.Interaction, _b): await self._pick(i, "black")
    @discord.ui.button(label="Odd",      style=discord.ButtonStyle.primary,   row=1)
    async def odd(self,   i: discord.Interaction, _b): await self._pick(i, "odd")
    @discord.ui.button(label="Even",     style=discord.ButtonStyle.primary,   row=1)
    async def even(self,  i: discord.Interaction, _b): await self._pick(i, "even")


class BaccaratBetView(_BetView):
    @discord.ui.button(label="👤 Player", style=discord.ButtonStyle.primary, row=0)
    async def player(self, i: discord.Interaction, _b): await self._pick(i, "player")
    @discord.ui.button(label="🏦 Banker", style=discord.ButtonStyle.danger,  row=0)
    async def banker(self, i: discord.Interaction, _b): await self._pick(i, "banker")
    @discord.ui.button(label="🤝 Tie",    style=discord.ButtonStyle.success, row=0)
    async def tie(self,    i: discord.Interaction, _b): await self._pick(i, "tie")


_BET_VIEWS: dict[str, type[_BetView]] = {
    "roulette": RouletteBetView,
    "baccarat": BaccaratBetView,
}

_DEFAULT_BETS: dict[str, callable] = {
    "roulette": lambda: random.choice(["red", "black", "odd", "even"]),
    "baccarat": lambda: random.choice(["player", "banker"]),
    "gamble":   lambda: True,
}

# ============================================================================
# JOIN VIEW
# ============================================================================

class EventJoinView(discord.ui.View):
    def __init__(self, game: dict, participants: dict, db, gid: str):
        super().__init__(timeout=var.JOIN_WINDOW)
        self.game         = game
        self.participants = participants
        self.db           = db
        self.gid          = gid

    @discord.ui.button(label="🎮 Join Event", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, _button: discord.ui.Button):
        uid = str(interaction.user.id)

        if uid in self.participants:
            await interaction.response.send_message("You've already joined!", ephemeral=True)
            return

        self.db.ensure_user(uid, self.gid, interaction.user.display_name)
        if self.db.get_balance(uid, self.gid) < var.EVENT_BET:
            await interaction.response.send_message(
                f"You need at least {var.CURRENCY_SYMBOL} **{var.EVENT_BET:,}** to join.",
                ephemeral=True,
            )
            return

        # Deduct bet and assign a random default so they're always in even if they ignore the bet view
        self.db.update_balance(uid, self.gid, -var.EVENT_BET, 'event_bet')
        game_id = self.game["id"]
        default = _DEFAULT_BETS.get(game_id, lambda: True)()
        self.participants[uid] = default

        if game_id in _BET_VIEWS:
            bet_label = default if isinstance(default, str) else ""
            view      = _BET_VIEWS[game_id](self.participants, uid)
            await interaction.response.send_message(
                f"✅ You're in! Default bet: **{bet_label}** — change it below if you want:",
                view=view,
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"✅ You're in! {var.CURRENCY_SYMBOL} **{var.EVENT_BET:,}** wagered.",
                ephemeral=True,
            )

# ============================================================================
# COG
# ============================================================================

class CasinoEventCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot            = bot
        self.db             = ForgeDB.get()
        self.event_active   = False
        self._loop_task: asyncio.Task | None = None

    @commands.Cog.listener()
    async def on_ready(self):
        if self._loop_task is None or self._loop_task.done():
            self._loop_task = asyncio.create_task(self._event_loop())

    def cog_unload(self):
        if self._loop_task:
            self._loop_task.cancel()

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

    async def _run_event(self):
        if self.event_active:
            return

        channel = self.bot.get_channel(var.EVENT_CHANNEL_ID)
        if channel is None:
            log.warning("CasinoEvent: EVENT_CHANNEL_ID (%s) not found — set it in variables.py", var.EVENT_CHANNEL_ID)
            return

        gid          = str(channel.guild.id)
        game         = random.choice(var.CASINO_GAMES)
        participants: dict[str, object] = {}

        join_embed = discord.Embed(
            title=f"🎰 Casino Event: {game['label']}!",
            description=(
                f"{game['description']}\n\n"
                f"**Entry:** {var.CURRENCY_SYMBOL} {var.EVENT_BET:,} {var.CURRENCY_NAME}\n"
                f"⏱️ Join window: **{var.JOIN_WINDOW}s**"
            ),
            color=game["color"],
        )
        join_embed.set_footer(text=f"{var.SERVER_NAME} · Click below to join!")
        join_embed.timestamp = datetime.utcnow()

        view = EventJoinView(game, participants, self.db, gid)
        self.event_active = True
        msg  = await channel.send(embed=join_embed, view=view)

        await asyncio.sleep(var.JOIN_WINDOW)

        # Close the join view
        view.stop()
        for item in view.children:
            item.disabled = True

        if not participants:
            join_embed.description = "*No one joined — event cancelled.*"
            await msg.edit(embed=join_embed, view=view)
            self.event_active = False
            return

        resolver = RESOLVERS.get(game["id"])
        if resolver is None:
            log.error("CasinoEvent: no resolver for game id '%s'", game["id"])
            self.event_active = False
            return

        summary, results = resolver(participants, var.EVENT_BET, self.db, gid)

        lines = []
        for uid, delta_str, emoji, bet in results:
            try:
                user = await self.bot.fetch_user(int(uid))
                name = user.display_name
            except Exception:
                name = f"<@{uid}>"
            bet_tag = f" `{bet}`" if isinstance(bet, str) and bet else ""
            lines.append(f"{emoji} **{name}**{bet_tag} → {delta_str}")

        result_embed = discord.Embed(
            title=f"🏆 Event Results: {game['label']}",
            description=f"**{summary}**\n\n" + "\n".join(lines),
            color=game["color"],
        )
        result_embed.set_footer(
            text=f"{len(participants)} player{'s' if len(participants) != 1 else ''} participated · {var.SERVER_NAME}"
        )
        result_embed.timestamp = datetime.utcnow()

        join_embed.description = "Event ended! Results below."
        await msg.edit(embed=join_embed, view=view)
        await channel.send(embed=result_embed)

        self.event_active = False

    # ── Admin commands ────────────────────────────────────────────────────────

    @app_commands.command(name="startevent", description="Manually trigger a casino event.")
    @app_commands.checks.has_permissions(administrator=True)
    async def startevent(self, interaction: discord.Interaction):
        if self.event_active:
            await interaction.response.send_message("An event is already running!", ephemeral=True)
            return
        await interaction.response.send_message("Starting casino event…", ephemeral=True)
        await self._run_event()

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
        await interaction.response.send_message(
            embed=discord.Embed(
                description=(
                    f"✅ Casino event interval set to **{min_minutes}–{max_minutes} minutes**.\n"
                    f"A random delay in that range is picked after each event."
                ),
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(CasinoEventCog(bot))
    log.info("✅ Events/Casino cog loaded")
