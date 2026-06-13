import discord
from discord.ext import commands
from discord import app_commands
import random
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('cr_variables', Path(__file__).parent / 'variables.py')
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


class CrossyRoadView(discord.ui.View):

    def __init__(
        self,
        cog: "CrossyRoadCog",
        original_interaction: discord.Interaction,
        bet: int,
        user_id: int,
        guild_id: str,
    ):
        super().__init__(timeout=var.BUTTON_TIMEOUT)
        self.cog                  = cog
        self.original_interaction = original_interaction
        self.bet                  = bet
        self.user_id              = user_id
        self.guild_id             = guild_id
        self.lanes_crossed        = 0
        self.max_lanes            = len(var.LANE_MULTIPLIERS)
        self.finished             = False

    def _current_payout(self) -> int:
        if self.lanes_crossed == 0:
            return self.bet
        return int(self.bet * var.LANE_MULTIPLIERS[self.lanes_crossed - 1])

    def _build_embed(self, *, hit_lane: int | None = None, completed: bool = False) -> discord.Embed:
        sym   = var.CURRENCY_SYMBOL
        lines = []

        home_icon = "🏠✅" if completed else "🏠"
        lines.append(f"{home_icon} **Home**")

        for lane_num in range(self.max_lanes, 0, -1):
            payout = int(self.bet * var.LANE_MULTIPLIERS[lane_num - 1])
            if hit_lane == lane_num:
                lines.append(f"🚗 **Lane {lane_num}** · {sym} {payout:,}")
            elif self.lanes_crossed >= lane_num:
                lines.append(f"✅ **Lane {lane_num}** · {sym} {payout:,}")
            elif lane_num == self.lanes_crossed + 1 and not self.finished:
                lines.append(f"🐔 **Lane {lane_num}** · {sym} {payout:,}")
            else:
                lines.append(f"🛣️  **Lane {lane_num}** · {sym} {payout:,}")

        lines.append(f"🏁 **Start** · {sym} {self.bet:,}")

        if self.lanes_crossed > 0 and not completed and hit_lane is None:
            lines.append(f"\n**Current value:** {sym} {self._current_payout():,}")
        elif self.lanes_crossed == 0 and not self.finished:
            lines.append(f"\nCross all {self.max_lanes} lanes to win big!")

        if hit_lane:
            color = var.COLOR_LOSE
        elif completed or (self.lanes_crossed > 0 and self.finished):
            color = var.COLOR_WIN
        else:
            color = var.COLOR_PLAYING

        embed = discord.Embed(
            title=f"🐔 Crossy Road — {sym} {self.bet:,}",
            description="\n".join(lines),
            color=color,
        )
        embed.set_footer(text=f"{var.CAR_CHANCE}% car chance per lane · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        return embed

    async def _finish(
        self,
        interaction: discord.Interaction,
        *,
        hit_lane: int | None = None,
        completed: bool = False,
    ):
        self.finished = True
        for item in self.children:
            item.disabled = True

        uid     = str(self.user_id)
        gid     = self.guild_id
        bot_uid = str(interaction.client.user.id)
        sym     = var.CURRENCY_SYMBOL
        name    = interaction.user.display_name

        if hit_lane is not None:
            _record_stats(self.cog.db, uid, gid, 0, self.bet)
            embed = self._build_embed(hit_lane=hit_lane)
            embed.description += f"\n\n💥 **WHAM!** You lost {sym} {self.bet:,}."
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.channel.send(
                f"🚗 **{name}** got hit by a car on lane {hit_lane} and lost "
                f"{sym} **{self.bet:,}** playing Crossy Road!"
            )
        else:
            raw_payout = self._current_payout()
            profit     = raw_payout - self.bet
            dm_mult    = getattr(interaction.client, 'multiplier_event_mult', None) or 1.0
            if dm_mult > 1.0 and profit > 0:
                profit     = int(profit * dm_mult)
                raw_payout = self.bet + profit

            self.cog.db.update_balance(uid, gid, raw_payout, 'win')
            _house_tx(self.cog.db, bot_uid, gid, -raw_payout, 'house_payout')
            _record_stats(self.cog.db, uid, gid, profit, 0)

            embed = self._build_embed(completed=completed)
            if completed:
                embed.description += f"\n\n🏠 **Made it home!** You won {sym} {profit:,}!"
            else:
                embed.description += f"\n\n💰 **Cashed out!** +{sym} {profit:,}"
            if dm_mult > 1.0:
                embed.add_field(name="💰 Event Bonus", value=f"**{dm_mult}x** multiplier applied!", inline=False)
            new_balance = self.cog.db.get_balance(uid, gid)
            embed.add_field(name="Balance", value=f"{sym} {new_balance:,}", inline=True)

            await interaction.response.edit_message(embed=embed, view=self)

            lanes_word = f"{self.lanes_crossed} lane{'s' if self.lanes_crossed != 1 else ''}"
            event_note = f" *(💰 {dm_mult}x event)*" if dm_mult > 1.0 else ""
            if completed:
                pub = (
                    f"🏠 **{name}** crossed all {self.lanes_crossed} lanes "
                    f"and won {sym} **{profit:,}** on Crossy Road!{event_note}"
                )
            else:
                pub = (
                    f"🐔 **{name}** crossed {lanes_word} "
                    f"and cashed out {sym} **{profit:,}** on Crossy Road!{event_note}"
                )
            await interaction.channel.send(pub)

        self.stop()

    @discord.ui.button(label="🏃 HOP!", style=discord.ButtonStyle.success)
    async def hop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return

        next_lane = self.lanes_crossed + 1

        if random.randint(1, 100) <= var.CAR_CHANCE:
            await self._finish(interaction, hit_lane=next_lane)
            return

        self.lanes_crossed += 1

        if self.lanes_crossed == self.max_lanes:
            await self._finish(interaction, completed=True)
            return

        embed = self._build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="💰 Cash Out", style=discord.ButtonStyle.primary)
    async def cash_out(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        if self.lanes_crossed == 0:
            await interaction.response.send_message(
                "Cross at least one lane before cashing out!", ephemeral=True
            )
            return
        await self._finish(interaction)

    async def on_timeout(self):
        self.finished = True
        for item in self.children:
            item.disabled = True
        uid     = str(self.user_id)
        gid     = self.guild_id
        bot_uid = str(self.cog.bot.user.id)
        if self.lanes_crossed > 0:
            raw_payout = self._current_payout()
            profit     = raw_payout - self.bet
            self.cog.db.update_balance(uid, gid, raw_payout, 'win')
            _house_tx(self.cog.db, bot_uid, gid, -raw_payout, 'house_payout')
            _record_stats(self.cog.db, uid, gid, profit, 0)
        else:
            self.cog.db.update_balance(uid, gid, self.bet, 'refund')
            _house_tx(self.cog.db, bot_uid, gid, -self.bet, 'house_refund')
        try:
            embed = discord.Embed(
                description="⏰ Game timed out." + (
                    f" Auto-cashed out for {var.CURRENCY_SYMBOL} {self._current_payout():,}."
                    if self.lanes_crossed > 0 else " Bet refunded."
                ),
                color=var.COLOR_ERROR,
            )
            await self.original_interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            pass


class CrossyRoadCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    async def cog_load(self):
        for col in ('games_won', 'games_lost'):
            try:
                self.db.execute(f"ALTER TABLE casino_stats ADD COLUMN {col} INTEGER DEFAULT 0")
            except Exception:
                pass

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        try:
            msg = f"❌ An error occurred: {error}"
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
        except Exception:
            pass

    @app_commands.command(name="crossyroad", description="Hop across traffic lanes — cash out before you get hit!")
    @app_commands.describe(amount="Amount to bet")
    async def crossyroad(self, interaction: discord.Interaction, amount: int):
        uid  = str(interaction.user.id)
        gid  = str(interaction.guild_id)
        name = interaction.user.display_name
        sym  = var.CURRENCY_SYMBOL

        self.db.ensure_user(uid, gid, name)

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

        bot_uid = str(interaction.client.user.id)
        self.db.update_balance(uid, gid, -amount, 'bet')
        _house_tx(self.db, bot_uid, gid, amount, 'house_gain')

        view  = CrossyRoadView(self, interaction, amount, interaction.user.id, gid)
        embed = view._build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CrossyRoadCog(bot))
    log.info("✅ Casino/CrossyRoad cog loaded")
