import discord
from discord.ext import commands
from discord import app_commands
import random
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('craps_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")

_DICE = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
_NATURALS = {7, 11}
_CRAPS    = {2, 3, 12}


def _roll() -> tuple[int, int]:
    return random.randint(1, 6), random.randint(1, 6)


def _dice_str(d1: int, d2: int) -> str:
    return f"{_DICE[d1 - 1]} {_DICE[d2 - 1]}"


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


class CrapsView(discord.ui.View):

    def __init__(self, cog, interaction: discord.Interaction, bet: int):
        super().__init__(timeout=var.BUTTON_TIMEOUT)
        self.cog         = cog
        self.db          = cog.db
        self.interaction = interaction
        self.bet         = bet
        self.uid         = str(interaction.user.id)
        self.gid         = str(interaction.guild_id)
        self.point       = None   # None = come-out phase
        self.resolved    = False
        self.history: list[str] = []

    def _build_embed(self, dice_str: str, total: int, status_line: str) -> discord.Embed:
        phase = "Come-out roll" if self.point is None else f"Point: **{self.point}** — roll {self.point} to win, avoid 7"
        history_txt = "\n".join(self.history[-6:]) if self.history else "—"
        embed = discord.Embed(
            title=f"🎲 Craps  •  {dice_str}  =  **{total}**",
            description=f"**{status_line}**\n\n_{phase}_",
            color=var.COLOR_PLAYING,
        )
        embed.add_field(name="Bet",       value=f"{var.CURRENCY_SYMBOL} {self.bet:,}", inline=True)
        embed.add_field(name="Roll log",  value=history_txt,                           inline=False)
        embed.set_footer(text=f"{self.interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        return embed

    @discord.ui.button(label="🎲 Roll Come-Out", style=discord.ButtonStyle.primary)
    async def roll_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != int(self.uid):
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        if self.resolved:
            await interaction.response.defer()
            return

        d1, d2  = _roll()
        total   = d1 + d2
        ds      = _dice_str(d1, d2)

        if self.point is None:
            # Come-out roll
            if total in _NATURALS:
                self.history.append(f"{ds} = **{total}** — Natural!")
                await self._win(interaction, ds, total, f"Natural {total}! Pass line wins.")
            elif total in _CRAPS:
                self.history.append(f"{ds} = **{total}** — Craps!")
                await self._lose(interaction, ds, total, f"Craps! {total} = instant loss.")
            else:
                self.point = total
                self.history.append(f"{ds} = **{total}** — Point set to {total}")
                button.label = f"🎲 Roll Again  (point: {total})"
                embed = self._build_embed(ds, total, f"Point is {total}. Roll it again before you roll a 7!")
                await interaction.response.edit_message(embed=embed, view=self)
        else:
            # Point phase
            if total == self.point:
                self.history.append(f"{ds} = **{total}** — Point made!")
                await self._win(interaction, ds, total, f"Point made! {total} hits — pass line wins.")
            elif total == 7:
                self.history.append(f"{ds} = **{total}** — Seven out!")
                await self._lose(interaction, ds, total, f"Seven out! Rolled 7 before the point ({self.point}).")
            else:
                self.history.append(f"{ds} = **{total}**")
                embed = self._build_embed(ds, total, f"No action on {total}. Keep rolling for {self.point}!")
                await interaction.response.edit_message(embed=embed, view=self)

    async def _win(self, interaction: discord.Interaction, ds: str, total: int, reason: str):
        self.resolved = True
        self.roll_btn.disabled = True

        payout = self.bet * 2
        profit = self.bet

        ev_mult = getattr(interaction.client, 'multiplier_event_mult', None) or 1.0
        if ev_mult > 1.0:
            profit = int(profit * ev_mult)
            payout = self.bet + profit

        bot_uid = str(interaction.client.user.id)
        self.db.update_balance(self.uid, self.gid, payout, 'win')
        _house_tx(self.db, bot_uid, self.gid, -payout, 'house_payout')
        _record_stats(self.db, self.uid, self.gid, profit, 0)

        new_bal = self.db.get_balance(self.uid, self.gid)
        history_txt = "\n".join(self.history[-6:])

        embed = discord.Embed(
            title=f"🎲 {ds}  =  {total}  •  You win!",
            description=f"**{reason}**\n\nWon {var.CURRENCY_SYMBOL} **{profit:,}** {var.CURRENCY_NAME}!",
            color=var.COLOR_WIN,
        )
        embed.add_field(name="Payout",   value=f"{var.CURRENCY_SYMBOL} {payout:,}", inline=True)
        embed.add_field(name="Balance",  value=f"{var.CURRENCY_SYMBOL} {new_bal:,}", inline=True)
        embed.add_field(name="Roll log", value=history_txt, inline=False)
        if ev_mult > 1.0:
            embed.add_field(name="💰 Event bonus", value=f"**{ev_mult}×** applied!", inline=False)
        embed.set_footer(text=f"{interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.channel.send(embed=discord.Embed(
            description=(
                f"🎲 **{interaction.user.display_name}** won craps ({reason.lower()}) "
                f"and took home {var.CURRENCY_SYMBOL} **{profit:,}**!"
                + (f" *(💰 {ev_mult}× event!)*" if ev_mult > 1.0 else "")
            ),
            color=var.COLOR_WIN,
        ))

    async def _lose(self, interaction: discord.Interaction, ds: str, total: int, reason: str):
        self.resolved = True
        self.roll_btn.disabled = True

        bot_uid = str(interaction.client.user.id)
        _record_stats(self.db, self.uid, self.gid, 0, self.bet)

        new_bal = self.db.get_balance(self.uid, self.gid)
        history_txt = "\n".join(self.history[-6:])

        embed = discord.Embed(
            title=f"🎲 {ds}  =  {total}  •  You lose!",
            description=f"**{reason}**\n\nLost {var.CURRENCY_SYMBOL} **{self.bet:,}** {var.CURRENCY_NAME}.",
            color=var.COLOR_LOSE,
        )
        embed.add_field(name="Balance",  value=f"{var.CURRENCY_SYMBOL} {new_bal:,}", inline=True)
        embed.add_field(name="Roll log", value=history_txt, inline=False)
        embed.set_footer(text=f"{interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.channel.send(embed=discord.Embed(
            description=f"🎲 **{interaction.user.display_name}** crapped out and lost {var.CURRENCY_SYMBOL} **{self.bet:,}**!",
            color=var.COLOR_LOSE,
        ))

    async def on_timeout(self):
        if self.resolved:
            return
        self.resolved = True
        self.roll_btn.disabled = True
        self.db.update_balance(self.uid, self.gid, self.bet, 'refund')
        bot_uid = str(self.cog.bot.user.id)
        _house_tx(self.db, bot_uid, self.gid, -self.bet, 'house_refund')
        embed = discord.Embed(
            title="⏰ Timed Out — Bet Refunded",
            description=f"You didn't roll in time. {var.CURRENCY_SYMBOL} {self.bet:,} refunded.",
            color=var.COLOR_ERROR,
        )
        try:
            await self.interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            pass


class CrapsCog(commands.Cog):

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
        name="craps",
        description="Roll the dice! Pass line bet: win on 7/11, lose on 2/3/12, otherwise set a point.",
    )
    @app_commands.describe(amount="Amount to bet on the pass line")
    async def craps(self, interaction: discord.Interaction, amount: int):
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

        view  = CrapsView(self, interaction, amount)
        embed = discord.Embed(
            title="🎲 Craps — Pass Line Bet",
            description=(
                f"**Bet:** {sym} {amount:,}\n\n"
                f"**Come-out roll:**\n"
                f"• 7 or 11 → **Natural win** (1:1)\n"
                f"• 2, 3, or 12 → **Craps** (lose)\n"
                f"• Any other number → **Point** is set — roll it again before a 7"
            ),
            color=var.COLOR_PLAYING,
        )
        embed.set_footer(text=f"{name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(CrapsCog(bot))
    log.info("✅ Casino/Craps cog loaded")
