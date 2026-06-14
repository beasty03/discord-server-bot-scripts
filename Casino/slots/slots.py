import discord
from discord.ext import commands
from discord import app_commands
import random
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('sl_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")

# (emoji, weight, 3-of-a-kind return multiplier)
_SYMBOLS = [
    ("🍒", 30, 2.0),
    ("🍋", 25, 2.5),
    ("🍊", 20, 3.0),
    ("🍇", 15, 4.0),
    ("🔔", 10, 5.0),
    ("⭐",  7, 8.0),
    ("💎",  4, 15.0),
    ("7️⃣",  2, 25.0),
]
_WEIGHTS = [s[1] for s in _SYMBOLS]


def _record_stats(db, uid: str, gid: str, won: int = 0, lost: int = 0):
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

def _house_tx(db, bot_uid: str, gid: str, amount: int, tx_type: str):
    db.ensure_user(bot_uid, gid, "House")
    db.update_balance(bot_uid, gid, amount, tx_type)


def _spin() -> list:
    return random.choices(_SYMBOLS, weights=_WEIGHTS, k=3)


def _evaluate(reels: list) -> tuple[str, float]:
    emojis = [r[0] for r in reels]
    if emojis[0] == emojis[1] == emojis[2]:
        return f"3× {emojis[0]}", reels[0][2]
    for sym in set(emojis):
        if emojis.count(sym) == 2:
            return f"2× {sym}", var.TWO_OF_A_KIND_MULT
    return "No match", 0.0


class SlotsCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    async def cog_load(self):
        for col in ('games_won', 'games_lost'):
            try:
                self.db.execute(f"ALTER TABLE casino_stats ADD COLUMN {col} INTEGER DEFAULT 0")
            except Exception:
                pass

    @app_commands.command(name="slots", description="Spin the slot machine for a chance to win big!")
    @app_commands.describe(amount="Amount to bet")
    async def slots(self, interaction: discord.Interaction, amount: int):
        uid  = str(interaction.user.id)
        gid  = str(interaction.guild_id)
        name = interaction.user.display_name
        sym  = var.CURRENCY_SYMBOL

        self.db.ensure_user(uid, gid, name)
        bot_uid = str(interaction.client.user.id)

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
                    description=var.MESSAGE_INSUFFICIENT_FUNDS.format(currency=var.CURRENCY_NAME),
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        self.db.update_balance(uid, gid, -amount, 'bet')
        _house_tx(self.db, bot_uid, gid, amount, 'house_gain')

        reels       = _spin()
        label, mult = _evaluate(reels)
        reel_str    = "  ".join(r[0] for r in reels)

        dm_mult = getattr(interaction.client, 'multiplier_event_mult', None) or 1.0

        if mult > 0:
            raw_payout = int(amount * mult)
            profit     = raw_payout - amount
            if dm_mult > 1.0:
                profit     = int(profit * dm_mult)
                raw_payout = amount + profit
            self.db.update_balance(uid, gid, raw_payout, 'win')
            _house_tx(self.db, bot_uid, gid, -raw_payout, 'house_payout')
            _record_stats(self.db, uid, gid, profit, 0)

            color      = var.COLOR_WIN
            result_txt = f"**{label}** — you won {sym} **{profit:,}**!"
            pub        = f"🎰 **{name}** hit **{label}** on Slots and won {sym} **{profit:,}**!"
            if dm_mult > 1.0:
                pub += f" *(💰 {dm_mult}x event)*"
        else:
            _record_stats(self.db, uid, gid, 0, amount)
            color      = var.COLOR_LOSE
            result_txt = f"**{label}** — better luck next time!"
            pub        = f"🎰 **{name}** missed on Slots and lost {sym} **{amount:,}**."

        new_balance = self.db.get_balance(uid, gid)

        embed = discord.Embed(
            title="🎰 Slot Machine",
            color=color,
        )
        embed.add_field(name="Reels", value=f"**[ {reel_str} ]**", inline=False)
        embed.add_field(name="Result", value=result_txt, inline=False)
        if mult > 0 and dm_mult > 1.0:
            embed.add_field(name="💰 Event Bonus", value=f"**{dm_mult}x** multiplier applied!", inline=False)
        embed.add_field(name="New Balance", value=f"{sym} {new_balance:,} {var.CURRENCY_NAME}", inline=True)
        embed.set_footer(text=f"Played by {interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()

        await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.channel.send(pub)


async def setup(bot: commands.Bot):
    await bot.add_cog(SlotsCog(bot))
    log.info("✅ Casino/Slots cog loaded")
