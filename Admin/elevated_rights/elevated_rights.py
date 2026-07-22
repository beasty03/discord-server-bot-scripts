import re
import time
import logging
from pathlib import Path

import discord
from discord.ext import commands, tasks
from discord import app_commands

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('elevated_rights_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

ForgeDB.declare_schema(
    tables=[
        """CREATE TABLE IF NOT EXISTS elevated_rights_grants (
               guild_id    TEXT    NOT NULL,
               user_id     TEXT    NOT NULL,
               role_id     INTEGER NOT NULL,
               granted_by  TEXT    NOT NULL,
               reason      TEXT,
               expires_at  INTEGER NOT NULL,
               PRIMARY KEY (guild_id, user_id, role_id)
           )""",
        """CREATE TABLE IF NOT EXISTS elevated_rights_config (
               key   TEXT PRIMARY KEY,
               value TEXT NOT NULL
           )""",
    ],
)

log = logging.getLogger("launcher")

_DURATION_RE = re.compile(r"(\d+)\s*([smhdw])", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def parse_duration(text: str) -> int | None:
    """Parse strings like '30m', '2h', '1d12h' into total seconds. Returns None if unparseable."""
    text = (text or "").strip().lower()
    if not text:
        return None
    matches = _DURATION_RE.findall(text)
    if not matches:
        return None
    # Reject trailing garbage that isn't part of a valid unit token
    if _DURATION_RE.sub("", text).strip():
        return None
    total = 0
    for amount, unit in matches:
        total += int(amount) * _UNIT_SECONDS[unit]
    return total if total > 0 else None


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    parts = []
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        if seconds >= size:
            value = seconds // size
            seconds -= value * size
            parts.append(f"{value}{unit}")
    return " ".join(parts) if parts else "0s"


class ElevatedRights(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()
        self._expiry_check.start()

    def cog_unload(self):
        self._expiry_check.cancel()

    # ── Database ──────────────────────────────────────────────────────────────

    def _add_grant(self, guild_id: str, user_id: str, role_id: int, granted_by: str, reason: str, expires_at: int):
        self.db.execute(
            """INSERT OR REPLACE INTO elevated_rights_grants
               (guild_id, user_id, role_id, granted_by, reason, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (guild_id, user_id, role_id, granted_by, reason, expires_at),
        )

    def _remove_grant(self, guild_id: str, user_id: str, role_id: int):
        self.db.execute(
            "DELETE FROM elevated_rights_grants WHERE guild_id = ? AND user_id = ? AND role_id = ?",
            (guild_id, user_id, role_id),
        )

    def _get_grants_for_user(self, guild_id: str, user_id: str) -> list[tuple]:
        return self.db.execute(
            "SELECT role_id, granted_by, reason, expires_at FROM elevated_rights_grants "
            "WHERE guild_id = ? AND user_id = ? ORDER BY expires_at",
            (guild_id, user_id),
        ) or []

    def _get_grants_for_guild(self, guild_id: str) -> list[tuple]:
        return self.db.execute(
            "SELECT user_id, role_id, granted_by, reason, expires_at FROM elevated_rights_grants "
            "WHERE guild_id = ? ORDER BY expires_at",
            (guild_id,),
        ) or []

    def _get_all_expired(self, now: int) -> list[tuple]:
        return self.db.execute(
            "SELECT guild_id, user_id, role_id FROM elevated_rights_grants WHERE expires_at <= ?",
            (now,),
        ) or []

    def _get_cfg(self, key: str) -> str | None:
        rows = self.db.execute("SELECT value FROM elevated_rights_config WHERE key = ?", (key,))
        return rows[0][0] if rows else None

    def _set_cfg(self, key: str, value: str):
        self.db.execute(
            "INSERT OR REPLACE INTO elevated_rights_config (key, value) VALUES (?, ?)",
            (key, str(value)),
        )

    def _default_duration(self) -> str:
        return self._get_cfg("default_duration") or var.DEFAULT_DURATION

    def _max_duration_hours(self) -> int:
        stored = self._get_cfg("max_duration_hours")
        return int(stored) if stored is not None else var.MAX_DURATION_HOURS

    def _default_role(self, guild: discord.Guild) -> discord.Role | None:
        stored = self._get_cfg("elevate_role_id")
        return guild.get_role(int(stored)) if stored else None

    # ── Background expiry sweep ──────────────────────────────────────────────

    @tasks.loop(seconds=var.CHECK_INTERVAL_SECONDS)
    async def _expiry_check(self):
        now = int(time.time())
        expired = self._get_all_expired(now)
        for guild_id, user_id, role_id in expired:
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                self._remove_grant(guild_id, user_id, role_id)
                continue
            role = guild.get_role(role_id)
            member = guild.get_member(int(user_id))
            if member and role and role in member.roles:
                try:
                    await member.remove_roles(role, reason="Temporary role expired")
                    log.info("[ElevatedRights] Expired role %s removed from %s in %s.", role_id, user_id, guild_id)
                except (discord.Forbidden, discord.HTTPException) as e:
                    log.warning("[ElevatedRights] Failed to remove expired role %s from %s: %s", role_id, user_id, e)
            self._remove_grant(guild_id, user_id, role_id)

    @_expiry_check.before_loop
    async def _before_expiry_check(self):
        await self.bot.wait_until_ready()

    # ── Slash commands ────────────────────────────────────────────────────────

    @app_commands.command(name="elevate", description="Temporarily grant a member a role.")
    @app_commands.describe(
        member="The member to grant the role to",
        role="The role to grant (uses the server default from /set_elevate_role if omitted)",
        duration="How long to grant it for, e.g. 30m, 2h, 1d (uses the server default if omitted)",
        reason="Optional reason, shown in /elevate_list",
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def elevate(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role | None = None,
        duration: str | None = None,
        reason: str | None = None,
    ):
        if role is None:
            role = self._default_role(interaction.guild)
            if role is None:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description="No default elevate role is set. Pass a `role`, or set one with `/set_elevate_role`.",
                        color=var.COLOR_ERROR,
                    ),
                    ephemeral=True,
                )
                return

        duration = duration or self._default_duration()
        seconds = parse_duration(duration)
        if seconds is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Couldn't parse duration `{duration}`. Try formats like `30m`, `2h`, or `1d12h`.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        max_hours = self._max_duration_hours()
        if max_hours and seconds > max_hours * 3600:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"That duration exceeds the max of {max_hours} hours. "
                                f"An admin can raise this with `/set_elevate_time`.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        if role.is_default() or role.managed:
            await interaction.response.send_message(
                embed=discord.Embed(description="That role can't be assigned manually.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"I can't assign **{role.name}** — it's above or equal to my highest role.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        if role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"You can't grant **{role.name}** — it's above or equal to your highest role.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        expires_at = int(time.time()) + seconds
        try:
            if role not in member.roles:
                await member.add_roles(role, reason=f"Temporary elevation by {interaction.user} ({reason or 'no reason given'})")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=discord.Embed(description="I don't have permission to assign that role.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        self._add_grant(str(interaction.guild.id), str(member.id), role.id, str(interaction.user.id), reason, expires_at)

        await interaction.response.send_message(
            embed=discord.Embed(
                description=(
                    f"Granted {member.mention} **{role.name}** for **{format_duration(seconds)}**"
                    f"{f' — *{reason}*' if reason else ''}.\nIt will be removed automatically."
                ),
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="elevate_remove", description="Revoke a temporary role early.")
    @app_commands.describe(
        member="The member to revoke the role from",
        role="The role to revoke (uses the server default from /set_elevate_role if omitted)",
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def elevate_remove(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role | None = None):
        if role is None:
            role = self._default_role(interaction.guild)
            if role is None:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description="No default elevate role is set. Pass a `role`, or set one with `/set_elevate_role`.",
                        color=var.COLOR_ERROR,
                    ),
                    ephemeral=True,
                )
                return

        rows = self.db.execute(
            "SELECT 1 FROM elevated_rights_grants WHERE guild_id = ? AND user_id = ? AND role_id = ?",
            (str(interaction.guild.id), str(member.id), role.id),
        )
        if not rows:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{member.mention} doesn't have an active temporary grant for **{role.name}**.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        self._remove_grant(str(interaction.guild.id), str(member.id), role.id)
        if role in member.roles:
            try:
                await member.remove_roles(role, reason=f"Temporary elevation revoked by {interaction.user}")
            except discord.Forbidden:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description="Grant record cleared, but I lack permission to remove the role itself.",
                        color=var.COLOR_ERROR,
                    ),
                    ephemeral=True,
                )
                return

        await interaction.response.send_message(
            embed=discord.Embed(description=f"Revoked **{role.name}** from {member.mention}.", color=var.COLOR_INFO),
            ephemeral=True,
        )

    @app_commands.command(name="elevate_list", description="List active temporary role grants.")
    @app_commands.describe(member="Show only this member's grants (optional)")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def elevate_list(self, interaction: discord.Interaction, member: discord.Member | None = None):
        now = int(time.time())
        if member:
            rows = [(member.id, role_id, granted_by, reason, expires_at)
                    for role_id, granted_by, reason, expires_at in self._get_grants_for_user(str(interaction.guild.id), str(member.id))]
        else:
            rows = self._get_grants_for_guild(str(interaction.guild.id))

        if not rows:
            await interaction.response.send_message("No active temporary role grants.", ephemeral=True)
            return

        lines = []
        for user_id, role_id, granted_by, reason, expires_at in rows:
            role = interaction.guild.get_role(role_id)
            remaining = format_duration(expires_at - now)
            role_name = role.mention if role else f"`{role_id}` (deleted)"
            reason_part = f" — *{reason}*" if reason else ""
            lines.append(f"<@{user_id}> — {role_name} — expires in **{remaining}**{reason_part}")

        await interaction.response.send_message(
            embed=discord.Embed(
                title="Active Temporary Role Grants",
                description="\n".join(lines[:25]),
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )


    @app_commands.command(name="set_elevate_role", description="Set the default role /elevate grants when no role is specified.")
    @app_commands.describe(role="The role /elevate should use by default")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_elevate_role(self, interaction: discord.Interaction, role: discord.Role):
        if role.is_default() or role.managed:
            await interaction.response.send_message(
                embed=discord.Embed(description="That role can't be used for elevation.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"I can't assign **{role.name}** — it's above or equal to my highest role. "
                                f"Move my role above it first.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        self._set_cfg("elevate_role_id", str(role.id))
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"Default elevate role set to **{role.name}**. `/elevate` will use it when `role` is omitted.",
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="set_elevate_time", description="Change the default and/or max duration allowed for /elevate.")
    @app_commands.describe(
        default_duration="New default duration used when /elevate omits one, e.g. 30m, 2h, 1d",
        max_duration_hours="New cap on grant length in hours (0 to remove the cap)",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_elevate_time(
        self,
        interaction: discord.Interaction,
        default_duration: str | None = None,
        max_duration_hours: app_commands.Range[int, 0, None] | None = None,
    ):
        if default_duration is None and max_duration_hours is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="Provide `default_duration`, `max_duration_hours`, or both.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        if default_duration is not None:
            seconds = parse_duration(default_duration)
            if seconds is None:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description=f"Couldn't parse duration `{default_duration}`. Try formats like `30m`, `2h`, or `1d12h`.",
                        color=var.COLOR_ERROR,
                    ),
                    ephemeral=True,
                )
                return
            effective_cap = max_duration_hours if max_duration_hours is not None else self._max_duration_hours()
            if effective_cap and seconds > effective_cap * 3600:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description=f"That default exceeds the current max of {effective_cap} hours.",
                        color=var.COLOR_ERROR,
                    ),
                    ephemeral=True,
                )
                return
            self._set_cfg("default_duration", default_duration)

        if max_duration_hours is not None:
            self._set_cfg("max_duration_hours", str(max_duration_hours))

        await interaction.response.send_message(
            embed=discord.Embed(
                description=(
                    f"Default elevate duration: **{self._default_duration()}**\n"
                    f"Max elevate duration: **{self._max_duration_hours() or 'no cap'}"
                    f"{' hours' if self._max_duration_hours() else ''}**"
                ),
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ElevatedRights(bot))
