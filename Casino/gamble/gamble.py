import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime
import sys
from pathlib import Path

# Add Casino folder to path to import variables.py
sys.path.insert(0, str(Path(__file__).parent))
import variables as var
from database_management.database_manager import DatabaseManager  # Import your DatabaseManager

# Initialize the DatabaseManager
db_manager = DatabaseManager()

# ============================================================================
# CASINO COG CLASS
# ============================================================================

class GambleCog(commands.Cog):
    """Casino gambling commands for Discord."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(
        name="gamble",
        description=f"Gamble your {var.CURRENCY_NAME} for a chance to win!"
    )
    @app_commands.describe(amount=f"Amount of {var.CURRENCY_NAME} to gamble")
    async def gamble(self, interaction: discord.Interaction, amount: int):
        """Gamble command - bet currency for a chance to win."""
        
        user_id = interaction.user.id
        
        if amount <= 0:
            embed = discord.Embed(
                title="❌ Invalid Bet",
                description=var.MESSAGE_INVALID_BET,
                color=var.COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if amount < var.MIN_BET:
            embed = discord.Embed(
                title="❌ Bet Too Low",
                description=var.MESSAGE_BET_TOO_LOW.format(
                    min_bet=var.MIN_BET,
                    currency=var.CURRENCY_NAME
                ),
                color=var.COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if var.MAX_BET > 0 and amount > var.MAX_BET:
            embed = discord.Embed(
                title="❌ Bet Too High",
                description=var.MESSAGE_BET_TOO_HIGH.format(
                    max_bet=var.MAX_BET,
                    currency=var.CURRENCY_NAME
                ),
                color=var.COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        balance = db_manager.get_user_balance(user_id)  # Use DatabaseManager

        if balance < amount:
            embed = discord.Embed(
                title="❌ Insufficient Funds",
                description=var.MESSAGE_INSUFFICIENT_FUNDS.format(currency=var.CURRENCY_NAME),
                color=var.COLOR_ERROR
            )
            embed.add_field(
                name=f"Your Balance",
                value=f"{var.CURRENCY_SYMBOL} {balance:,} {var.CURRENCY_NAME}",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        roll = random.randint(1, 100)
        won = roll <= var.WIN_CHANCE
        
        if won:
            winnings = int(amount * var.WIN_MULTIPLIER)
            profit = winnings - amount
            db_manager.update_balance(user_id, profit, won=True)  # Use DatabaseManager
            new_balance = balance + profit
            
            embed = discord.Embed(
                title="🎉 YOU WON!",
                description=var.MESSAGE_WIN.format(
                    amount=f"{profit:,}",
                    currency=var.CURRENCY_NAME
                ),
                color=var.COLOR_WIN
            )
            embed.add_field(name="Roll", value=f"{roll}/100", inline=True)
            embed.add_field(name="Bet", value=f"{var.CURRENCY_SYMBOL} {amount:,}", inline=True)
            embed.add_field(name="Winnings", value=f"{var.CURRENCY_SYMBOL} {winnings:,}", inline=True)
            embed.add_field(
                name="New Balance",
                value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}",
                inline=False
            )
        else:
            db_manager.update_balance(user_id, amount, won=False)  # Use DatabaseManager
            new_balance = balance - amount
            
            embed = discord.Embed(
                title="💸 YOU LOST!",
                description=var.MESSAGE_LOSE.format(
                    amount=f"{amount:,}",
                    currency=var.CURRENCY_NAME
                ),
                color=var.COLOR_LOSE
            )
            embed.add_field(name="Roll", value=f"{roll}/100", inline=True)
            embed.add_field(name="Lost", value=f"{var.CURRENCY_SYMBOL} {amount:,}", inline=True)
            embed.add_field(name="Win Chance", value=f"{var.WIN_CHANCE}%", inline=True)
            embed.add_field(
                name="New Balance",
                value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}",
                inline=False
            )
        
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(
        name="balance",
        description=f"Check your {var.CURRENCY_NAME} balance"
    )
    async def balance(self, interaction: discord.Interaction):
        """Check user balance and statistics."""
        
        user_id = interaction.user.id
        stats = db_manager.get_user_stats(user_id)  # Use DatabaseManager
        
        if not stats:
            balance = db_manager.get_user_balance(user_id)  # Ensure the user is created
            stats = db_manager.get_user_stats(user_id)  # Retrieve stats again
        
        net_profit = stats['total_won'] - stats['total_lost']
        
        embed = discord.Embed(
            title=f"{var.CURRENCY_SYMBOL} Balance",
            description=f"**{interaction.user.display_name}'s** gambling statistics",
            color=var.COLOR_INFO
        )
        
        embed.add_field(
            name="Current Balance",
            value=f"{var.CURRENCY_SYMBOL} {stats['balance']:,} {var.CURRENCY_NAME}",
            inline=False
        )
        
        embed.add_field(name="Games Played", value=f"{stats['games_played']:,}", inline=True)
        embed.add_field(name="Total Won", value=f"{var.CURRENCY_SYMBOL} {stats['total_won']:,}", inline=True)
        embed.add_field(name="Total Lost", value=f"{var.CURRENCY_SYMBOL} {stats['total_lost']:,}", inline=True)
        
        profit_emoji = "📈" if net_profit >= 0 else "📉"
        embed.add_field(
            name=f"{profit_emoji} Net Profit/Loss",
            value=f"{var.CURRENCY_SYMBOL} {net_profit:+,} {var.CURRENCY_NAME}",
            inline=False
        )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(
        name="daily",
        description=f"Claim your daily {var.CURRENCY_NAME} bonus"
    )
    async def daily(self, interaction: discord.Interaction):
        """Claim daily bonus."""
        
        user_id = interaction.user.id
        success, time_remaining = db_manager.claim_daily_bonus(user_id)  # Use DatabaseManager
        
        if success:
            new_balance = db_manager.get_user_balance(user_id)
            embed = discord.Embed(
                title="🎁 Daily Bonus Claimed!",
                description=f"You received **{var.CURRENCY_SYMBOL} {var.DAILY_BONUS_AMOUNT:,} {var.CURRENCY_NAME}**!",
                color=var.COLOR_WIN
            )
            embed.add_field(
                name="New Balance",
                value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}",
                inline=False
            )
            embed.set_footer(text="Come back tomorrow for another bonus!")
        else:
            hours = time_remaining // 3600
            minutes = (time_remaining % 3600) // 60
            embed = discord.Embed(
                title="⏰ Daily Bonus Not Ready",
                description=f"You can claim your next daily bonus in **{hours}h {minutes}m**",
                color=var.COLOR_ERROR
            )
        
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(
        name="leaderboard",
        description="View the top gamblers"
    )
    async def leaderboard(self, interaction: discord.Interaction):
        """Display leaderboard."""
        
        top_users = db_manager.get_leaderboard(var.LEADERBOARD_TOP_COUNT)  # Use DatabaseManager
        
        embed = discord.Embed(
            title=f"🏆 {var.CURRENCY_NAME} Leaderboard",
            description="Top 10 richest gamblers",
            color=var.COLOR_INFO
        )
        
        if not top_users:
            embed.description = "No users found. Start gambling to appear here!"
        else:
            leaderboard_text = ""
            for i, (user_id, balance, games) in enumerate(top_users, 1):
                try:
                    user = await self.bot.fetch_user(user_id)
                    username = user.display_name
                except:
                    username = f"User {user_id}"
                
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                leaderboard_text += f"{medal} **{username}** - {var.CURRENCY_SYMBOL} {balance:,} ({games} games)\n"
            
            embed.description = leaderboard_text
        
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

# ============================================================================
# COG SETUP FUNCTION
# ============================================================================

async def setup(bot: commands.Bot):
    """
    Setup function to load this cog.
    Required for the launcher to load this module.
    """
    # Add the cog to the bot
    await bot.add_cog(GambleCog(bot))
    
    print("✅ Casino/Gamble cog loaded successfully")