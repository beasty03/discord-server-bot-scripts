import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('rocket_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")


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


def _generate_crash() -> float:
    """Crash point using house-edged geometric distribution. ~50% crash before 2×."""
    r = random.random()
    if r < 0.01:   # 1% instant crash — guaranteed house edge
        return 1.0
    return max(1.01, round(0.99 / (1.0 - r), 2))


class RocketView(discord.ui.View):

    def __init__(self, cog, interaction: discord.Interaction, bet: int, crash_at: float):
        super().__init__(timeout=var.BUTTON_TIMEOUT)
        self.cog          = cog
        self.db           = cog.db
        self.interaction  = interaction
        self.bet          = bet
        self.crash_at     = crash_at
        self.uid          = str(interaction.user.id)
        self.gid          = str(interaction.guild_id)
        self.current_mult = 1.0
        self.cashed_out   = False
        self.crashed      = False
        self.task         = None

    def _build_embed(self, mult: float, desc: str = "") -> discord.Embed:
        payout = int(self.bet * mult)
        embed  = discord.Embed(
            title=f"🚀 Rocket  •  {mult:.2f}×",
            description=(
                f"{desc}\n\n"
                f"**Bet:** {var.CURRENCY_SYMBOL} {self.bet:,}\n"
                f"**Cash out now for:** {var.CURRENCY_SYMBOL} {payout:,}  *(+{payout - self.bet:,})*"
            ).strip(),
            color=var.COLOR_PLAYING,
        )
        embed.set_footer(text=f"{self.interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        return embed

    # ── Cash out (button) ──────────────────────────────────────────────────────

    @discord.ui.button(label="🚀 CASH OUT  •  1.00×", style=discord.ButtonStyle.green)
    async def cashout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != int(self.uid):
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        if self.cashed_out or self.crashed:
            await interaction.response.defer()
            return

        self.cashed_out = True
        if self.task:
            self.task.cancel()

        mult   = self.current_mult
        payout = int(self.bet * mult)
        profit = payout - self.bet

        ev_mult = getattr(interaction.client, 'multiplier_event_mult', None) or 1.0
        if ev_mult > 1.0:
            profit = int(profit * ev_mult)
            payout = self.bet + profit

        bot_uid = str(interaction.client.user.id)
        self.db.update_balance(self.uid, self.gid, payout, 'win')
        _house_tx(self.db, bot_uid, self.gid, -payout, 'house_payout')
        _record_stats(self.db, self.uid, self.gid, profit, 0)

        new_bal  = self.db.get_balance(self.uid, self.gid)
        button.label    = f"✅ Cashed out at {mult:.2f}×"
        button.style    = discord.ButtonStyle.success
        button.disabled = True

        embed = discord.Embed(
            title=f"✅ Cashed out at {mult:.2f}×!",
            description=f"You won {var.CURRENCY_SYMBOL} **{profit:,}** {var.CURRENCY_NAME}!",
            color=var.COLOR_WIN,
        )
        embed.add_field(name="Multiplier",  value=f"**{mult:.2f}×**",                      inline=True)
        embed.add_field(name="Payout",      value=f"{var.CURRENCY_SYMBOL} {payout:,}",     inline=True)
        embed.add_field(name="Balance",     value=f"{var.CURRENCY_SYMBOL} {new_bal:,}",    inline=True)
        if ev_mult > 1.0:
            embed.add_field(name="💰 Event bonus", value=f"**{ev_mult}×** applied!", inline=False)
        embed.set_footer(text=f"{interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.channel.send(embed=discord.Embed(
            description=(
                f"🚀 **{interaction.user.display_name}** cashed out at **{mult:.2f}×** "
                f"and won {var.CURRENCY_SYMBOL} **{profit:,}**!"
                + (f" *(💰 {ev_mult}× event!)*" if ev_mult > 1.0 else "")
            ),
            color=var.COLOR_WIN,
        ))

    # ── Background tick task ───────────────────────────────────────────────────

    async def _run_rocket(self):
        try:
            for mult in var.TICK_STAGES[1:]:
                await asyncio.sleep(var.TICK_DELAY)
                if self.cashed_out or self.crashed:
                    return
                if mult >= self.crash_at:
                    await self._do_crash()
                    return
                self.current_mult = mult
                self.children[0].label = f"🚀 CASH OUT  •  {mult:.2f}×"
                try:
                    await self.interaction.edit_original_response(
                        embed=self._build_embed(mult, "🚀 Flying — cash out before it crashes!"),
                        view=self,
                    )
                except Exception:
                    return
            # Exhausted all stages without crashing
            if not self.cashed_out and not self.crashed:
                self.crash_at = var.TICK_STAGES[-1]
                await self._do_crash()
        except asyncio.CancelledError:
            pass

    async def _do_crash(self):
        if self.cashed_out:
            return
        self.crashed = True

        bot_uid = str(self.cog.bot.user.id)
        _record_stats(self.db, self.uid, self.gid, 0, self.bet)

        self.children[0].label    = f"💥 Crashed at {self.crash_at:.2f}×"
        self.children[0].style    = discord.ButtonStyle.danger
        self.children[0].disabled = True

        embed = discord.Embed(
            title=f"💥 Rocket crashed at {self.crash_at:.2f}×!",
            description=f"Lost {var.CURRENCY_SYMBOL} **{self.bet:,}** {var.CURRENCY_NAME}.",
            color=var.COLOR_LOSE,
        )
        embed.add_field(name="Crash point", value=f"**{self.crash_at:.2f}×**",          inline=True)
        embed.add_field(name="Last safe",   value=f"**{self.current_mult:.2f}×**",       inline=True)
        embed.set_footer(text=f"{self.interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        try:
            await self.interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            pass
        try:
            await self.interaction.channel.send(embed=discord.Embed(
                description=(
                    f"💥 **{self.interaction.user.display_name}**'s rocket crashed at "
                    f"**{self.crash_at:.2f}×** — lost {var.CURRENCY_SYMBOL} **{self.bet:,}**!"
                ),
                color=var.COLOR_LOSE,
            ))
        except Exception:
            pass

    # ── Timeout ────────────────────────────────────────────────────────────────

    async def on_timeout(self):
        if self.cashed_out or self.crashed:
            return
        self.crashed = True
        if self.task:
            self.task.cancel()
        _record_stats(self.db, self.uid, self.gid, 0, self.bet)
        self.children[0].label    = "💥 Timed Out"
        self.children[0].disabled = True
        embed = discord.Embed(
            title="⏰ Timed Out — Rocket Crashed!",
            description=f"You took too long to cash out. Lost {var.CURRENCY_SYMBOL} **{self.bet:,}**.",
            color=var.COLOR_LOSE,
        )
        try:
            await self.interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            pass


class RocketCog(commands.Cog):

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
        name="rocket",
        description="Watch the multiplier climb — cash out before the rocket crashes!",
    )
    @app_commands.describe(amount="Amount to bet")
    async def rocket(self, interaction: discord.Interaction, amount: int):
        uid  = str(interaction.user.id)
        gid  = str(interaction.guild_id)
        name = interaction.user.display_name

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

        bot_uid  = str(interaction.client.user.id)
        self.db.update_balance(uid, gid, -amount, 'bet')
        _house_tx(self.db, bot_uid, gid, amount, 'house_gain')

        crash_at = _generate_crash()
        view     = RocketView(self, interaction, amount, crash_at)

        await interaction.response.send_message(
            embed=view._build_embed(1.0, "🚀 Launching — cash out before it crashes!"),
            view=view, ephemeral=True,
        )
        view.task = asyncio.create_task(view._run_rocket())


async def setup(bot):
    await bot.add_cog(RocketCog(bot))
    log.info("✅ Casino/Rocket cog loaded")
