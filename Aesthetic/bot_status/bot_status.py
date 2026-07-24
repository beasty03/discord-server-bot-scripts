import json
import logging
from pathlib import Path
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('bot_status_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

log = logging.getLogger("launcher")

_CONFIG_FILE = Path(__file__).parent / "bot_status_config.json"

_STATUS_MAP = {
    "online":    discord.Status.online,
    "idle":      discord.Status.idle,
    "dnd":       discord.Status.dnd,
    "invisible": discord.Status.invisible,
}
_ACTIVITY_MAP = {
    "playing":   discord.ActivityType.playing,
    "watching":  discord.ActivityType.watching,
    "listening": discord.ActivityType.listening,
    "competing": discord.ActivityType.competing,
}


class BotStatus(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cfg = self._load_cfg()

    # ── Runtime config (JSON, persists status/activity across restarts) ───────

    def _load_cfg(self) -> dict:
        if _CONFIG_FILE.exists():
            try:
                return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_cfg(self):
        _CONFIG_FILE.write_text(json.dumps(self._cfg, indent=2), encoding="utf-8")

    def _build_activity(self) -> discord.Activity | None:
        atype = self._cfg.get("activity_type")
        text  = self._cfg.get("activity_text")
        if not atype or not text:
            return None
        return discord.Activity(type=_ACTIVITY_MAP[atype], name=text)

    async def _apply_presence(self):
        status = _STATUS_MAP.get(self._cfg.get("status"), discord.Status.online)
        await self.bot.change_presence(status=status, activity=self._build_activity())

    @commands.Cog.listener()
    async def on_ready(self):
        if self._cfg:
            await self._apply_presence()

    # ── /set_bot_status ───────────────────────────────────────────────────────

    @app_commands.command(name="set_bot_status", description="Change the bot's online status.")
    @app_commands.describe(status="Which status to show")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_bot_status(self, interaction: discord.Interaction, status: Literal["online", "idle", "dnd", "invisible"]):
        self._cfg["status"] = status
        self._save_cfg()
        await self._apply_presence()
        await interaction.response.send_message(
            embed=discord.Embed(description=f"✅ Status set to **{status}**.", color=var.COLOR_INFO),
            ephemeral=True,
        )

    # ── /set_bot_activity ─────────────────────────────────────────────────────

    @app_commands.command(name="set_bot_activity", description="Change the bot's activity (the line shown under its name).")
    @app_commands.describe(type="Activity verb shown before the text", text="The activity text, e.g. 'with fire'")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_bot_activity(
        self,
        interaction: discord.Interaction,
        type: Literal["playing", "watching", "listening", "competing"],
        text: str,
    ):
        self._cfg["activity_type"] = type
        self._cfg["activity_text"] = text
        self._save_cfg()
        await self._apply_presence()
        await interaction.response.send_message(
            embed=discord.Embed(description=f"✅ Activity set to **{type.capitalize()} {text}**.", color=var.COLOR_INFO),
            ephemeral=True,
        )

    # ── /clear_bot_activity ───────────────────────────────────────────────────

    @app_commands.command(name="clear_bot_activity", description="Remove the bot's current activity, keeping its status.")
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_bot_activity(self, interaction: discord.Interaction):
        self._cfg.pop("activity_type", None)
        self._cfg.pop("activity_text", None)
        self._save_cfg()
        await self._apply_presence()
        await interaction.response.send_message(
            embed=discord.Embed(description="✅ Activity cleared.", color=var.COLOR_INFO),
            ephemeral=True,
        )

    # ── /view_bot_status ──────────────────────────────────────────────────────

    @app_commands.command(name="view_bot_status", description="Show the bot's currently configured status and activity.")
    async def view_bot_status(self, interaction: discord.Interaction):
        status = self._cfg.get("status", "online")
        atype  = self._cfg.get("activity_type")
        text   = self._cfg.get("activity_text")
        activity_line = f"{atype.capitalize()} {text}" if atype and text else "*(none set)*"
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🤖 Bot Status",
                description=f"Status: `{status}`\nActivity: {activity_line}",
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(BotStatus(bot))
    log.info("✅ Aesthetic/BotStatus cog loaded")
