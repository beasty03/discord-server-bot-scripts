import discord
from discord.ext import commands
from discord import app_commands
import random
import math
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('dm_variables', Path(__file__).parent / 'variables.py')
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


def _calc_multiplier(mines: int, safe_picked: int, grid: int = 16) -> float:
    """Payout multiplier after k safe picks using combinatorics with house edge."""
    if safe_picked == 0:
        return 1.0
    safe_tiles = grid - mines
    if safe_picked > safe_tiles:
        return 0.0
    fair = math.comb(grid, safe_picked) / math.comb(safe_tiles, safe_picked)
    return round(fair * (var.HOUSE_EDGE ** safe_picked), 3)


class MinesView(discord.ui.View):

    def __init__(self, cog, interaction: discord.Interaction, bet: int, mines: int):
        super().__init__(timeout=var.BUTTON_TIMEOUT)
        self.cog          = cog
        self.db           = cog.db
        self.interaction  = interaction
        self.bet          = bet
        self.mines        = mines
        self.uid          = str(interaction.user.id)
        self.gid          = str(interaction.guild_id)
        self.resolved     = False
        self.safe_picked  = 0
        self.mine_pos     = set(random.sample(range(var.GRID_SIZE), mines))
        self.revealed     = set()
        self._build_buttons()

    # ── Button layout ──────────────────────────────────────────────────────────

    def _build_buttons(self):
        self.clear_items()

        for pos in range(var.GRID_SIZE):
            if pos in self.revealed:
                if pos in self.mine_pos:
                    label, style = "💣", discord.ButtonStyle.danger
                else:
                    label, style = "💎", discord.ButtonStyle.success
                disabled = True
            else:
                label, style = "🔲", discord.ButtonStyle.secondary
                disabled     = self.resolved

            btn = discord.ui.Button(
                label=label, style=style,
                row=pos // 4, custom_id=f"tile_{pos}", disabled=disabled,
            )
            btn.callback = self._make_tile_cb(pos)
            self.add_item(btn)

        mult   = _calc_multiplier(self.mines, self.safe_picked)
        payout = int(self.bet * mult)
        cash_btn = discord.ui.Button(
            label=f"💰 Cash Out  •  {mult:.2f}×  (+{payout - self.bet:,})",
            style=discord.ButtonStyle.primary if self.safe_picked > 0 else discord.ButtonStyle.secondary,
            row=4, custom_id="cashout",
            disabled=self.safe_picked == 0 or self.resolved,
        )
        cash_btn.callback = self._cashout_cb
        self.add_item(cash_btn)

    def _make_tile_cb(self, pos: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != int(self.uid):
                await interaction.response.send_message("This isn't your game!", ephemeral=True)
                return
            if self.resolved or pos in self.revealed:
                await interaction.response.defer()
                return
            await self._reveal(interaction, pos)
        return callback

    # ── Tile reveal ────────────────────────────────────────────────────────────

    async def _reveal(self, interaction: discord.Interaction, pos: int):
        if pos in self.mine_pos:
            self.resolved = True
            self.revealed.add(pos)
            for mp in self.mine_pos:   # reveal all mines
                self.revealed.add(mp)
            self._build_buttons()

            bot_uid = str(interaction.client.user.id)
            _record_stats(self.db, self.uid, self.gid, 0, self.bet)

            new_bal = self.db.get_balance(self.uid, self.gid)
            embed = discord.Embed(
                title="💣 BOOM! You hit a mine!",
                description=f"Lost {var.CURRENCY_SYMBOL} **{self.bet:,}** {var.CURRENCY_NAME}.",
                color=var.COLOR_LOSE,
            )
            embed.add_field(name="Safe tiles found", value=f"**{self.safe_picked}**", inline=True)
            embed.add_field(name="New balance",      value=f"{var.CURRENCY_SYMBOL} {new_bal:,}", inline=True)
            embed.set_footer(text=f"{interaction.user.display_name} · {var.SERVER_NAME}")
            embed.timestamp = datetime.utcnow()
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.channel.send(embed=discord.Embed(
                description=f"💣 **{interaction.user.display_name}** hit a mine in Diamond Mines and lost {var.CURRENCY_SYMBOL} **{self.bet:,}**!",
                color=var.COLOR_LOSE,
            ))
        else:
            self.safe_picked += 1
            self.revealed.add(pos)

            safe_tiles = var.GRID_SIZE - self.mines
            mult       = _calc_multiplier(self.mines, self.safe_picked)

            if self.safe_picked == safe_tiles:
                # Found every safe tile — auto-cashout with jackpot
                await self._do_cashout(interaction, auto_jackpot=True)
                return

            self._build_buttons()
            payout = int(self.bet * mult)
            embed = discord.Embed(
                title="💎 Diamond Mines",
                description=(
                    f"**Mines:** {self.mines}  •  **Found:** {self.safe_picked}/{safe_tiles} safe tiles\n"
                    f"**Multiplier:** `{mult:.2f}×`  •  **Cash out for:** {var.CURRENCY_SYMBOL} {payout:,}"
                ),
                color=var.COLOR_PLAYING,
            )
            embed.set_footer(text=f"{interaction.user.display_name} · {var.SERVER_NAME}")
            embed.timestamp = datetime.utcnow()
            await interaction.response.edit_message(embed=embed, view=self)

    # ── Cash out ───────────────────────────────────────────────────────────────

    async def _cashout_cb(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.uid):
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        if self.resolved or self.safe_picked == 0:
            await interaction.response.defer()
            return
        await self._do_cashout(interaction)

    async def _do_cashout(self, interaction: discord.Interaction, auto_jackpot: bool = False):
        self.resolved = True
        self._build_buttons()

        mult   = _calc_multiplier(self.mines, self.safe_picked)
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

        new_bal = self.db.get_balance(self.uid, self.gid)
        title   = f"💎 JACKPOT! All {self.safe_picked} safe tiles cleared!" if auto_jackpot else f"💰 Cashed out at {mult:.2f}×!"
        embed   = discord.Embed(title=title, color=var.COLOR_WIN)
        embed.description = f"You won {var.CURRENCY_SYMBOL} **{profit:,}** {var.CURRENCY_NAME}!"
        embed.add_field(name="Safe tiles", value=f"**{self.safe_picked}**",                    inline=True)
        embed.add_field(name="Multiplier", value=f"**{mult:.2f}×**",                           inline=True)
        embed.add_field(name="Payout",     value=f"{var.CURRENCY_SYMBOL} {payout:,}",          inline=True)
        embed.add_field(name="Balance",    value=f"{var.CURRENCY_SYMBOL} {new_bal:,}",         inline=True)
        if ev_mult > 1.0:
            embed.add_field(name="💰 Event bonus", value=f"**{ev_mult}×** applied!", inline=False)
        embed.set_footer(text=f"{interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.edit_message(embed=embed, view=self)

        pub = (
            f"{'🏆 JACKPOT!' if auto_jackpot else '💎'} **{interaction.user.display_name}** "
            f"cashed out at **{mult:.2f}×** in Diamond Mines and won {var.CURRENCY_SYMBOL} **{profit:,}**!"
            + (f" *(💰 {ev_mult}× event!)*" if ev_mult > 1.0 else "")
        )
        await interaction.channel.send(embed=discord.Embed(description=pub, color=var.COLOR_WIN))

    # ── Timeout ────────────────────────────────────────────────────────────────

    async def on_timeout(self):
        if self.resolved:
            return
        self.resolved = True
        self._build_buttons()

        if self.safe_picked > 0:
            mult   = _calc_multiplier(self.mines, self.safe_picked)
            payout = int(self.bet * mult)
            self.db.update_balance(self.uid, self.gid, payout, 'win')
            bot_uid = str(self.cog.bot.user.id)
            _house_tx(self.db, bot_uid, self.gid, -payout, 'house_payout')
            _record_stats(self.db, self.uid, self.gid, payout - self.bet, 0)
            desc = f"⏰ Timed out — auto cashed out at `{mult:.2f}×` for {var.CURRENCY_SYMBOL} {payout:,}."
        else:
            self.db.update_balance(self.uid, self.gid, self.bet, 'refund')
            bot_uid = str(self.cog.bot.user.id)
            _house_tx(self.db, bot_uid, self.gid, -self.bet, 'house_refund')
            desc = "⏰ Timed out — bet refunded."

        embed = discord.Embed(title="⏰ Game Timed Out", description=desc, color=var.COLOR_ERROR)
        try:
            await self.interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            pass


class DiamondMinesCog(commands.Cog):

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
        name="mines",
        description="Reveal diamonds on a 4×4 grid. Avoid mines and cash out before you explode!",
    )
    @app_commands.describe(
        amount="Amount to bet",
        mines=f"Number of mines on the grid (1–12, default 3)",
    )
    async def mines(self, interaction: discord.Interaction, amount: int, mines: int = 3):
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
        if not (var.MIN_MINES <= mines <= var.MAX_MINES):
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Mines must be between {var.MIN_MINES} and {var.MAX_MINES}.",
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

        safe_tiles = var.GRID_SIZE - mines
        view  = MinesView(self, interaction, amount, mines)
        embed = discord.Embed(
            title="💎 Diamond Mines",
            description=(
                f"**Bet:** {sym} {amount:,}  •  **Mines:** {mines}  •  **Safe tiles:** {safe_tiles}\n\n"
                f"Click tiles to reveal 💎 diamonds. Hit a 💣 mine and you lose everything.\n"
                f"Cash out any time to lock in your multiplier."
            ),
            color=var.COLOR_PLAYING,
        )
        embed.set_footer(text=f"{name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(DiamondMinesCog(bot))
    log.info("✅ Casino/DiamondMines cog loaded")
