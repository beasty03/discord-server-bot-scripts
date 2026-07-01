import importlib.util as _ilu
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

_spec = _ilu.spec_from_file_location("panel_variables", Path(__file__).parent / "variables.py")
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

_lspec_log = _ilu.spec_from_file_location("panel_log_config", Path(__file__).parent / "log_config.py")
_lmod_log = _ilu.module_from_spec(_lspec_log)
_lspec_log.loader.exec_module(_lmod_log)
CATEGORIES = _lmod_log.CATEGORIES
get_all    = _lmod_log.get_all
toggle_log = _lmod_log.toggle_log

log = logging.getLogger(__name__)

# ── category literals for slash command choices ───────────────────────────────
_CAT_KEYS = list(CATEGORIES.keys())
_CatLiteral = Literal[
    "house_daily",
    "fight_results",
    "api_warnings",
    "automod",
    "tamagotchi",
]


# ============================================================================
# COG
# ============================================================================

class AdminPanelCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /bot_status ───────────────────────────────────────────────────────────

    @app_commands.command(name="bot_status", description="View the load status of every cog")
    @app_commands.default_permissions(administrator=True)
    async def bot_status(self, interaction: discord.Interaction):
        loaded = set(self.bot.cogs.keys())
        total_expected = total_loaded = 0
        all_ok = True
        embed = discord.Embed(
            title=f"⚙️ Cog Status — {var.SERVER_NAME}",
            timestamp=datetime.now(timezone.utc),
            color=var.COLOR_OK,
        )

        for group, cogs in var.COG_GROUPS.items():
            total_expected += len(cogs)
            missing = [c for c in cogs if c not in loaded]
            n_loaded = len(cogs) - len(missing)
            total_loaded += n_loaded

            if not missing:
                value = f"✅ All {len(cogs)} loaded"
            else:
                all_ok = False
                joined = ", ".join(f"`{c}`" for c in missing)
                value = f"⚠️ {n_loaded}/{len(cogs)} loaded\n❌ {joined}"

            embed.add_field(name=group, value=value, inline=True)

        ratio  = f"{total_loaded}/{total_expected}"
        color  = var.COLOR_OK if all_ok else (var.COLOR_WARN if total_loaded >= total_expected * 0.8 else var.COLOR_ERROR)
        embed.color = color
        embed.description = f"**{ratio}** cogs loaded"
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /log settings ─────────────────────────────────────────────────────────

    log = app_commands.Group(
        name="log",
        description="Control what gets posted to #bot-logs and #mod-logs",
        default_permissions=discord.Permissions(administrator=True),
    )

    @log.command(name="settings", description="Show all bot-logs category toggles")
    async def log_settings(self, interaction: discord.Interaction):
        settings = get_all()
        lines = []
        for key, desc in CATEGORIES.items():
            icon = "🟢" if settings[key] else "🔴"
            lines.append(f"{icon} **{key}** — {desc}")

        embed = discord.Embed(
            title="📋 Bot-Logs Settings",
            description="\n".join(lines),
            color=var.COLOR_PANEL,
        )
        embed.set_footer(text="Use /log toggle <category> to enable or disable a category.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /log toggle ───────────────────────────────────────────────────────────

    @log.command(name="toggle", description="Enable or disable a bot-logs category")
    @app_commands.describe(category="Which log category to toggle")
    async def log_toggle(self, interaction: discord.Interaction, category: _CatLiteral):
        new_state = toggle_log(category)
        icon = "🟢 enabled" if new_state else "🔴 disabled"
        desc = CATEGORIES.get(category, category)
        embed = discord.Embed(
            description=f"{icon} **{category}**\n{desc}",
            color=var.COLOR_OK if new_state else var.COLOR_ERROR,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminPanelCog(bot))
