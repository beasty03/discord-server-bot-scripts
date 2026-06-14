import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import time
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('hr_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")


def _pick_winner() -> int:
    roll = random.randint(1, 100)
    cumul = 0
    for h in var.HORSES:
        cumul += h["chance"]
        if roll <= cumul:
            return h["id"]
    return var.HORSES[-1]["id"]


def _track(positions: list[int], winner_id: int = -1) -> str:
    TRACK = var.TRACK_LENGTH
    lines = []
    for h in var.HORSES:
        pos  = positions[h["id"] - 1]
        bar  = "▓" * pos + "░" * (TRACK - pos)
        flag = " 🏆" if h["id"] == winner_id else ""
        lines.append(f"{h['emoji']} **{h['name']}** {bar}{flag}")
    return "\n".join(lines)


def _mid_positions(winner_id: int) -> list[int]:
    mid = var.TRACK_LENGTH // 2
    pos = [random.randint(max(1, mid - 3), mid + 1) for _ in range(6)]
    pos[winner_id - 1] = random.randint(mid + 1, mid + 3)
    return pos


def _final_positions(winner_id: int) -> list[int]:
    pos = [random.randint(var.TRACK_LENGTH - 7, var.TRACK_LENGTH - 1) for _ in range(6)]
    pos[winner_id - 1] = var.TRACK_LENGTH
    return pos

# ── Helpers ───────────────────────────────────────────────────────────────────

def _record_stats(db, uid, gid, won=0, lost=0):
    db.execute(
        """INSERT INTO casino_stats (user_id, guild_id, games_played, games_won, games_lost, total_won, total_lost)
           VALUES (?, ?, 1, ?, ?, ?, ?)
           ON CONFLICT(user_id, guild_id) DO UPDATE SET
               games_played = games_played + 1,
               games_won    = games_won    + excluded.games_won,
               games_lost   = games_lost   + excluded.games_lost,
               total_won    = total_won    + excluded.total_won,
               total_lost   = total_lost   + excluded.total_lost""",
        (uid, gid, 1 if won > 0 else 0, 1 if lost > 0 else 0, won, lost),
    )


def _house_tx(db, bot_uid, gid, amount, tx_type):
    db.ensure_user(bot_uid, gid, "House")
    db.update_balance(bot_uid, gid, amount, tx_type)

# ── Race state ────────────────────────────────────────────────────────────────

class _Race:
    __slots__ = ("gid", "channel", "msg", "end_ts", "participants", "task")

    def __init__(self, gid: str, channel, msg, end_ts: int):
        self.gid          = gid
        self.channel      = channel
        self.msg          = msg
        self.end_ts       = end_ts
        self.participants: dict[str, dict] = {}  # uid -> {amount, horse_id, name}
        self.task         = None

# ── Horse-picker view (ephemeral, per-user) ───────────────────────────────────

class HorsePickView(discord.ui.View):
    def __init__(self, cog: "HorseRacingCog", race: _Race, uid: str, amount: int, bot_uid: str, timeout: float):
        super().__init__(timeout=max(5.0, timeout))
        self.cog     = cog
        self.race    = race
        self.uid     = uid
        self.amount  = amount
        self.bot_uid = bot_uid
        self.picked  = False

    async def _pick(self, interaction: discord.Interaction, horse: dict):
        if str(interaction.user.id) != self.uid:
            await interaction.response.send_message("This is not your bet!", ephemeral=True)
            return
        if self.picked:
            await interaction.response.defer()
            return
        self.picked = True
        self.stop()
        for item in self.children:
            item.disabled = True

        self.race.participants[self.uid]["horse_id"] = horse["id"]

        await interaction.response.edit_message(
            embed=discord.Embed(
                description=(
                    f"✅ You're riding **{horse['emoji']} {horse['name']}** ({horse['odds']}:1)!\n"
                    f"Bet: {var.CURRENCY_SYMBOL} **{self.amount:,}**\n\n"
                    f"⏱️ Race starts <t:{self.race.end_ts}:R> — good luck! 🍀"
                ),
                color=var.COLOR_INFO,
            ),
            view=self,
        )

    async def on_timeout(self):
        if not self.picked:
            gid = self.race.gid
            self.cog.db.update_balance(self.uid, gid, self.amount, 'refund')
            _house_tx(self.cog.db, self.bot_uid, gid, -self.amount, 'house_refund')
            self.race.participants.pop(self.uid, None)

    @discord.ui.button(label="⚡ Thunder  (2:1)",   style=discord.ButtonStyle.primary,   row=0)
    async def h1(self, i, _): await self._pick(i, var.HORSES[0])
    @discord.ui.button(label="💧 Splash   (3:1)",   style=discord.ButtonStyle.primary,   row=0)
    async def h2(self, i, _): await self._pick(i, var.HORSES[1])
    @discord.ui.button(label="🔥 Blaze    (5:1)",   style=discord.ButtonStyle.primary,   row=0)
    async def h3(self, i, _): await self._pick(i, var.HORSES[2])
    @discord.ui.button(label="🍀 Lucky    (7:1)",   style=discord.ButtonStyle.success,   row=1)
    async def h4(self, i, _): await self._pick(i, var.HORSES[3])
    @discord.ui.button(label="🌙 Midnight (9:1)",   style=discord.ButtonStyle.success,   row=1)
    async def h5(self, i, _): await self._pick(i, var.HORSES[4])
    @discord.ui.button(label="⭐ Comet    (14:1)",  style=discord.ButtonStyle.secondary, row=1)
    async def h6(self, i, _): await self._pick(i, var.HORSES[5])

# ── Cog ───────────────────────────────────────────────────────────────────────

class HorseRacingCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot   = bot
        self.db    = ForgeDB.get()
        self._races: dict[str, _Race] = {}  # guild_id -> active _Race

    async def cog_load(self):
        for col in ('games_won', 'games_lost'):
            try:
                self.db.execute(f"ALTER TABLE casino_stats ADD COLUMN {col} INTEGER DEFAULT 0")
            except Exception:
                pass

    # ── Race resolution ───────────────────────────────────────────────────────

    async def _resolve_race(self, race: _Race):
        gid = race.gid
        participants = {uid: d for uid, d in race.participants.items() if d.get("horse_id")}

        if not participants:
            await race.msg.edit(embed=discord.Embed(
                title="🏇 Horse Race — Cancelled",
                description="No riders picked their horse in time. All bets refunded.",
                color=var.COLOR_ERROR,
            ))
            return

        winner_id = _pick_winner()
        winner    = var.HORSES[winner_id - 1]
        bot_uid   = str(self.bot.user.id) if self.bot.user else ""
        dm_mult   = getattr(self.bot, 'multiplier_event_mult', None) or 1.0

        # Frame 1 — mid-race
        mid_embed = discord.Embed(
            title="🏇 Mid-Race!",
            description=_track(_mid_positions(winner_id)),
            color=var.COLOR_PLAYING,
        )
        mid_embed.set_footer(text=f"{var.SERVER_NAME} · And they're off!")
        mid_embed.timestamp = datetime.utcnow()
        await race.msg.edit(embed=mid_embed)
        await asyncio.sleep(var.RACE_ANIMATION_DELAY)

        # Frame 2 — final result + payouts
        final_pos    = _final_positions(winner_id)
        result_lines = []
        for uid, data in participants.items():
            amount   = data["amount"]
            horse_id = data["horse_id"]
            name     = data.get("name", f"<@{uid}>")
            horse    = var.HORSES[horse_id - 1]

            if horse_id == winner_id:
                payout = amount * winner["odds"]
                if dm_mult > 1.0:
                    payout = amount + int((payout - amount) * dm_mult)
                profit = payout - amount
                self.db.update_balance(uid, gid, payout, 'win')
                _house_tx(self.db, bot_uid, gid, -payout, 'house_payout')
                _record_stats(self.db, uid, gid, profit, 0)
                result_lines.append(
                    f"✅ **{name}** ({horse['emoji']} {horse['name']}) → +{var.CURRENCY_SYMBOL} {profit:,}"
                )
            else:
                _record_stats(self.db, uid, gid, 0, amount)
                result_lines.append(
                    f"❌ **{name}** ({horse['emoji']} {horse['name']}) → -{var.CURRENCY_SYMBOL} {amount:,}"
                )

        dm_note = f"\n💰 **{dm_mult}x** event — payouts boosted!" if dm_mult > 1.0 else ""
        final_embed = discord.Embed(
            title=f"🏆 {winner['emoji']} {winner['name']} wins the race!",
            description=(
                f"**Race Track:**\n{_track(final_pos, winner_id)}\n\n"
                f"**Results:**\n" + "\n".join(result_lines) + dm_note
            ),
            color=var.COLOR_WIN,
        )
        n = len(participants)
        final_embed.set_footer(text=f"{n} rider{'s' if n != 1 else ''} · {var.SERVER_NAME}")
        final_embed.timestamp = datetime.utcnow()
        await race.msg.edit(embed=final_embed)

    async def _race_timer(self, gid: str, race: _Race):
        await asyncio.sleep(var.JOIN_WINDOW)
        self._races.pop(gid, None)
        await self._resolve_race(race)

    # ── /horserace ────────────────────────────────────────────────────────────

    @app_commands.command(name="horserace", description="Join or start a shared horse race and bet on your horse!")
    @app_commands.describe(amount="Amount to bet")
    async def horserace(self, interaction: discord.Interaction, amount: int):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)
        self.db.ensure_user(uid, gid, interaction.user.display_name)

        if amount <= 0:
            await interaction.response.send_message(
                embed=discord.Embed(description=var.MESSAGE_INVALID_BET, color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        if amount < var.MIN_BET:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=var.MESSAGE_BET_TOO_LOW.format(min_bet=var.MIN_BET, currency=var.CURRENCY_NAME),
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        if var.MAX_BET > 0 and amount > var.MAX_BET:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=var.MESSAGE_BET_TOO_HIGH.format(max_bet=var.MAX_BET, currency=var.CURRENCY_NAME),
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        balance = self.db.get_balance(uid, gid)
        if balance < amount:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        f"Not enough {var.CURRENCY_NAME}.\n"
                        f"Balance: {var.CURRENCY_SYMBOL} {balance:,} · Bet: {var.CURRENCY_SYMBOL} {amount:,}"
                    ),
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        if gid in self._races and uid in self._races[gid].participants:
            await interaction.response.send_message(
                embed=discord.Embed(description="You've already joined this race!", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        # Deduct bet; refunded in HorsePickView.on_timeout if no horse picked
        bot_uid = str(interaction.client.user.id)
        self.db.update_balance(uid, gid, -amount, 'bet')
        _house_tx(self.db, bot_uid, gid, amount, 'house_gain')

        if gid not in self._races:
            end_ts = int(time.time()) + var.JOIN_WINDOW
            horse_list = "\n".join(
                f"{h['emoji']} **{h['name']}** — {h['odds']}:1 odds *(~{h['chance']}% chance)*"
                for h in var.HORSES
            )
            announce_embed = discord.Embed(
                title="🏇 Horse Race — Accepting Riders!",
                description=(
                    f"Use `/horserace [amount]` to join and pick your horse!\n\n"
                    f"{horse_list}\n\n"
                    f"⏱️ Race starts <t:{end_ts}:R>"
                ),
                color=var.COLOR_PLAYING,
            )
            announce_embed.set_footer(text=f"{var.SERVER_NAME} · Winners paid at full odds!")
            announce_embed.timestamp = datetime.utcnow()
            msg  = await interaction.channel.send(embed=announce_embed)
            race = _Race(gid, interaction.channel, msg, end_ts)
            self._races[gid] = race
            race.task = asyncio.create_task(self._race_timer(gid, race))
        else:
            race = self._races[gid]

        race.participants[uid] = {"amount": amount, "horse_id": None, "name": interaction.user.display_name}

        timeout_left = max(5.0, race.end_ts - time.time())
        pick_embed = discord.Embed(
            title="🏇 Pick Your Horse!",
            description=(
                f"Bet: {var.CURRENCY_SYMBOL} **{amount:,}** · Race starts <t:{race.end_ts}:R>\n\n"
                "Choose below — if time runs out your bet is refunded."
            ),
            color=var.COLOR_PLAYING,
        )
        view = HorsePickView(self, race, uid, amount, bot_uid, timeout=timeout_left)
        await interaction.response.send_message(embed=pick_embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HorseRacingCog(bot))
    log.info("✅ Casino/HorseRacing cog loaded")
