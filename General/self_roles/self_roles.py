import discord
from discord.ext import commands
from discord import app_commands
import logging
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('self_roles_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

ForgeDB.declare_schema(
    tables=[
        """CREATE TABLE IF NOT EXISTS self_roles_list (
               role_id INTEGER PRIMARY KEY,
               label   TEXT    NOT NULL
           )""",
        """CREATE TABLE IF NOT EXISTS self_roles_config (
               key   TEXT PRIMARY KEY,
               value TEXT NOT NULL
           )""",
    ],
)

log      = logging.getLogger("launcher")
MAX_ROLES = 25


class SelfRoleButton(discord.ui.Button):
    def __init__(self, role_id: int, label: str):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            custom_id=f"selfrole_{role_id}",
        )
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(self.role_id)
        if role is None:
            await interaction.response.send_message(
                "This role no longer exists. Ask an admin to update the panel.", ephemeral=True
            )
            return
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"Removed **{role.name}**.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Added **{role.name}**.", ephemeral=True)


class SelfRoles(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    # ── Database ──────────────────────────────────────────────────────────────

    def _get_cfg(self, key: str) -> str | None:
        rows = self.db.execute("SELECT value FROM self_roles_config WHERE key = ?", (key,))
        return rows[0][0] if rows else None

    def _set_cfg(self, key: str, value: str):
        self.db.execute(
            "INSERT OR REPLACE INTO self_roles_config (key, value) VALUES (?, ?)",
            (key, str(value)),
        )

    def _get_roles(self) -> list[tuple[int, str]]:
        rows = self.db.execute("SELECT role_id, label FROM self_roles_list ORDER BY rowid")
        return rows if rows else []

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_view(self, roles: list[tuple[int, str]]) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        for role_id, label in roles:
            view.add_item(SelfRoleButton(role_id=role_id, label=label))
        return view

    def _build_embed(self, roles: list[tuple[int, str]]) -> discord.Embed:
        return discord.Embed(
            title=var.PANEL_TITLE,
            description=var.PANEL_DESCRIPTION if roles else "*No self-assignable roles have been added yet.*",
            color=var.PANEL_COLOR,
        )

    def _resolve_channel(self) -> discord.TextChannel | None:
        guild = self.bot.get_guild(var.GUILD_ID)
        if guild is None:
            return None
        cid = self._get_cfg("channel_id")
        if cid:
            ch = guild.get_channel(int(cid))
            if ch:
                return ch
        return discord.utils.get(guild.text_channels, name=var.DEFAULT_CHANNEL_NAME)

    async def _sync_message(self):
        channel = self._resolve_channel()
        if channel is None:
            log.warning("[SelfRoles] No channel configured — cannot sync role panel.")
            return

        roles = self._get_roles()
        embed = self._build_embed(roles)
        view  = self._build_view(roles)
        self.bot.add_view(view)

        mid = self._get_cfg("message_id")
        if mid:
            try:
                msg = await channel.fetch_message(int(mid))
                await msg.edit(embed=embed, view=view)
                return
            except discord.NotFound:
                pass

        msg = await channel.send(embed=embed, view=view)
        self._set_cfg("message_id", str(msg.id))

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self):
        roles = self._get_roles()
        if roles:
            self.bot.add_view(self._build_view(roles))
        log.info("[SelfRoles] Ready — %d self-assignable role(s) registered.", len(roles))

    # ── Slash commands ────────────────────────────────────────────────────────

    @app_commands.command(name="selfroles_channel", description="Set the channel where the self-role panel is posted.")
    @app_commands.describe(channel="Text channel for the role panel")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def selfroles_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self._set_cfg("channel_id", str(channel.id))
        self._set_cfg("message_id", "")
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"Self-role channel set to {channel.mention}. Run `/selfroles_post` to post the panel.",
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="selfroles_add", description="Add a role to the self-role panel.")
    @app_commands.describe(role="The role to make self-assignable", label="Button label shown to users (defaults to the role name)")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def selfroles_add(self, interaction: discord.Interaction, role: discord.Role, label: str | None = None):
        if len(self._get_roles()) >= MAX_ROLES:
            await interaction.response.send_message(
                f"The panel is full ({MAX_ROLES} roles max). Remove one before adding another.",
                ephemeral=True,
            )
            return
        label = label or role.name
        self.db.execute(
            "INSERT OR REPLACE INTO self_roles_list (role_id, label) VALUES (?, ?)",
            (role.id, label),
        )
        await interaction.response.send_message(
            embed=discord.Embed(description=f"**{label}** added to the self-role panel.", color=var.COLOR_INFO),
            ephemeral=True,
        )
        await self._sync_message()

    @app_commands.command(name="selfroles_remove", description="Remove a role from the self-role panel.")
    @app_commands.describe(role="The role to remove from the panel")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def selfroles_remove(self, interaction: discord.Interaction, role: discord.Role):
        rows = self.db.execute("SELECT role_id FROM self_roles_list WHERE role_id = ?", (role.id,))
        if not rows:
            await interaction.response.send_message(f"**{role.name}** is not on the self-role panel.", ephemeral=True)
            return
        self.db.execute("DELETE FROM self_roles_list WHERE role_id = ?", (role.id,))
        await interaction.response.send_message(
            embed=discord.Embed(description=f"**{role.name}** removed from the self-role panel.", color=var.COLOR_INFO),
            ephemeral=True,
        )
        await self._sync_message()

    @app_commands.command(name="selfroles_post", description="Post or refresh the self-role panel in the configured channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def selfroles_post(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self._sync_message()
        await interaction.followup.send("Self-role panel posted!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SelfRoles(bot))
