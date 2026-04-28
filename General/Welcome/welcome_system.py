import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import time
from collections import defaultdict
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # makes local variables.py importable
import variables as var
from cogs.Database_management.database_manager import DatabaseManager

db_manager = DatabaseManager(starting_balance=var.STARTING_BALANCE)

log = logging.getLogger("launcher")


class TermsAcceptView(discord.ui.View):
    """Persistent view — survives bot restarts via bot.add_view() in on_ready."""
    cog_ref = None  # set to the live WelcomeSystem instance

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="✅ Accept Terms & Conditions",
        style=discord.ButtonStyle.green,
        custom_id="welcome_accept_terms",
    )
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if TermsAcceptView.cog_ref is None:
            await interaction.response.send_message(
                "The bot is still starting up — please try again in a moment.", ephemeral=True
            )
            return
        await TermsAcceptView.cog_ref.handle_acceptance(interaction)


class WelcomeSystem(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        TermsAcceptView.cog_ref = self
        self._register_tables()

    def cog_unload(self):
        if self.message_log_task.is_running():
            self.message_log_task.cancel()

    # ── Database setup ───────────────────────────────────────────────────────

    def _register_tables(self):
        db_manager.register_table("""
            CREATE TABLE IF NOT EXISTS pending_users (
                user_id   INTEGER PRIMARY KEY,
                guild_id  INTEGER NOT NULL,
                join_ts   REAL    NOT NULL
            )
        """)
        db_manager.register_table("""
            CREATE TABLE IF NOT EXISTS new_member_messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                channel_id      INTEGER NOT NULL,
                channel_name    TEXT    NOT NULL,
                message_content TEXT    NOT NULL,
                timestamp       REAL    NOT NULL
            )
        """)
        db_manager.register_table("""
            CREATE TABLE IF NOT EXISTS welcome_config (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

    # ── Config helpers ───────────────────────────────────────────────────────

    def _get_cfg(self, key: str) -> str | None:
        rows = db_manager.execute("SELECT value FROM welcome_config WHERE key = ?", (key,))
        return rows[0][0] if rows else None

    def _set_cfg(self, key: str, value: str):
        db_manager.execute(
            "INSERT OR REPLACE INTO welcome_config (key, value) VALUES (?, ?)",
            (key, str(value)),
        )

    def _interval(self) -> int:
        v = self._get_cfg("monitoring_interval_hours")
        return int(v) if v else var.MESSAGE_LOG_INTERVAL_HOURS

    def _period(self) -> int:
        v = self._get_cfg("monitoring_period_days")
        return int(v) if v else var.MONITORING_PERIOD_DAYS

    def _welcome_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        cid = self._get_cfg("welcome_channel_id")
        if cid:
            return guild.get_channel(int(cid))
        return discord.utils.get(guild.text_channels, name="welcome")

    def _bot_logs(self, guild: discord.Guild) -> discord.TextChannel | None:
        return discord.utils.get(guild.text_channels, name="bot-logs")

    def _member_role(self, guild: discord.Guild) -> discord.Role | None:
        rid = self._get_cfg("welcome_role_id")
        if rid:
            return guild.get_role(int(rid))
        return discord.utils.get(guild.roles, name="Member")

    def _terms(self) -> str:
        t = self._get_cfg("terms_text")
        return t if t else var.DEFAULT_TERMS

    # ── Startup checks ───────────────────────────────────────────────────────

    async def _startup_checks(self, guild: discord.Guild):
        bot_logs = self._bot_logs(guild)
        if not bot_logs:
            log.warning("[WelcomeSystem] No #bot-logs channel found in %s", guild.name)
            return

        if not self._welcome_channel(guild):
            await bot_logs.send(embed=discord.Embed(
                title="⚠️ Welcome Channel Missing",
                description=(
                    "No welcome channel is configured.\n\n"
                    "Please provide a channel where new users will be welcomed:\n"
                    "**→** `/set_welcome_channel #channel`"
                ),
                color=var.COLOR_ERROR,
            ))

        if not self._member_role(guild):
            await bot_logs.send(embed=discord.Embed(
                title="⚠️ Member Role Missing",
                description=(
                    "No member role is configured.\n\n"
                    "Please provide a role that will be given to new users after they accept T&C:\n"
                    "**→** `/set_welcome_role @role`"
                ),
                color=var.COLOR_ERROR,
            ))

        # Deny Send Messages on @everyone to enforce the T&C gate
        everyone = guild.default_role
        if everyone.permissions.send_messages:
            perms = everyone.permissions
            perms.update(send_messages=False)
            try:
                await everyone.edit(
                    permissions=perms,
                    reason="Welcome system: gate chat access behind T&C acceptance",
                )
                await bot_logs.send(embed=discord.Embed(
                    title="🔒 Permissions Updated",
                    description=(
                        "Set **@everyone → Send Messages** to `Deny`.\n"
                        "Members who accept T&C and receive the Member role will still be able to chat."
                    ),
                    color=var.COLOR_INFO,
                ))
            except discord.Forbidden:
                await bot_logs.send(embed=discord.Embed(
                    title="⚠️ Could Not Update @everyone Permissions",
                    description=(
                        "I don't have the **Manage Roles** permission needed to edit @everyone.\n"
                        "Please manually set **@everyone → Send Messages** to `Deny`."
                    ),
                    color=var.COLOR_ERROR,
                ))

        # Allow Send Messages on the Member role so accepted users can chat
        role = self._member_role(guild)
        if role and not role.permissions.send_messages:
            perms = role.permissions
            perms.update(send_messages=True)
            try:
                await role.edit(
                    permissions=perms,
                    reason="Welcome system: grant Send Messages to members who accepted T&C",
                )
                await bot_logs.send(embed=discord.Embed(
                    title="🔓 Member Role Updated",
                    description=f"Set **{role.name} → Send Messages** to `Allow`.",
                    color=var.COLOR_INFO,
                ))
            except discord.Forbidden:
                await bot_logs.send(embed=discord.Embed(
                    title="⚠️ Could Not Update Member Role Permissions",
                    description=(
                        f"I don't have permission to edit the **{role.name}** role.\n"
                        "Please manually set **Send Messages** to `Allow` on it.\n"
                        "Make sure my role is above it in the role list."
                    ),
                    color=var.COLOR_ERROR,
                ))

    # ── Events ───────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TermsAcceptView())  # re-register persistent view after restarts
        for guild in self.bot.guilds:
            await self._startup_checks(guild)
        self.message_log_task.change_interval(hours=self._interval())
        if not self.message_log_task.is_running():
            self.message_log_task.start()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self._startup_checks(guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        db_manager.execute(
            "INSERT OR REPLACE INTO pending_users (user_id, guild_id, join_ts) VALUES (?, ?, ?)",
            (member.id, member.guild.id, time.time()),
        )

        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}!",
            description=(
                f"Before you can participate you must read and accept our Terms & Conditions.\n\n"
                f"**Terms & Conditions**\n{self._terms()}\n\n"
                f"Click the button below to accept and unlock the server."
            ),
            color=var.COLOR_INFO,
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(text=member.guild.name)

        try:
            await member.send(embed=embed, view=TermsAcceptView())
        except discord.Forbidden:
            ch = self._bot_logs(member.guild)
            if ch:
                await ch.send(embed=discord.Embed(
                    title="⚠️ Could Not DM New Member",
                    description=(
                        f"{member.mention} joined but I couldn't send the T&C (DMs disabled).\n"
                        f"Use `/resend_terms` on them once they enable DMs."
                    ),
                    color=var.COLOR_ERROR,
                ))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or message.guild.id != var.GUILD_ID:
            return

        member = message.guild.get_member(message.author.id)
        if not member or not member.joined_at:
            return

        # Only track members within the monitoring window
        if member.joined_at.timestamp() < time.time() - self._period() * 86400:
            return

        # Skip users who haven't accepted T&C yet
        if db_manager.execute("SELECT 1 FROM pending_users WHERE user_id = ?", (member.id,)):
            return

        db_manager.execute(
            "INSERT INTO new_member_messages "
            "(user_id, channel_id, channel_name, message_content, timestamp) VALUES (?, ?, ?, ?, ?)",
            (member.id, message.channel.id, message.channel.name, message.content[:500], time.time()),
        )

    # ── T&C acceptance flow ──────────────────────────────────────────────────

    async def handle_acceptance(self, interaction: discord.Interaction):
        user = interaction.user
        guild = self.bot.get_guild(var.GUILD_ID)
        if not guild:
            await interaction.response.send_message("Server not found — contact an admin.", ephemeral=True)
            return

        member = guild.get_member(user.id)
        if not member:
            await interaction.response.send_message("You're no longer in the server.", ephemeral=True)
            return

        if not db_manager.execute("SELECT 1 FROM pending_users WHERE user_id = ?", (user.id,)):
            await interaction.response.send_message("You've already accepted the terms!", ephemeral=True)
            return

        role = self._member_role(guild)
        if not role:
            await interaction.response.send_message(
                "The member role isn't configured yet — contact an admin.", ephemeral=True
            )
            return

        try:
            await member.add_roles(role, reason="Accepted Terms & Conditions")
        except discord.Forbidden:
            await interaction.response.send_message(
                "I lack permission to assign roles — contact an admin.", ephemeral=True
            )
            return

        db_manager.execute("DELETE FROM pending_users WHERE user_id = ?", (user.id,))
        db_manager.get_user_balance(user.id)  # creates casino record with starting balance

        welcome_ch = self._welcome_channel(guild)
        if welcome_ch:
            shoutout = discord.Embed(
                title="👋 New Member!",
                description=(
                    f"Everyone welcome {member.mention} to **{guild.name}**! 🎉\n"
                    f"They've accepted the Terms & Conditions and are ready to chat."
                ),
                color=var.COLOR_WIN,
                timestamp=datetime.utcnow(),
            )
            shoutout.set_thumbnail(url=member.display_avatar.url)
            shoutout.set_footer(text=f"Member #{guild.member_count}")
            await welcome_ch.send(embed=shoutout)

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="✅ Access Granted",
                description=f"You now have full access to **{guild.name}**. Enjoy your stay!",
                color=var.COLOR_WIN,
            ),
            view=None,
        )

    # ── Hourly monitoring task ───────────────────────────────────────────────

    @tasks.loop(hours=1)
    async def message_log_task(self):
        guild = self.bot.get_guild(var.GUILD_ID)
        if not guild:
            return

        ch = self._bot_logs(guild)
        if not ch:
            return

        rows = db_manager.execute(
            "SELECT user_id, channel_name, message_content, timestamp "
            "FROM new_member_messages ORDER BY user_id, timestamp",
            (),
        )
        if not rows:
            return

        # Snapshot and clear before building embeds so a mid-send crash doesn't double-log
        db_manager.execute("DELETE FROM new_member_messages", ())

        grouped: dict[int, list] = defaultdict(list)
        for uid, cname, content, ts in rows:
            grouped[uid].append((cname, content, ts))

        # Split into multiple embeds if needed (Discord limit: 25 fields per embed)
        embeds: list[discord.Embed] = []
        embed = discord.Embed(
            title="📋 New Member Activity Log",
            description=f"Activity from members who joined in the last {self._period()} day(s)",
            color=var.COLOR_INFO,
            timestamp=datetime.utcnow(),
        )
        fields = 0

        for uid, msgs in grouped.items():
            if fields >= 25:
                embeds.append(embed)
                embed = discord.Embed(color=var.COLOR_INFO, timestamp=datetime.utcnow())
                fields = 0

            m = guild.get_member(uid)
            label = m.display_name if m else f"User {uid}"
            if m and m.joined_at:
                days = (datetime.utcnow() - m.joined_at.replace(tzinfo=None)).days
                label += f" (joined {days}d ago)"

            body = "\n".join(
                f"**#{cname}:** {txt[:100]}" for cname, txt, _ in msgs[-10:]
            ) or "*(no text content)*"

            embed.add_field(name=f"👤 {label}", value=body, inline=False)
            fields += 1

        embeds.append(embed)
        for e in embeds:
            await ch.send(embed=e)

    # ── Control panel commands ───────────────────────────────────────────────

    @app_commands.command(name="set_welcome_channel", description="Set the channel where new members are welcomed")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self._set_cfg("welcome_channel_id", str(channel.id))
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Welcome Channel Set",
            description=f"New members will be welcomed in {channel.mention}",
            color=var.COLOR_WIN,
        ), ephemeral=True)

    @app_commands.command(name="set_welcome_role", description="Set the role given to members after accepting T&C")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome_role(self, interaction: discord.Interaction, role: discord.Role):
        self._set_cfg("welcome_role_id", str(role.id))
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Welcome Role Set",
            description=f"New members will receive {role.mention} after accepting T&C.",
            color=var.COLOR_WIN,
        ), ephemeral=True)

    @app_commands.command(name="set_terms", description="Update the Terms & Conditions shown to new members")
    @app_commands.default_permissions(administrator=True)
    async def set_terms(self, interaction: discord.Interaction, text: str):
        self._set_cfg("terms_text", text)
        embed = discord.Embed(
            title="✅ Terms & Conditions Updated",
            description="New members will see the updated text the next time they join.",
            color=var.COLOR_WIN,
        )
        embed.add_field(name="Preview", value=text[:500], inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="set_monitoring_interval",
        description="How often (in hours) the new-member activity log is posted to #bot-logs",
    )
    @app_commands.default_permissions(administrator=True)
    async def set_monitoring_interval(
        self, interaction: discord.Interaction, hours: app_commands.Range[int, 1, 24]
    ):
        self._set_cfg("monitoring_interval_hours", str(hours))
        self.message_log_task.change_interval(hours=hours)
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Monitoring Interval Updated",
            description=f"Activity logs will be posted every **{hours} hour(s)**.",
            color=var.COLOR_WIN,
        ), ephemeral=True)

    @app_commands.command(
        name="set_monitoring_period",
        description="How many days after joining a member's messages are monitored",
    )
    @app_commands.default_permissions(administrator=True)
    async def set_monitoring_period(
        self, interaction: discord.Interaction, days: app_commands.Range[int, 1, 30]
    ):
        self._set_cfg("monitoring_period_days", str(days))
        await interaction.response.send_message(embed=discord.Embed(
            title="✅ Monitoring Period Updated",
            description=f"Messages from members who joined in the last **{days} day(s)** will be monitored.",
            color=var.COLOR_WIN,
        ), ephemeral=True)

    @app_commands.command(name="resend_terms", description="Resend the T&C DM to a member who missed it")
    @app_commands.default_permissions(administrator=True)
    async def resend_terms(self, interaction: discord.Interaction, member: discord.Member):
        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}!",
            description=(
                f"**Terms & Conditions**\n{self._terms()}\n\n"
                "Click the button below to accept and unlock the server."
            ),
            color=var.COLOR_INFO,
            timestamp=datetime.utcnow(),
        )
        embed.set_footer(text=member.guild.name)
        try:
            await member.send(embed=embed, view=TermsAcceptView())
            await interaction.response.send_message(embed=discord.Embed(
                title="✅ T&C Resent",
                description=f"Terms & Conditions DM sent to {member.mention}.",
                color=var.COLOR_WIN,
            ), ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(embed=discord.Embed(
                title="❌ Could Not DM Member",
                description=f"{member.mention} has DMs disabled.",
                color=var.COLOR_ERROR,
            ), ephemeral=True)

    # ── Error handler ────────────────────────────────────────────────────────

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ An error occurred: {error}", ephemeral=True)
        except Exception:
            pass
        raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeSystem(bot))
    logging.getLogger("launcher").info("✅ WelcomeSystem cog loaded")
