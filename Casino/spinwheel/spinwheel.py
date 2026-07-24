import discord
from discord.ext import commands
from discord import app_commands
import random
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('sw_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")

_WEIGHTS = [s[2] for s in var.SEGMENTS]

_WHEEL_DISPLAY = " | ".join(s[0] for s in var.SEGMENTS)


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


def _spin() -> tuple:
    return random.choices(var.SEGMENTS, weights=_WEIGHTS, k=1)[0]


class SpinWheelCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    async def cog_load(self):
        for col in ('games_won', 'games_lost'):
            try:
                self.db.execute(f"ALTER TABLE casino_stats ADD COLUMN {col} INTEGER DEFAULT 0")
            except Exception:
                pass

    @app_commands.command(
        name="spinwheel",
        description="Spin the prize wheel and see where it lands!",
    )
    @app_commands.describe(amount="Amount to bet")
    async def spinwheel(self, interaction: discord.Interaction, amount: int):
        uid  = str(interaction.user.id)
        gid  = str(interaction.guild_id)
        name = interaction.user.display_name
        sym  = var.CURRENCY_SYMBOL

        self.db.ensure_user(uid, gid, name)

        if amount < var.MIN_BET:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=var.MESSAGE_BET_TOO_LOW.format(min_bet=var.MIN_BET, currency=var.CURRENCY_NAME),
                    color=var.COLOR_ERROR,
                ), ephemeral=True,
            )
        if var.MAX_BET > 0 and amount > var.MAX_BET:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=var.MESSAGE_BET_TOO_HIGH.format(max_bet=var.MAX_BET, currency=var.CURRENCY_NAME),
                    color=var.COLOR_ERROR,
                ), ephemeral=True,
            )

        balance = self.db.get_balance(uid, gid)
        if balance < amount:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=var.MESSAGE_INSUFFICIENT_FUNDS.format(currency=var.CURRENCY_NAME),
                    color=var.COLOR_ERROR,
                ), ephemeral=True,
            )

        bot_uid = str(interaction.client.user.id)
        self.db.update_balance(uid, gid, -amount, 'bet')
        _house_tx(self.db, bot_uid, gid, amount, 'house_gain')

        label, mult, _ = _spin()
        payout = int(amount * mult)
        profit = payout - amount
        won    = profit > 0   # only True when mult > 1.0

        # Event multiplier applies only to actual wins, not to partial losses
        ev_mult = getattr(interaction.client, 'multiplier_event_mult', None) or 1.0
        if won and ev_mult > 1.0:
            profit = int(profit * ev_mult)
            payout = amount + profit

        if payout > 0:
            self.db.update_balance(uid, gid, payout, 'win')
            _house_tx(self.db, bot_uid, gid, -payout, 'house_payout')

        _record_stats(self.db, uid, gid, profit if won else 0, amount if not won else 0)

        new_bal = self.db.get_balance(uid, gid)

        if profit < 0:
            color = var.COLOR_LOSE
            title = f"🎡 {label}"
            desc  = f"Lost {sym} **{abs(profit):,}** {var.CURRENCY_NAME}."
        else:
            color = var.COLOR_WIN
            title = f"🎡 {label} — You win!"
            desc  = f"Won {sym} **{profit:,}** {var.CURRENCY_NAME}!"

        embed = discord.Embed(title=title, description=desc, color=color)
        embed.add_field(name="Bet",        value=f"{sym} {amount:,}",  inline=True)
        embed.add_field(name="Multiplier", value=f"**{mult}×**",       inline=True)
        embed.add_field(name="Balance",    value=f"{sym} {new_bal:,}", inline=True)
        if won and ev_mult > 1.0:
            embed.add_field(name="💰 Event bonus", value=f"**{ev_mult}×** applied!", inline=False)
        embed.set_footer(text=f"🎡 {_WHEEL_DISPLAY}  •  {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(SpinWheelCog(bot))
    log.info("✅ Casino/SpinWheel cog loaded")
