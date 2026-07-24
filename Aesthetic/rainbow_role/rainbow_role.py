import colorsys
import logging
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('rainbow_role_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

ForgeDB.declare_schema(
    tables=[
        """CREATE TABLE IF NOT EXISTS rainbow_role_config (
               guild_id         TEXT PRIMARY KEY,
               role_id          INTEGER NOT NULL,
               interval_seconds INTEGER NOT NULL,
               hue              INTEGER NOT NULL DEFAULT 0
           )""",
    ],
)

log = logging.getLogger("launcher")


def _hue_to_color(hue: int) -> discord.Color:
    r, g, b = colorsys.hsv_to_rgb(hue / 360, 1.0, 1.0)
    return discord.Color.from_rgb(int(r * 255), int(g * 255), int(b * 255))


class RainbowRole(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()
        rows = self.db.execute("SELECT interval_seconds FROM rainbow_role_config LIMIT 1")
        interval = rows[0][0] if rows else var.DEFAULT_INTERVAL_SECONDS
        self._cycle.change_interval(seconds=interval)
        self._cycle.start()

    def cog_unload(self):
        self._cycle.cancel()

    # ── Database ──────────────────────────────────────────────────────────────

    def _get_row(self, guild_id: str) -> tuple | None:
        rows = self.db.execute(
            "SELECT role_id, interval_seconds, hue FROM rainbow_role_config WHERE guild_id = ?",
            (guild_id,),
        )
        return rows[0] if rows else None

    def _set_role(self, guild_id: str, role_id: int):
        self.db.execute(
            """INSERT INTO rainbow_role_config (guild_id, role_id, interval_seconds, hue)
               VALUES (?, ?, ?, 0)
               ON CONFLICT(guild_id) DO UPDATE SET role_id = excluded.role_id""",
            (guild_id, role_id, var.DEFAULT_INTERVAL_SECONDS),
        )

    def _set_interval(self, guild_id: str, seconds: int):
        self.db.execute(
            "UPDATE rainbow_role_config SET interval_seconds = ? WHERE guild_id = ?",
            (seconds, guild_id),
        )

    def _set_hue(self, guild_id: str, hue: int):
        self.db.execute(
            "UPDATE rainbow_role_config SET hue = ? WHERE guild_id = ?",
            (hue, guild_id),
        )

    def _all_rows(self) -> list[tuple]:
        return self.db.execute("SELECT guild_id, role_id, hue FROM rainbow_role_config") or []

    # ── Background color cycle ───────────────────────────────────────────────

    @tasks.loop(seconds=var.DEFAULT_INTERVAL_SECONDS)
    async def _cycle(self):
        for guild_id, role_id, hue in self._all_rows():
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                continue
            role = guild.get_role(role_id)
            if role is None:
                continue
            new_hue = (hue + var.HUE_STEP_DEGREES) % 360
            try:
                await role.edit(color=_hue_to_color(new_hue), reason="Rainbow role color cycle")
            except (discord.Forbidden, discord.HTTPException) as e:
                log.warning("[RainbowRole] Failed to update role color in %s: %s", guild_id, e)
                continue
            self._set_hue(guild_id, new_hue)

    @_cycle.before_loop
    async def _before_cycle(self):
        await self.bot.wait_until_ready()

    # ── /rainbow_join ─────────────────────────────────────────────────────────

    @app_commands.command(name="rainbow_join", description="Get the rainbow role — its color cycles automatically.")
    async def rainbow_join(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        row = self._get_row(guild_id)

        if row is None:
            if not interaction.guild.me.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description="⚠️ I need the **Manage Roles** permission to create the rainbow role.",
                        color=var.COLOR_ERROR,
                    ),
                    ephemeral=True,
                )
                return
            try:
                role = await interaction.guild.create_role(
                    name=var.DEFAULT_ROLE_NAME,
                    color=_hue_to_color(0),
                    reason="Rainbow role auto-created by /rainbow_join",
                )
                try:
                    await role.edit(position=max(interaction.guild.me.top_role.position - 1, 1))
                except (discord.Forbidden, discord.HTTPException):
                    pass
            except discord.Forbidden:
                await interaction.response.send_message(
                    embed=discord.Embed(description="⚠️ I don't have permission to create roles.", color=var.COLOR_ERROR),
                    ephemeral=True,
                )
                return
            self._set_role(guild_id, role.id)
        else:
            role = interaction.guild.get_role(row[0])
            if role is None:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description="⚠️ The configured rainbow role no longer exists. Ask an admin to run `/set_rainbow_role` again.",
                        color=var.COLOR_ERROR,
                    ),
                    ephemeral=True,
                )
                return

        if role in interaction.user.roles:
            await interaction.response.send_message(
                embed=discord.Embed(description=f"You already have {role.mention}.", color=var.COLOR_INFO),
                ephemeral=True,
            )
            return

        try:
            await interaction.user.add_roles(role, reason="Joined the rainbow role")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=discord.Embed(description="⚠️ I don't have permission to assign that role.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"🌈 You now have {role.mention} — its color will keep shifting.",
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )

    # ── /rainbow_leave ────────────────────────────────────────────────────────

    @app_commands.command(name="rainbow_leave", description="Remove your rainbow role.")
    async def rainbow_leave(self, interaction: discord.Interaction):
        row = self._get_row(str(interaction.guild.id))
        if row is None:
            await interaction.response.send_message(
                embed=discord.Embed(description="No rainbow role is set up on this server yet.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        role = interaction.guild.get_role(row[0])
        if role is None or role not in interaction.user.roles:
            await interaction.response.send_message(
                embed=discord.Embed(description="You don't have the rainbow role.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        try:
            await interaction.user.remove_roles(role, reason="Left the rainbow role")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=discord.Embed(description="⚠️ I don't have permission to remove that role.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=discord.Embed(description="Removed your rainbow role.", color=var.COLOR_INFO),
            ephemeral=True,
        )

    # ── /set_rainbow_role ─────────────────────────────────────────────────────

    @app_commands.command(name="set_rainbow_role", description="Use an existing role as the rainbow role instead of an auto-created one.")
    @app_commands.describe(role="The role that should cycle colors")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_rainbow_role(self, interaction: discord.Interaction, role: discord.Role):
        if role.is_default() or role.managed:
            await interaction.response.send_message(
                embed=discord.Embed(description="That role can't be used for this.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"I can't edit **{role.name}** — it's above or equal to my highest role.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        self._set_role(str(interaction.guild.id), role.id)
        await interaction.response.send_message(
            embed=discord.Embed(description=f"✅ {role.mention} will now cycle colors.", color=var.COLOR_INFO),
            ephemeral=True,
        )

    # ── /set_rainbow_speed ────────────────────────────────────────────────────

    @app_commands.command(name="set_rainbow_speed", description="Change how often the rainbow role's color shifts.")
    @app_commands.describe(seconds="Seconds between color shifts")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_rainbow_speed(
        self,
        interaction: discord.Interaction,
        seconds: app_commands.Range[int, var.MIN_INTERVAL_SECONDS, None],
    ):
        guild_id = str(interaction.guild.id)
        row = self._get_row(guild_id)
        if row is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="No rainbow role is set up yet — use `/rainbow_join` or `/set_rainbow_role` first.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        self._set_interval(guild_id, seconds)
        self._cycle.change_interval(seconds=seconds)
        await interaction.response.send_message(
            embed=discord.Embed(description=f"✅ Rainbow role now shifts color every **{seconds}s**.", color=var.COLOR_INFO),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(RainbowRole(bot))
    log.info("✅ Aesthetic/RainbowRole cog loaded")
