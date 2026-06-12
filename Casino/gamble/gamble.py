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
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="balance", description=f"Check your {var.CURRENCY_NAME} balance")
    async def balance(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)
        self.db.ensure_user(uid, gid, interaction.user.display_name)

        balance = self.db.get_balance(uid, gid)
        rows    = self.db.execute(
            "SELECT games_played, total_won, total_lost FROM casino_stats WHERE user_id = ? AND guild_id = ?",
            (uid, gid),
        )
        games_played = rows[0][0] if rows else 0
        total_won    = rows[0][1] if rows else 0
        total_lost   = rows[0][2] if rows else 0
        net          = total_won - total_lost

        embed = discord.Embed(
            title=f"{var.CURRENCY_SYMBOL} Balance",
            description=f"**{interaction.user.display_name}'s** gambling statistics",
            color=var.COLOR_INFO,
        )
        embed.add_field(name="Current Balance", value=f"{var.CURRENCY_SYMBOL} {balance:,} {var.CURRENCY_NAME}", inline=False)
        embed.add_field(name="Games Played",    value=f"{games_played:,}",                                       inline=True)
        embed.add_field(name="Total Won",       value=f"{var.CURRENCY_SYMBOL} {total_won:,}",                    inline=True)
        embed.add_field(name="Total Lost",      value=f"{var.CURRENCY_SYMBOL} {total_lost:,}",                   inline=True)
        embed.add_field(
            name=f"{'📈' if net >= 0 else '📉'} Net Profit/Loss",
            value=f"{var.CURRENCY_SYMBOL} {net:+,} {var.CURRENCY_NAME}",
            inline=False,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description=f"Claim your daily {var.CURRENCY_NAME} bonus")
    async def daily(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)
        self.db.ensure_user(uid, gid, interaction.user.display_name)

        balance_before          = self.db.get_balance(uid, gid)
        success, time_remaining = self.db.claim_daily(uid, gid)

        if success:
            new_balance  = self.db.get_balance(uid, gid)
            bonus_amount = new_balance - balance_before
            embed = discord.Embed(
                title="🎁 Daily Bonus Claimed!",
                description=f"You received **{var.CURRENCY_SYMBOL} {bonus_amount:,} {var.CURRENCY_NAME}**!",
                color=var.COLOR_WIN,
            )
            embed.add_field(name="New Balance", value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}", inline=False)
            embed.set_footer(text="Come back tomorrow for another bonus!")
        else:
            hours   = time_remaining // 3600
            minutes = (time_remaining % 3600) // 60
            embed = discord.Embed(
                title="⏰ Daily Bonus Not Ready",
                description=f"You can claim your next daily bonus in **{hours}h {minutes}m**",
                color=var.COLOR_ERROR,
            )

        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="View the top gamblers")
    async def leaderboard(self, interaction: discord.Interaction):
        gid  = str(interaction.guild_id)
        rows = self.db.execute(
            """SELECT u.user_id, u.balance, COALESCE(c.games_played, 0)
               FROM users u
               LEFT JOIN casino_stats c ON u.user_id = c.user_id AND u.guild_id = c.guild_id
               WHERE u.guild_id = ?
               ORDER BY u.balance DESC LIMIT ?""",
            (gid, var.LEADERBOARD_TOP_COUNT),
        )
        embed = discord.Embed(
            title=f"🏆 {var.CURRENCY_NAME} Leaderboard",
            description="Top 10 richest gamblers",
            color=var.COLOR_INFO,
        )
        if not rows:
            embed.description = "No users found. Start gambling to appear here!"
        else:
            lines = []
            for i, (uid, balance, games) in enumerate(rows, 1):
                try:
                    user = await self.bot.fetch_user(int(uid))
                    name = user.display_name
                except Exception:
                    name = f"User {uid}"
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                lines.append(f"{medal} **{name}** - {var.CURRENCY_SYMBOL} {balance:,} ({games} games)")
            embed.description = "\n".join(lines)

        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(GambleCog(bot))
    print("✅ Casino/Gamble cog loaded successfully")
