import discord
from discord.ext import commands
from discord import app_commands
import logging
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('cfg_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

_cg_spec = _ilu.spec_from_file_location('channel_guard', Path(__file__).parent / 'channel_guard.py')
_cg = _ilu.module_from_spec(_cg_spec)
_cg_spec.loader.exec_module(_cg)
BotConfig = _cg.BotConfig
global_interaction_check = _cg.global_interaction_check

log = logging.getLogger("launcher")


class ConfigCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.tree.interaction_check = global_interaction_check
        log.info("✅ Global channel/role guard active")

    def cog_unload(self):
        try:
            del self.bot.tree.interaction_check
        except AttributeError:
            pass

    # ── Allowed channels ──────────────────────────────────────────────────────

    @app_commands.command(name="add_allowed_channel", description="Add a channel where bot commands can be used.")
    @app_commands.describe(channel="Channel to allow")
    async def add_allowed_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        BotConfig().add_allowed(channel.id, channel.name)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ {channel.mention} added to allowed channels.",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="remove_allowed_channel", description="Remove a channel from the allowed list.")
    @app_commands.describe(channel="Channel to remove")
    async def remove_allowed_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        BotConfig().remove_allowed(channel.id)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ {channel.mention} removed from allowed channels.",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )

    # ── Control panel ─────────────────────────────────────────────────────────

    @app_commands.command(name="set_control_panel", description="Set the channel where admin/set commands must be run.")
    @app_commands.describe(channel="The control panel channel")
    async def set_control_panel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        BotConfig().set_control_panel(channel.id, channel.name)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Control panel set to {channel.mention}.",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )

    # ── Staff roles ───────────────────────────────────────────────────────────

    @app_commands.command(name="set_staff_roles", description="Set which roles count as Admin/Moderator for bot commands.")
    @app_commands.describe(
        role1="First staff role",
        role2="Second staff role (optional)",
        role3="Third staff role (optional)",
        role4="Fourth staff role (optional)",
    )
    async def set_staff_roles(
        self,
        interaction: discord.Interaction,
        role1: discord.Role,
        role2: discord.Role | None = None,
        role3: discord.Role | None = None,
        role4: discord.Role | None = None,
    ):
        roles = [r for r in [role1, role2, role3, role4] if r is not None]
        BotConfig().set_staff_roles([r.name for r in roles])
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Staff roles set to: {', '.join(r.mention for r in roles)}.",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )

    # ── View current config ───────────────────────────────────────────────────

    @app_commands.command(name="view_config", description="Show the current channel and role configuration.")
    async def view_config(self, interaction: discord.Interaction):
        cfg = BotConfig()

        allowed = cfg.allowed_channels()
        allowed_val = (
            "\n".join(f"<#{c['id']}> (#{c['name']})" for c in allowed)
            if allowed else f"*(default: #{', #'.join(cfg.allowed_names())})*"
        )

        cp = cfg.control_panel()
        cp_val = f"<#{cp['id']}> (#{cp['name']})" if cp else f"*(default: #{cfg.control_panel_name()})*"

        staff = cfg.staff_role_names()
        staff_val = ", ".join(f"**{r}**" for r in staff)

        embed = discord.Embed(title="⚙️ Bot Configuration", color=var.COLOR_INFO)
        embed.add_field(name="Allowed Channels",  value=allowed_val, inline=False)
        embed.add_field(name="Control Panel",     value=cp_val,      inline=False)
        embed.add_field(name="Staff Role Names",  value=staff_val,   inline=False)
        embed.set_footer(text=var.SERVER_NAME)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ConfigCog(bot))
    log.info("✅ General/Config cog loaded")
