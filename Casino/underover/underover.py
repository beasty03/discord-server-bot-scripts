import discord
from discord.ext import commands
from discord import app_commands
import random
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('uo_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")

_DICE = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]


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


class UnderOverView(discord.ui.View):

    def __init__(self, cog, interaction: discord.Interaction, bet: int):
        super().__init__(timeout=var.BUTTON_TIMEOUT)
        self.cog         = cog
        self.db          = cog.db
        self.interaction = interaction
        self.bet         = bet
        self.uid         = str(interaction.user.id)
        self.gid         = str(interaction.guild_id)
        self.resolved    = False

    async def _resolve(self, interaction: discord.Interaction, choice: str):
        if interaction.user.id != int(self.uid):
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        if self.resolved:
            await interaction.response.defer()
            return

        self.resolved = True
        for item in self.children:
            item.disabled = True

        d1, d2 = _roll()
        total  = d1 + d2
        ds     = _dice_str(d1, d2)

        if total < 7:
            actual = "under"
        elif total == 7:
            actual = "exact"
        else:
            actual = "over"

        won = choice == actual

        _PAYOUT = {"under": var.PAYOUT_UNDER, "exact": var.PAYOUT_EXACT, "over": var.PAYOUT_OVER}
        _LABEL  = {"under": "Under 7",  "exact": "Exactly 7", "over": "Over 7"}
        _RANGE  = {"under": "2 – 6",    "exact": "= 7",       "over": "8 – 12"}

        mult    = _PAYOUT[choice]
        sym     = var.CURRENCY_SYMBOL
        bot_uid = str(interaction.client.user.id)

        if won:
            payout  = int(self.bet * mult)
            profit  = payout - self.bet
            ev_mult = getattr(interaction.client, 'multiplier_event_mult', None) or 1.0
            if ev_mult > 1.0:
                profit = int(profit * ev_mult)
                payout = self.bet + profit
            self.db.update_balance(self.uid, self.gid, payout, 'win')
            _house_tx(self.db, bot_uid, self.gid, -payout, 'house_payout')
            _record_stats(self.db, self.uid, self.gid, profit, 0)
        else:
            payout  = 0
            profit  = -self.bet
            ev_mult = 1.0
            _record_stats(self.db, self.uid, self.gid, 0, self.bet)

        new_bal   = self.db.get_balance(self.uid, self.gid)
        result_lbl = "Under 7" if total < 7 else ("Exactly 7" if total == 7 else "Over 7")

        embed = discord.Embed(
            title=f"🎲 {ds}  =  **{total}**  —  {result_lbl}",
            color=var.COLOR_WIN if won else var.COLOR_LOSE,
        )

        if won:
            embed.description = (
                f"You bet **{_LABEL[choice]}** — **WIN!** 🎉\n\n"
                f"Won {sym} **{profit:,}** {var.CURRENCY_NAME}! (**{mult}×**)"
            )
        else:
            embed.description = (
                f"You bet **{_LABEL[choice]}** — **LOSE** 💀\n\n"
                f"Lost {sym} **{self.bet:,}** {var.CURRENCY_NAME}."
            )

        embed.add_field(name="Your bet",  value=f"**{_LABEL[choice]}** *(range: {_RANGE[choice]})*", inline=True)
        embed.add_field(name="Balance",   value=f"{sym} {new_bal:,}",                                inline=True)
        if won and ev_mult > 1.0:
            embed.add_field(name="💰 Event bonus", value=f"**{ev_mult}×** applied!", inline=False)
        embed.set_footer(text=f"{interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()

        await interaction.response.edit_message(embed=embed, view=self)

        if won:
            pub = (
                f"🎲 **{interaction.user.display_name}** rolled **{total}** in Under/Over "
                f"and won {sym} **{profit:,}**! *(bet: {_LABEL[choice]} · {mult}×)*"
                + (f" *(💰 {ev_mult}× event!)*" if ev_mult > 1.0 else "")
            )
            await interaction.channel.send(embed=discord.Embed(description=pub, color=var.COLOR_WIN))

    @discord.ui.button(label="🔽 Under 7  •  2.2×", style=discord.ButtonStyle.primary)
    async def under(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, "under")

    @discord.ui.button(label="7️⃣ Exactly 7  •  5.5×", style=discord.ButtonStyle.secondary)
    async def exact(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, "exact")

    @discord.ui.button(label="🔼 Over 7  •  2.2×", style=discord.ButtonStyle.primary)
    async def over(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, "over")

    async def on_timeout(self):
        if self.resolved:
            return
        self.resolved = True
        for item in self.children:
            item.disabled = True
        self.db.update_balance(self.uid, self.gid, self.bet, 'refund')
        bot_uid = str(self.cog.bot.user.id)
        _house_tx(self.db, bot_uid, self.gid, -self.bet, 'house_refund')
        embed = discord.Embed(
            title="⏰ Timed Out — Bet Refunded",
            description=f"You didn't choose in time. {var.CURRENCY_SYMBOL} {self.bet:,} refunded.",
            color=var.COLOR_ERROR,
        )
        try:
            await self.interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            pass


class UnderOverCog(commands.Cog):

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
        name="underover",
        description="Roll 2 dice — bet Under 7, Exactly 7, or Over 7!",
    )
    @app_commands.describe(amount="Amount to bet")
    async def underover(self, interaction: discord.Interaction, amount: int):
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

        view  = UnderOverView(self, interaction, amount)
        embed = discord.Embed(
            title="🎲 Under/Over — Two Dice",
            description=(
                f"**Bet:** {sym} {amount:,}\n\n"
                f"Two dice will be rolled. Pick your bet:\n\n"
                f"| Bet | Range | Pays |\n"
                f"|-----|-------|------|\n"
                f"| 🔽 Under 7 | 2 – 6 | **{var.PAYOUT_UNDER}×** |\n"
                f"| 7️⃣ Exactly 7 | = 7 | **{var.PAYOUT_EXACT}×** |\n"
                f"| 🔼 Over 7 | 8 – 12 | **{var.PAYOUT_OVER}×** |\n"
            ),
            color=var.COLOR_PLAYING,
        )
        embed.set_footer(text=f"{name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(UnderOverCog(bot))
    log.info("✅ Casino/UnderOver cog loaded")
