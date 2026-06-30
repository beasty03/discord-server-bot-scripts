import discord
from discord.ext import commands
from discord import app_commands
import logging
import json
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('bank_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB
from utils.config_loader import load_config, save_config

log = logging.getLogger("launcher")

_SETTINGS_FILE    = Path(__file__).parent / "bank_settings.json"
_SORTED_TIMEZONES = sorted(available_timezones())


def _load_settings() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            return json.loads(_SETTINGS_FILE.read_text("utf-8"))
        except Exception:
            pass
    return {}


def _save_settings(data: dict):
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2), "utf-8")

def _house_tx(db, bot_uid: str, gid: str, amount: int, tx_type: str):
    db.ensure_user(bot_uid, gid, "House")
    db.update_balance(bot_uid, gid, amount, tx_type)


def _daily_reset_time() -> tuple[int, int]:
    data = _load_settings()
    return (
        int(data.get("daily_reset_hour",   var.DAILY_RESET_HOUR)),
        int(data.get("daily_reset_minute", var.DAILY_RESET_MINUTE)),
    )


def _daily_tz() -> ZoneInfo:
    name = _load_settings().get("daily_timezone") or var.DAILY_TIMEZONE
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _effective_daily_date(now: datetime, reset_hour: int, reset_minute: int) -> date:
    """The 'daily day' for streak/claim purposes, shifted so it rolls over at the reset time instead of midnight."""
    return (now - timedelta(hours=reset_hour, minutes=reset_minute)).date()


class BankCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    async def cog_load(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS daily_streaks (
                user_id           TEXT NOT NULL,
                guild_id          TEXT NOT NULL,
                last_claimed_date TEXT,
                streak            INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

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

        reset_hour, reset_minute = _daily_reset_time()
        tz        = _daily_tz()
        now       = datetime.now(tz)
        today     = _effective_daily_date(now, reset_hour, reset_minute)
        today_str = today.isoformat()

        rows          = self.db.execute(
            "SELECT last_claimed_date, streak FROM daily_streaks WHERE user_id = ? AND guild_id = ?",
            (uid, gid),
        )
        last_date_str  = rows[0][0] if rows else None
        current_streak = rows[0][1] if rows else 0

        # Seconds until next reset (used in both branches)
        next_reset = now.replace(hour=reset_hour, minute=reset_minute, second=0, microsecond=0)
        if next_reset <= now:
            next_reset += timedelta(days=1)
        secs      = int((next_reset - now).total_seconds())
        hrs, mins = secs // 3600, (secs % 3600) // 60

        if last_date_str == today_str:
            embed = discord.Embed(
                title="⏰ Already Claimed",
                description=f"You already claimed your daily today!\nResets in **{hrs}h {mins}m**.",
                color=var.COLOR_ERROR,
            )
            embed.timestamp = now
            await interaction.response.send_message(embed=embed)
            return

        # New streak
        if last_date_str:
            days_since = (today - date.fromisoformat(last_date_str)).days
            new_streak = current_streak + 1 if days_since == 1 else 1
        else:
            new_streak = 1

        # Base amount
        custom      = _load_settings().get("daily_amount", 0)
        base_amount = custom if custom > 0 else var.DAILY_BONUS_AMOUNT

        # Streak bonus (kicks in at STREAK_BONUS_STARTS)
        streak_bonus_pct = 0
        if new_streak >= var.STREAK_BONUS_STARTS:
            days_above       = new_streak - (var.STREAK_BONUS_STARTS - 1)
            streak_bonus_pct = min(days_above * var.STREAK_BONUS_PER_DAY, var.STREAK_BONUS_MAX)
        streak_bonus = int(base_amount * streak_bonus_pct / 100)

        # Multiplier event bonus (applied on top of base + streak)
        dm_mult     = getattr(interaction.client, 'multiplier_event_mult', None) or 1.0
        event_bonus = int((base_amount + streak_bonus) * (dm_mult - 1)) if dm_mult > 1.0 else 0

        total_amount = base_amount + streak_bonus + event_bonus

        # Credit balance; house pays the daily reward
        bot_uid = str(interaction.client.user.id)
        self.db.update_balance(uid, gid, base_amount, 'daily')
        _house_tx(self.db, bot_uid, gid, -base_amount, 'house_payout')
        if streak_bonus > 0:
            self.db.update_balance(uid, gid, streak_bonus, 'daily_streak')
            _house_tx(self.db, bot_uid, gid, -streak_bonus, 'house_payout')
        if event_bonus > 0:
            self.db.update_balance(uid, gid, event_bonus, 'daily_event_bonus')
            _house_tx(self.db, bot_uid, gid, -event_bonus, 'house_payout')

        # Persist streak
        self.db.execute(
            """INSERT INTO daily_streaks (user_id, guild_id, last_claimed_date, streak)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, guild_id) DO UPDATE SET
                   last_claimed_date = excluded.last_claimed_date,
                   streak            = excluded.streak""",
            (uid, gid, today_str, new_streak),
        )

        new_balance  = self.db.get_balance(uid, gid)
        streak_emoji = "🔥" if new_streak >= var.STREAK_BONUS_STARTS else "📅"

        embed = discord.Embed(
            title="🎁 Daily Bonus Claimed!",
            description=f"You received **{var.CURRENCY_SYMBOL} {total_amount:,} {var.CURRENCY_NAME}**!",
            color=var.COLOR_WIN,
        )
        embed.add_field(name="Base Daily", value=f"{var.CURRENCY_SYMBOL} {base_amount:,}", inline=True)
        if streak_bonus > 0:
            embed.add_field(
                name=f"🔥 Streak Bonus (+{streak_bonus_pct:.0f}%)",
                value=f"{var.CURRENCY_SYMBOL} {streak_bonus:,}",
                inline=True,
            )
        if event_bonus > 0:
            embed.add_field(
                name=f"💰 Event Bonus ({dm_mult}x)",
                value=f"{var.CURRENCY_SYMBOL} {event_bonus:,}",
                inline=True,
            )
        days_label = f"**{new_streak}** day{'s' if new_streak != 1 else ''}"
        if new_streak == var.STREAK_BONUS_STARTS - 1:
            days_label += " — bonus tomorrow!"
        embed.add_field(name=f"{streak_emoji} Streak", value=days_label, inline=True)
        embed.add_field(
            name="New Balance",
            value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}",
            inline=False,
        )
        embed.set_footer(text=f"Resets in {hrs}h {mins}m · {var.SERVER_NAME}")
        embed.timestamp = now
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

    # ── /house_balance ────────────────────────────────────────────────────────

    @app_commands.command(name="house_balance", description="Show the house (bot) bank balance for this server.")
    async def house_balance(self, interaction: discord.Interaction):
        bot_uid = str(interaction.client.user.id)
        gid     = str(interaction.guild_id)
        self.db.ensure_user(bot_uid, gid, "House")
        balance = self.db.get_balance(bot_uid, gid)
        color   = var.COLOR_WIN if balance >= 0 else var.COLOR_ERROR
        embed   = discord.Embed(
            title="🏦 House Balance",
            description=(
                f"The casino house currently holds **{var.CURRENCY_SYMBOL} {balance:,} {var.CURRENCY_NAME}**."
            ),
            color=color,
        )
        embed.set_footer(text=var.SERVER_NAME)
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /set_daily_amount ─────────────────────────────────────────────────────

    @app_commands.command(name="set_daily_amount", description="Set the daily bonus amount all players receive.")
    @app_commands.describe(amount="Coins awarded each day (0 = use server default)")
    async def set_daily_amount(self, interaction: discord.Interaction, amount: int):
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

    # ── /set_daily_time ───────────────────────────────────────────────────────

    @app_commands.command(name="set_daily_time", description="Set the time the daily bonus resets (uses your configured timezone).")
    @app_commands.describe(hour="Hour (0–23)", minute="Minute (0–59)")
    async def set_daily_time(self, interaction: discord.Interaction, hour: int, minute: int):
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            await interaction.response.send_message("Invalid time — hour must be 0–23 and minute 0–59.", ephemeral=True)
            return
        data = _load_settings()
        data["daily_reset_hour"]   = hour
        data["daily_reset_minute"] = minute
        _save_settings(data)
        tz = _daily_tz()
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Daily bonus now resets at **{hour:02d}:{minute:02d}** ({tz.key}).",
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )

    # ── /set_daily_timezone ───────────────────────────────────────────────────

    @app_commands.command(name="set_daily_timezone", description="Set the timezone for the daily bonus reset time (e.g. Europe/Brussels).")
    @app_commands.describe(timezone="Start typing to search — e.g. Brussels, New_York, London")
    async def set_daily_timezone(self, interaction: discord.Interaction, timezone: str):
        try:
            tz = ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            await interaction.response.send_message(
                f"`{timezone}` is not a valid timezone. Use an IANA name like `Europe/Brussels` or `America/New_York`.",
                ephemeral=True,
            )
            return
        data = _load_settings()
        data["daily_timezone"] = timezone
        _save_settings(data)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Timezone set to **{tz.key}**. Daily reset time is now interpreted in that timezone.",
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )

    @set_daily_timezone.autocomplete("timezone")
    async def daily_timezone_autocomplete(self, _interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        lower   = current.lower()
        matches = [tz for tz in _SORTED_TIMEZONES if lower in tz.lower()]
        return [app_commands.Choice(name=tz, value=tz) for tz in matches[:25]]


async def setup(bot: commands.Bot):
    await bot.add_cog(BankCog(bot))
    log.info("✅ Casino/Bank cog loaded")
