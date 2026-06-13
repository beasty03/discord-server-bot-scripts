import asyncio
import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('me_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from utils.config_loader import load_config

log = logging.getLogger("launcher")
SETTINGS_FILE = Path(__file__).parent / 'multiplier_event_settings.json'


class MultiplierEventCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._settings: dict = self._load_settings()
        self._event_task: asyncio.Task | None = None
        if not hasattr(self.bot, 'multiplier_event_mult'):
            self.bot.multiplier_event_mult = None

    # ── Settings ──────────────────────────────────────────────────────────────

    def _load_settings(self) -> dict:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_settings(self):
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._settings, f, indent=2)

    def _get_channel(self) -> discord.TextChannel | None:
        shared = load_config().get('multiplier_announcement_channel_id')
        if shared:
            ch = self.bot.get_channel(int(shared))
            if ch:
                return ch
        cid = self._settings.get('event_channel_id') or var.EVENT_CHANNEL_ID
        return self.bot.get_channel(int(cid)) if cid else None

    # ── Background event task ─────────────────────────────────────────────────

    async def _run_event(self, multiplier: float):
        duration = self._settings.get('event_duration', var.EVENT_DURATION)
        end_ts   = int(time.time()) + duration
        channel  = self._get_channel()

        if channel:
            mins, secs = divmod(duration, 60)
            embed = discord.Embed(
                title="✨ Multiplier Event!",
                description=(
                    f"All {var.CURRENCY_NAME} earnings are boosted by **{multiplier}x** "
                    f"for the next **{mins}m {secs:02d}s**!\n\n"
                    f"Event ends <t:{end_ts}:R>"
                ),
                color=var.COLOR_ACTIVE,
            )
            embed.timestamp = datetime.utcnow()
            await channel.send(embed=embed)

        try:
            await asyncio.sleep(duration)
        except asyncio.CancelledError:
            pass
        finally:
            self.bot.multiplier_event_mult = None
            ch = self._get_channel()
            if ch:
                try:
                    embed = discord.Embed(
                        title="✨ Multiplier Event Ended",
                        description="The bonus multiplier has expired. Regular payouts resume.",
                        color=var.COLOR_END,
                    )
                    embed.timestamp = datetime.utcnow()
                    await ch.send(embed=embed)
                except Exception:
                    pass

    def _pick_multiplier(self) -> float:
        mult_min = self._settings.get('multiplier_min', var.MULTIPLIER_MIN)
        mult_max = self._settings.get('multiplier_max', var.MULTIPLIER_MAX)
        return round(random.uniform(mult_min, mult_max), 2)

    def _start_task(self, multiplier: float):
        if self._event_task and not self._event_task.done():
            self._event_task.cancel()
        self._event_task = asyncio.create_task(self._run_event(multiplier))

    # Called by /startevent multiplier in casino_event.py
    async def start_from_startevent(self, interaction: discord.Interaction):
        if self.bot.multiplier_event_mult is not None:
            await interaction.response.send_message(
                f"❌ A Multiplier event is already active! (multiplier: **{self.bot.multiplier_event_mult}x**)",
                ephemeral=True,
            )
            return
        multiplier = self._pick_multiplier()
        duration   = self._settings.get('event_duration', var.EVENT_DURATION)
        self.bot.multiplier_event_mult = multiplier
        self._start_task(multiplier)
        end_ts = int(time.time()) + duration
        mins, secs = divmod(duration, 60)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=(
                    f"✅ Multiplier event started!\n"
                    f"Multiplier: **{multiplier}x** · Duration: **{mins}m {secs:02d}s**\n"
                    f"Ends <t:{end_ts}:R>"
                ),
                color=var.COLOR_ACTIVE,
            ),
            ephemeral=True,
        )

    # ── Commands ──────────────────────────────────────────────────────────────

    @app_commands.command(name="start_multiplier_event", description="Start a Multiplier event — all earnings are boosted.")
    async def start_event(self, interaction: discord.Interaction):
        await self.start_from_startevent(interaction)

    @app_commands.command(name="stop_multiplier_event", description="Stop the active Multiplier event early.")
    async def stop_event(self, interaction: discord.Interaction):
        if self.bot.multiplier_event_mult is None:
            await interaction.response.send_message("❌ No Multiplier event is currently active.", ephemeral=True)
            return
        if self._event_task and not self._event_task.done():
            self._event_task.cancel()
        self.bot.multiplier_event_mult = None
        channel = self._get_channel()
        if channel:
            await channel.send(embed=discord.Embed(
                title="✨ Multiplier Event Ended",
                description="The event was stopped early by an admin.",
                color=var.COLOR_END,
            ))
        await interaction.response.send_message("✅ Multiplier event stopped.", ephemeral=True)

    @app_commands.command(name="set_multiplier_channel", description="Set the channel for Multiplier event announcements.")
    @app_commands.describe(channel="Channel to post announcements in")
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self._settings['event_channel_id'] = channel.id
        self._save_settings()
        await interaction.response.send_message(
            f"✅ Multiplier event channel set to {channel.mention}.", ephemeral=True
        )

    @app_commands.command(name="set_multiplier_duration", description="Set how long a Multiplier event lasts.")
    @app_commands.describe(seconds="Duration in seconds (e.g. 300 = 5 minutes)")
    async def set_duration(self, interaction: discord.Interaction, seconds: int):
        if seconds < 30:
            await interaction.response.send_message("❌ Duration must be at least 30 seconds.", ephemeral=True)
            return
        self._settings['event_duration'] = seconds
        self._save_settings()
        mins, secs = divmod(seconds, 60)
        label = f"{mins}m {secs:02d}s" if mins else f"{secs}s"
        await interaction.response.send_message(f"✅ Event duration set to **{label}**.", ephemeral=True)

    @app_commands.command(name="set_multiplier_min", description="Set the minimum bonus multiplier.")
    @app_commands.describe(value="Minimum multiplier (e.g. 1.1 = +10% earnings)")
    async def set_min(self, interaction: discord.Interaction, value: float):
        if value < 1.0:
            await interaction.response.send_message("❌ Minimum must be ≥ 1.0.", ephemeral=True)
            return
        self._settings['multiplier_min'] = value
        self._save_settings()
        await interaction.response.send_message(f"✅ Minimum multiplier set to **{value}x**.", ephemeral=True)

    @app_commands.command(name="set_multiplier_max", description="Set the maximum bonus multiplier.")
    @app_commands.describe(value="Maximum multiplier (e.g. 2.0 = double earnings)")
    async def set_max(self, interaction: discord.Interaction, value: float):
        if value < 1.0:
            await interaction.response.send_message("❌ Maximum must be ≥ 1.0.", ephemeral=True)
            return
        self._settings['multiplier_max'] = value
        self._save_settings()
        await interaction.response.send_message(f"✅ Maximum multiplier set to **{value}x**.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MultiplierEventCog(bot))
    log.info("✅ Events/MultiplierEvent cog loaded")
