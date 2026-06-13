import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import variables as var
from forge_db import ForgeDB

# ============================================================================
# HELPERS
# ============================================================================

def _record_stats(db, uid: str, gid: str, won: int = 0, lost: int = 0):
    db.execute(
        """INSERT INTO casino_stats (user_id, guild_id, games_played, total_won, total_lost)
           VALUES (?, ?, 1, ?, ?)
           ON CONFLICT(user_id, guild_id) DO UPDATE SET
               games_played = games_played + 1,
               total_won    = total_won    + excluded.total_won,
               total_lost   = total_lost   + excluded.total_lost""",
        (uid, gid, won, lost),
    )

# ============================================================================
# CASINO COG CLASS
# ============================================================================

class GambleCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    @app_commands.command(name="gamble", description=f"Gamble your {var.CURRENCY_NAME} for a chance to win!")
    @app_commands.describe(amount=f"Amount of {var.CURRENCY_NAME} to gamble")
    async def gamble(self, interaction: discord.Interaction, amount: int):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)
        self.db.ensure_user(uid, gid, interaction.user.display_name)

        if amount <= 0:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ Invalid Bet", description=var.MESSAGE_INVALID_BET, color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        if amount < var.MIN_BET:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Bet Too Low",
                    description=var.MESSAGE_BET_TOO_LOW.format(min_bet=var.MIN_BET, currency=var.CURRENCY_NAME),
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        if var.MAX_BET > 0 and amount > var.MAX_BET:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Bet Too High",
                    description=var.MESSAGE_BET_TOO_HIGH.format(max_bet=var.MAX_BET, currency=var.CURRENCY_NAME),
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        balance = self.db.get_balance(uid, gid)
        if balance < amount:
            embed = discord.Embed(
                title="❌ Insufficient Funds",
                description=var.MESSAGE_INSUFFICIENT_FUNDS.format(currency=var.CURRENCY_NAME),
                color=var.COLOR_ERROR,
            )
            embed.add_field(name="Your Balance", value=f"{var.CURRENCY_SYMBOL} {balance:,} {var.CURRENCY_NAME}", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        roll = random.randint(1, 100)
        won  = roll <= var.WIN_CHANCE

        if won:
            winnings = int(amount * var.WIN_MULTIPLIER)
            profit   = winnings - amount
            self.db.update_balance(uid, gid, profit, 'win')
            _record_stats(self.db, uid, gid, profit, 0)
            new_balance = self.db.get_balance(uid, gid)
            embed = discord.Embed(
                title="🎉 YOU WON!",
                description=var.MESSAGE_WIN.format(amount=f"{profit:,}", currency=var.CURRENCY_NAME),
                color=var.COLOR_WIN,
            )
            embed.add_field(name="Roll",        value=f"{roll}/100",                           inline=True)
            embed.add_field(name="Bet",         value=f"{var.CURRENCY_SYMBOL} {amount:,}",     inline=True)
            embed.add_field(name="Winnings",    value=f"{var.CURRENCY_SYMBOL} {winnings:,}",   inline=True)
            embed.add_field(name="New Balance", value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}", inline=False)
        else:
            self.db.update_balance(uid, gid, -amount, 'loss')
            _record_stats(self.db, uid, gid, 0, amount)
            new_balance = self.db.get_balance(uid, gid)
            embed = discord.Embed(
                title="💸 YOU LOST!",
                description=var.MESSAGE_LOSE.format(amount=f"{amount:,}", currency=var.CURRENCY_NAME),
                color=var.COLOR_LOSE,
            )
            embed.add_field(name="Roll",        value=f"{roll}/100",                           inline=True)
            embed.add_field(name="Lost",        value=f"{var.CURRENCY_SYMBOL} {amount:,}",     inline=True)
            embed.add_field(name="Win Chance",  value=f"{var.WIN_CHANCE}%",                    inline=True)
            embed.add_field(name="New Balance", value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}", inline=False)

        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        if interaction.channel:
            pub = discord.Embed(
                description=(
                    f"🎲 **{interaction.user.display_name}** won {var.CURRENCY_SYMBOL} **{profit:,}** playing Gamble!"
                    if won else
                    f"🎲 **{interaction.user.display_name}** lost {var.CURRENCY_SYMBOL} **{amount:,}** playing Gamble"
                ),
                color=var.COLOR_WIN if won else var.COLOR_LOSE,
            )
            await interaction.channel.send(embed=pub)



async def setup(bot: commands.Bot):
    await bot.add_cog(GambleCog(bot))
    print("✅ Casino/Gamble cog loaded successfully")
