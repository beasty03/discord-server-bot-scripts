# bot.py

import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
import time
from datetime import datetime, timedelta
import variables as var

# ============================================================================
# DATABASE SETUP
# ============================================================================

def init_database():
    """Initialize the SQLite database and create tables if they don't exist."""
    conn = sqlite3.connect(var.DATABASE_NAME)
    cursor = conn.cursor()
    
    # Create users table with balance
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER NOT NULL DEFAULT 0,
            total_won INTEGER DEFAULT 0,
            total_lost INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            last_daily REAL DEFAULT 0,
            created_at REAL DEFAULT (julianday('now'))
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {var.DATABASE_NAME}")

def get_user_balance(user_id: int) -> int:
    """Get user balance, create account if doesn't exist."""
    conn = sqlite3.connect(var.DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result is None:
        # Create new user with starting balance
        cursor.execute(
            'INSERT INTO users (user_id, balance) VALUES (?, ?)',
            (user_id, var.STARTING_BALANCE)
        )
        conn.commit()
        conn.close()
        return var.STARTING_BALANCE
    
    conn.close()
    return result[0]

def update_balance(user_id: int, amount: int, won: bool = False):
    """Update user balance and statistics."""
    conn = sqlite3.connect(var.DATABASE_NAME)
    cursor = conn.cursor()
    
    if won:
        cursor.execute('''
            UPDATE users 
            SET balance = balance + ?,
                total_won = total_won + ?,
                games_played = games_played + 1
            WHERE user_id = ?
        ''', (amount, amount, user_id))
    else:
        cursor.execute('''
            UPDATE users 
            SET balance = balance - ?,
                total_lost = total_lost + ?,
                games_played = games_played + 1
            WHERE user_id = ?
        ''', (amount, amount, user_id))
    
    conn.commit()
    conn.close()

def get_user_stats(user_id: int) -> dict:
    """Get user statistics."""
    conn = sqlite3.connect(var.DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT balance, total_won, total_lost, games_played, last_daily
        FROM users WHERE user_id = ?
    ''', (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'balance': result[0],
            'total_won': result[1],
            'total_lost': result[2],
            'games_played': result[3],
            'last_daily': result[4]
        }
    return None

def claim_daily_bonus(user_id: int) -> tuple[bool, int]:
    """Claim daily bonus. Returns (success, time_remaining)."""
    conn = sqlite3.connect(var.DATABASE_NAME)
    cursor = conn.cursor()
    
    # Get user or create
    get_user_balance(user_id)
    
    cursor.execute('SELECT last_daily FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    current_time = time.time()
    last_daily = result[0] if result else 0
    time_since_last = current_time - last_daily
    
    if time_since_last < var.DAILY_BONUS_COOLDOWN:
        conn.close()
        return False, int(var.DAILY_BONUS_COOLDOWN - time_since_last)
    
    # Grant bonus
    cursor.execute('''
        UPDATE users 
        SET balance = balance + ?,
            last_daily = ?
        WHERE user_id = ?
    ''', (var.DAILY_BONUS_AMOUNT, current_time, user_id))
    
    conn.commit()
    conn.close()
    return True, 0

def get_leaderboard(limit: int = 10) -> list:
    """Get top users by balance."""
    conn = sqlite3.connect(var.DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, balance, games_played
        FROM users
        ORDER BY balance DESC
        LIMIT ?
    ''', (limit,))
    
    results = cursor.fetchall()
    conn.close()
    return results

# ============================================================================
# BOT SETUP
# ============================================================================

class GambleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(command_prefix='!', intents=intents)
        
    async def setup_hook(self):
        """Sync commands when bot starts."""
        await self.tree.sync(guild=discord.Object(id=var.GUILD_ID))
        print(f"✅ Commands synced to guild: {var.GUILD_ID}")
    
    async def on_ready(self):
        print(f'✅ Logged in as {self.user} (ID: {self.user.id})')
        print(f'✅ Connected to: {var.SERVER_NAME}')
        print('━' * 50)

bot = GambleBot()

# ============================================================================
# GAMBLE COMMAND
# ============================================================================

@bot.tree.command(
    name="gamble",
    description=f"Gamble your {var.CURRENCY_NAME} for a chance to win!",
    guild=discord.Object(id=var.GUILD_ID)
)
@app_commands.describe(amount=f"Amount of {var.CURRENCY_NAME} to gamble")
async def gamble(interaction: discord.Interaction, amount: int):
    """Gamble command - bet currency for a chance to win."""
    
    user_id = interaction.user.id
    
    # Validate bet amount
    if amount <= 0:
        embed = discord.Embed(
            title="❌ Invalid Bet",
            description=var.MESSAGE_INVALID_BET,
            color=var.COLOR_ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Check minimum bet
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
    
    # Check maximum bet (if enabled)
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
    
    # Get user balance
    balance = get_user_balance(user_id)
    
    # Check if user has enough balance
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
    
    # Determine win/loss
    roll = random.randint(1, 100)
    won = roll <= var.WIN_CHANCE
    
    if won:
        winnings = int(amount * var.WIN_MULTIPLIER)
        profit = winnings - amount
        update_balance(user_id, profit, won=True)
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
        update_balance(user_id, amount, won=False)
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

# ============================================================================
# BALANCE COMMAND
# ============================================================================

@bot.tree.command(
    name="balance",
    description=f"Check your {var.CURRENCY_NAME} balance",
    guild=discord.Object(id=var.GUILD_ID)
)
async def balance(interaction: discord.Interaction):
    """Check user balance and statistics."""
    
    user_id = interaction.user.id
    stats = get_user_stats(user_id)
    
    if not stats:
        balance = get_user_balance(user_id)
        stats = get_user_stats(user_id)
    
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