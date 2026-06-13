import discord
from discord.ext import commands
from discord import app_commands
import logging
import json
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('bank_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB
from utils.config_loader import load_config, save_config

log = logging.getLogger("launcher")

_SETTINGS_FILE = Path(__file__).parent / "bank_settings.json"


def _load_settings() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            return json.loads(_SETTINGS_FILE.read_text("utf-8"))
        except Exception:
            pass
    return {}


def _save_settings(data: dict):
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2), "utf-8")


class BankCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    # ── /balance ──────────────────────────────────────────────────────────────

    @app_commands.command(name="bal", description="Show your full casino stats and balance.")
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

            # Apply configured daily amount override
            custom = _load_settings().get("daily_amount", 0)
            if custom > 0 and custom != bonus_amount:
                diff = custom - bonus_amount
                self.db.update_balance(uid, gid, diff, 'daily_override')
                new_balance  = self.db.get_balance(uid, gid)
                bonus_amount = custom

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

    # ── /set_currency_name / /set_currency_icon ───────────────────────────────

    @app_commands.command(name="set_currency_name", description="Set the currency name shown across all bot commands.")
    @app_commands.describe(name="New currency name (e.g. coins, credits, gold)")
    async def set_currency_name(self, interaction: discord.Interaction, name: str):
        cfg = load_config()
        cfg["currency_name"] = name
        save_config(cfg)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Currency name set to **{name}**. Restart the bot to apply across all cogs.",
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="set_currency_icon", description="Set the currency emoji shown across all bot commands.")
    @app_commands.describe(icon="Emoji to use as the currency symbol (e.g. 💎 🪙 ⭐)")
    async def set_currency_icon(self, interaction: discord.Interaction, icon: str):
        cfg = load_config()
        cfg["currency_symbol"] = icon
        save_config(cfg)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Currency icon set to **{icon}**. Restart the bot to apply across all cogs.",
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )

    # ── /set_bal_amount ───────────────────────────────────────────────────────

    @app_commands.command(name="set_bal_amount", description="Set a user's balance to a specific amount.")
    @app_commands.describe(member="The user whose balance to set", amount="New balance amount")
    async def set_bal_amount(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount < 0:
            await interaction.response.send_message(
                embed=discord.Embed(description="Amount must be 0 or higher.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return
        uid = str(member.id)
        gid = str(interaction.guild_id)
        self.db.ensure_user(uid, gid, member.display_name)
        current = self.db.get_balance(uid, gid)
        delta   = amount - current
        if delta != 0:
            self.db.update_balance(uid, gid, delta, 'admin_set')
        await interaction.response.send_message(
            embed=discord.Embed(
                description=(
                    f"✅ {member.mention}'s balance set to "
                    f"**{var.CURRENCY_SYMBOL} {amount:,} {var.CURRENCY_NAME}**."
                ),
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )

    # ── /set_daily ────────────────────────────────────────────────────────────

    @app_commands.command(name="set_daily", description="Set the daily bonus amount all players receive.")
    @app_commands.describe(amount="Coins awarded each day (0 = use server default)")
    async def set_daily(self, interaction: discord.Interaction, amount: int):
        if amount < 0:
            await interaction.response.send_message(
                embed=discord.Embed(description="Amount must be 0 or higher.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return
        data = _load_settings()
        data["daily_amount"] = amount
        _save_settings(data)
        msg = (
            f"Daily bonus set to **{var.CURRENCY_SYMBOL} {amount:,} {var.CURRENCY_NAME}**."
            if amount > 0
            else "Daily bonus reset to server default."
        )
        await interaction.response.send_message(
            embed=discord.Embed(description=f"✅ {msg}", color=var.COLOR_WIN),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(BankCog(bot))
    log.info("✅ Casino/Bank cog loaded")
