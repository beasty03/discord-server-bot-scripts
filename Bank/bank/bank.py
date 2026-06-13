import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('bank_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")


class BankCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    # ── /balance ──────────────────────────────────────────────────────────────

    @app_commands.command(name="balance", description="Show your full casino stats and balance.")
    @app_commands.describe(member="Another user to look up (leave empty for yourself)")
    async def balance(self, interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        uid    = str(target.id)
        gid    = str(interaction.guild_id)
        self.db.ensure_user(uid, gid, target.display_name)

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
            title=f"{var.CURRENCY_SYMBOL} {target.display_name}'s Stats",
            color=var.COLOR_INFO,
        )
        embed.add_field(name="Balance",      value=f"{var.CURRENCY_SYMBOL} **{balance:,}** {var.CURRENCY_NAME}", inline=False)
        embed.add_field(name="Games Played", value=f"{games_played:,}",                                           inline=True)
        embed.add_field(name="Total Won",    value=f"{var.CURRENCY_SYMBOL} {total_won:,}",                        inline=True)
        embed.add_field(name="Total Lost",   value=f"{var.CURRENCY_SYMBOL} {total_lost:,}",                       inline=True)
        embed.add_field(
            name=f"{'📈' if net >= 0 else '📉'} Net Profit/Loss",
            value=f"{var.CURRENCY_SYMBOL} {net:+,} {var.CURRENCY_NAME}",
            inline=False,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"{var.SERVER_NAME} Casino")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    # ── /bal ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="bal", description="Quick balance check.")
    @app_commands.describe(member="Another user to look up (leave empty for yourself)")
    async def bal(self, interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        uid    = str(target.id)
        gid    = str(interaction.guild_id)
        self.db.ensure_user(uid, gid, target.display_name)

        balance = self.db.get_balance(uid, gid)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"{target.mention} has **{var.CURRENCY_SYMBOL} {balance:,} {var.CURRENCY_NAME}**",
                color=var.COLOR_INFO,
            )
        )

    # ── /daily ────────────────────────────────────────────────────────────────

    @app_commands.command(name="daily", description=f"Claim your daily {var.CURRENCY_NAME} bonus.")
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
            embed.add_field(
                name="New Balance",
                value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}",
                inline=False,
            )
            embed.set_footer(text="Come back tomorrow for another bonus!")
        else:
            hours   = time_remaining // 3600
            minutes = (time_remaining % 3600) // 60
            embed   = discord.Embed(
                title="⏰ Daily Bonus Not Ready",
                description=f"You can claim your next bonus in **{hours}h {minutes}m**.",
                color=var.COLOR_ERROR,
            )

        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    # ── /top ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="top", description="View the richest players on the server.")
    async def top(self, interaction: discord.Interaction):
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
            title=f"🏆 {var.CURRENCY_NAME.capitalize()} Leaderboard",
            color=var.COLOR_INFO,
        )
        if not rows:
            embed.description = "No players yet — start gambling to appear here!"
        else:
            lines = []
            for i, (uid, balance, games) in enumerate(rows, 1):
                try:
                    user = await self.bot.fetch_user(int(uid))
                    name = user.display_name
                except Exception:
                    name = f"User {uid}"
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                lines.append(
                    f"{medal} {name} — {var.CURRENCY_SYMBOL} **{balance:,}** "
                    f"*({games:,} game{'s' if games != 1 else ''})*"
                )
            embed.description = "\n".join(lines)
        embed.set_footer(text=f"{var.SERVER_NAME} Casino")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    # ── /give ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="give", description="Give some of your coins to another player.")
    @app_commands.describe(
        member="The player to send coins to",
        amount=f"How many coins to send",
    )
    async def give(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        sender_uid = str(interaction.user.id)
        recip_uid  = str(member.id)
        gid        = str(interaction.guild_id)

        if member.id == interaction.user.id:
            await interaction.response.send_message(
                embed=discord.Embed(description="You can't give coins to yourself.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        if member.bot:
            await interaction.response.send_message(
                embed=discord.Embed(description="You can't give coins to a bot.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        if amount < var.GIVE_MIN:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Minimum transfer is **{var.CURRENCY_SYMBOL} {var.GIVE_MIN:,}**.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        if var.GIVE_MAX > 0 and amount > var.GIVE_MAX:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Maximum transfer is **{var.CURRENCY_SYMBOL} {var.GIVE_MAX:,}**.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        self.db.ensure_user(sender_uid, gid, interaction.user.display_name)
        sender_balance = self.db.get_balance(sender_uid, gid)

        if sender_balance < amount:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        f"You don't have enough {var.CURRENCY_NAME}.\n"
                        f"Your balance: **{var.CURRENCY_SYMBOL} {sender_balance:,}**"
                    ),
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        self.db.ensure_user(recip_uid, gid, member.display_name)
        self.db.update_balance(sender_uid, gid, -amount, 'transfer_out')
        self.db.update_balance(recip_uid,  gid,  amount, 'transfer_in')

        new_sender_balance = self.db.get_balance(sender_uid, gid)
        embed = discord.Embed(
            title="💸 Transfer Complete",
            description=(
                f"{interaction.user.mention} gave **{var.CURRENCY_SYMBOL} {amount:,} {var.CURRENCY_NAME}** "
                f"to {member.mention}!"
            ),
            color=var.COLOR_WIN,
        )
        embed.add_field(
            name="Your new balance",
            value=f"{var.CURRENCY_SYMBOL} {new_sender_balance:,} {var.CURRENCY_NAME}",
            inline=False,
        )
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(BankCog(bot))
    log.info("✅ Casino/Bank cog loaded")
