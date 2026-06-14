import asyncio
import importlib.util as _ilu
import random
import time
from datetime import datetime
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

_spec = _ilu.spec_from_file_location('coinflip_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def _validate_bet(db, uid: str, gid: str, amount: int):
    if amount <= 0:
        return "Please enter a valid bet amount."
    if amount < var.MIN_BET:
        return f"Minimum bet is {var.CURRENCY_SYMBOL} **{var.MIN_BET:,}** {var.CURRENCY_NAME}."
    if var.MAX_BET > 0 and amount > var.MAX_BET:
        return f"Maximum bet is {var.CURRENCY_SYMBOL} **{var.MAX_BET:,}** {var.CURRENCY_NAME}."
    balance = db.get_balance(uid, gid)
    if balance < amount:
        return f"You only have {var.CURRENCY_SYMBOL} **{balance:,}** {var.CURRENCY_NAME}."
    return None


# ── vs-bot choice view ────────────────────────────────────────────────────────

class _BotChoiceView(discord.ui.View):
    """Heads / Tails pick buttons for the vs-bot game (ephemeral)."""

    def __init__(self, cog: "CoinFlipCog", uid: str, gid: str, amount: int):
        super().__init__(timeout=30.0)
        self.cog    = cog
        self.uid    = uid
        self.gid    = gid
        self.amount = amount
        self.done   = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.uid:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return False
        if self.done:
            return False
        return True

    @discord.ui.button(label="🪙 Heads", style=discord.ButtonStyle.primary)
    async def heads(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, "heads")

    @discord.ui.button(label="🌑 Tails", style=discord.ButtonStyle.secondary)
    async def tails(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, "tails")

    async def _resolve(self, interaction: discord.Interaction, pick: str):
        self.done = True
        self.stop()

        db      = self.cog.db
        bot_uid = str(self.cog.bot.user.id)
        name    = interaction.user.display_name
        dm_mult = getattr(self.cog.bot, 'multiplier_event_mult', None) or 1.0

        # 48 % win chance — if player wins, coin shows their pick; otherwise shows opposite
        player_wins  = random.randint(1, 100) <= var.WIN_CHANCE
        coin_result  = pick if player_wins else ("tails" if pick == "heads" else "heads")
        coin_display = "🪙 Heads" if coin_result == "heads" else "🌑 Tails"
        pick_display = "🪙 Heads" if pick == "heads" else "🌑 Tails"

        # Show flip animation
        for item in self.children:
            item.disabled = True
        flip_embed = discord.Embed(
            title="🪙 Flipping…",
            description=f"You picked **{pick_display}** — coin is in the air!",
            color=0xF1C40F,
        )
        await interaction.response.edit_message(embed=flip_embed, view=self)
        await asyncio.sleep(1.5)

        if player_wins:
            profit = int(self.amount * (var.WIN_MULTIPLIER - 1))
            if dm_mult > 1.0:
                profit = int(profit * dm_mult)
            db.update_balance(self.uid, self.gid, profit, 'win')
            _house_tx(db, bot_uid, self.gid, -profit, 'house_payout')
            _record_stats(db, self.uid, self.gid, profit, 0)
            new_bal = db.get_balance(self.uid, self.gid)
            embed = discord.Embed(title=f"🎉 You Won! — {coin_display}", color=var.COLOR_WIN)
            embed.add_field(name="Your Pick",   value=pick_display,                                inline=True)
            embed.add_field(name="Bet",         value=f"{var.CURRENCY_SYMBOL} {self.amount:,}",   inline=True)
            embed.add_field(name="Profit",      value=f"{var.CURRENCY_SYMBOL} {profit:,}",        inline=True)
            embed.add_field(name="New Balance", value=f"{var.CURRENCY_SYMBOL} {new_bal:,} {var.CURRENCY_NAME}", inline=False)
            if dm_mult > 1.0:
                embed.add_field(name="💰 Event Bonus", value=f"**{dm_mult}x** multiplier applied!", inline=False)
            pub_desc = f"🪙 **{name}** won {var.CURRENCY_SYMBOL} **{profit:,}** on Coin Flip!"
            if dm_mult > 1.0:
                pub_desc += f" *(💰 {dm_mult}x event!)*"
        else:
            db.update_balance(self.uid, self.gid, -self.amount, 'loss')
            _house_tx(db, bot_uid, self.gid, self.amount, 'house_gain')
            _record_stats(db, self.uid, self.gid, 0, self.amount)
            new_bal = db.get_balance(self.uid, self.gid)
            embed = discord.Embed(title=f"💸 You Lost! — {coin_display}", color=var.COLOR_LOSE)
            embed.add_field(name="Your Pick",   value=pick_display,                                inline=True)
            embed.add_field(name="Bet",         value=f"{var.CURRENCY_SYMBOL} {self.amount:,}",   inline=True)
            embed.add_field(name="Chance",      value=f"{var.WIN_CHANCE}%",                        inline=True)
            embed.add_field(name="New Balance", value=f"{var.CURRENCY_SYMBOL} {new_bal:,} {var.CURRENCY_NAME}", inline=False)
            pub_desc = f"🪙 **{name}** lost {var.CURRENCY_SYMBOL} **{self.amount:,}** on Coin Flip."

        embed.set_footer(text=f"Played by {name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.edit_original_response(embed=embed, view=self)

        if interaction.channel:
            await interaction.channel.send(embed=discord.Embed(
                description=pub_desc,
                color=var.COLOR_WIN if player_wins else var.COLOR_LOSE,
            ))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


# ── PvP challenge view ────────────────────────────────────────────────────────

class _ChallengeView(discord.ui.View):
    """Accept / Decline buttons shown to the challenged user."""

    def __init__(self, cog: "CoinFlipCog", challenger: discord.Member,
                 challengee: discord.Member, amount: int, gid: str):
        super().__init__(timeout=float(var.CHALLENGE_TIMEOUT))
        self.cog        = cog
        self.challenger = challenger
        self.challengee = challengee
        self.amount     = amount
        self.gid        = gid
        self.resolved   = False
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.challengee.id:
            await interaction.response.send_message(
                "❌ This challenge isn't for you!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.resolved:
            return
        db  = self.cog.db
        uid = str(interaction.user.id)
        err = _validate_bet(db, uid, self.gid, self.amount)
        if err:
            await interaction.response.send_message(f"❌ {err}", ephemeral=True)
            return

        self.resolved = True
        self.stop()

        db.update_balance(uid, self.gid, -self.amount, 'coinflip_bet')
        _house_tx(db, str(self.cog.bot.user.id), self.gid, self.amount, 'pvp_hold')

        challenger_wins = random.random() < 0.5
        winner = self.challenger if challenger_wins else self.challengee
        loser  = self.challengee if challenger_wins else self.challenger
        w_uid  = str(winner.id)
        l_uid  = str(loser.id)
        side   = "🪙 Heads" if challenger_wins else "🌑 Tails"

        db.update_balance(w_uid, self.gid, self.amount * 2, 'coinflip_win')
        _house_tx(db, str(self.cog.bot.user.id), self.gid, -(self.amount * 2), 'pvp_payout')
        _record_stats(db, w_uid, self.gid, self.amount, 0)
        _record_stats(db, l_uid, self.gid, 0, self.amount)

        for item in self.children:
            item.disabled = True
        flip_embed = discord.Embed(
            title="🪙 Flipping coin…",
            description="*The coin is in the air!*",
            color=0xF1C40F,
        )
        await interaction.response.edit_message(embed=flip_embed, view=self)
        await asyncio.sleep(1.5)

        w_bal = db.get_balance(w_uid, self.gid)
        l_bal = db.get_balance(l_uid, self.gid)
        result_embed = discord.Embed(
            title=f"🪙 Coin Flip — {side}",
            color=var.COLOR_WIN,
        )
        result_embed.add_field(
            name="🏆 Winner",
            value=f"{winner.mention} wins {var.CURRENCY_SYMBOL} **{self.amount:,}**!",
            inline=False,
        )
        result_embed.add_field(
            name=f"{winner.display_name} balance",
            value=f"{var.CURRENCY_SYMBOL} {w_bal:,} {var.CURRENCY_NAME}",
            inline=True,
        )
        result_embed.add_field(
            name=f"{loser.display_name} balance",
            value=f"{var.CURRENCY_SYMBOL} {l_bal:,} {var.CURRENCY_NAME}",
            inline=True,
        )
        result_embed.set_footer(
            text=f"{self.challenger.display_name} vs {self.challengee.display_name} · {var.SERVER_NAME}"
        )
        result_embed.timestamp = datetime.utcnow()
        await interaction.message.edit(embed=result_embed, view=self)

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.resolved:
            return
        self.resolved = True
        self.stop()
        self._refund_challenger()
        for item in self.children:
            item.disabled = True
        embed = discord.Embed(
            description=(
                f"❌ **{self.challengee.display_name}** declined the coin flip.\n"
                f"{var.CURRENCY_SYMBOL} **{self.amount:,}** refunded to {self.challenger.mention}."
            ),
            color=var.COLOR_ERROR,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        if self.resolved:
            return
        self.resolved = True
        self._refund_challenger()
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                embed = discord.Embed(
                    description=(
                        f"⏰ Challenge expired — **{self.challengee.display_name}** didn't respond.\n"
                        f"{var.CURRENCY_SYMBOL} **{self.amount:,}** refunded to {self.challenger.mention}."
                    ),
                    color=var.COLOR_ERROR,
                )
                await self.message.edit(embed=embed, view=self)
            except Exception:
                pass

    def _refund_challenger(self):
        db      = self.cog.db
        c_uid   = str(self.challenger.id)
        bot_uid = str(self.cog.bot.user.id)
        db.update_balance(c_uid, self.gid, self.amount, 'refund')
        _house_tx(db, bot_uid, self.gid, -self.amount, 'pvp_refund')


# ── Cog ───────────────────────────────────────────────────────────────────────

class CoinFlipCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    @app_commands.command(name="coinflip", description="Flip a coin — pick Heads or Tails, or challenge another user!")
    @app_commands.describe(
        amount="Amount to bet",
        user="User to challenge (leave empty to play against the bot)",
    )
    async def coinflip(
        self,
        interaction: discord.Interaction,
        amount: int,
        user: discord.Member | None = None,
    ):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)
        self.db.ensure_user(uid, gid, interaction.user.display_name)

        if user is not None and user.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't challenge yourself!", ephemeral=True)
            return

        if user is not None and user.bot:
            await interaction.response.send_message(
                "❌ You can't challenge a bot — leave the user field empty to play against me!",
                ephemeral=True,
            )
            return

        err = _validate_bet(self.db, uid, gid, amount)
        if err:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ Invalid Bet", description=err, color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        if user is None:
            await self._vs_bot(interaction, uid, gid, amount)
        else:
            await self._vs_user(interaction, uid, gid, amount, user)

    # ── vs bot ────────────────────────────────────────────────────────────────

    async def _vs_bot(self, interaction: discord.Interaction, uid: str, gid: str, amount: int):
        view = _BotChoiceView(self, uid, gid, amount)
        embed = discord.Embed(
            title="🪙 Coin Flip — Pick a Side!",
            description=f"**Bet:** {var.CURRENCY_SYMBOL} **{amount:,}** {var.CURRENCY_NAME}\n\nChoose Heads or Tails!",
            color=var.COLOR_INFO,
        )
        embed.set_footer(text=f"Played by {interaction.user.display_name} · {var.SERVER_NAME}")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ── vs user ───────────────────────────────────────────────────────────────

    async def _vs_user(
        self,
        interaction: discord.Interaction,
        uid: str,
        gid: str,
        amount: int,
        target: discord.Member,
    ):
        bot_uid = str(self.bot.user.id)
        self.db.ensure_user(uid, gid, interaction.user.display_name)

        self.db.update_balance(uid, gid, -amount, 'coinflip_bet')
        _house_tx(self.db, bot_uid, gid, amount, 'pvp_hold')

        end_ts = int(time.time()) + var.CHALLENGE_TIMEOUT
        view   = _ChallengeView(self, interaction.user, target, amount, gid)
        embed  = discord.Embed(
            title="🪙 Coin Flip Challenge!",
            description=(
                f"{target.mention}, **{interaction.user.display_name}** challenges you to a coin flip!\n\n"
                f"**Bet:** {var.CURRENCY_SYMBOL} **{amount:,}** {var.CURRENCY_NAME} each\n"
                f"**Winner takes:** {var.CURRENCY_SYMBOL} **{amount * 2:,}**\n\n"
                f"Expires <t:{end_ts}:R>"
            ),
            color=var.COLOR_INFO,
        )
        embed.set_footer(text=f"Challenge by {interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()
        view.message = msg


async def setup(bot: commands.Bot):
    await bot.add_cog(CoinFlipCog(bot))
    print("✅ Casino/CoinFlip cog loaded successfully")
