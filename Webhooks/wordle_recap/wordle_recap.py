import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import aiohttp
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones
from pathlib import Path

import json

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('wordle_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

log               = logging.getLogger("launcher")
NYT_WORDLE_API    = "https://www.nytimes.com/svc/wordle/v2/{date}.json"
_SORTED_TIMEZONES = sorted(available_timezones())
_CONFIG_FILE      = Path(__file__).parent / "wordle_config.json"


class WordleRecap(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot         = bot
        self._cfg        = self._load_cfg()
        self.post_hour   = self._cfg.get("post_hour",   var.WORDLE_POST_HOUR)
        self.post_minute = self._cfg.get("post_minute", var.WORDLE_POST_MINUTE)
        self._last_posted: date | None = None

    # ── JSON config ───────────────────────────────────────────────────────────

    def _load_cfg(self) -> dict:
        if _CONFIG_FILE.exists():
            try:
                return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_cfg(self):
        _CONFIG_FILE.write_text(json.dumps(self._cfg, indent=2), encoding="utf-8")

    def _get_cfg(self, key: str):
        return self._cfg.get(key)

    def _set_cfg(self, key: str, value):
        self._cfg[key] = value
        self._save_cfg()

    def _get_tz(self) -> ZoneInfo:
        name = self._get_cfg("timezone") or var.WORDLE_TIMEZONE
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.wordle_timer.is_running():
            self.wordle_timer.start()
        tz = self._get_tz()
        log.info(
            "[WordleRecap] Ready — posting daily recap at %02d:%02d %s in #%s",
            self.post_hour, self.post_minute, tz.key, var.DEFAULT_CHANNEL_NAME,
        )

    def cog_unload(self):
        if self.wordle_timer.is_running():
            self.wordle_timer.cancel()

    # ── Scheduled task ────────────────────────────────────────────────────────

    @tasks.loop(minutes=1)
    async def wordle_timer(self):
        now = datetime.now(self._get_tz())
        if now.hour != self.post_hour or now.minute != self.post_minute:
            return
        yesterday = now.date() - timedelta(days=1)
        if self._last_posted == yesterday:
            return
        self._last_posted = yesterday
        await self._post_wordle_recap(yesterday)

    # ── Core logic ────────────────────────────────────────────────────────────

    async def _post_wordle_recap(self, target_date: date):
        channel = self._resolve_channel()
        if channel is None:
            log.warning("[WordleRecap] No channel found — skipping post for %s.", target_date)
            return

        solution, wordle_number = await self._fetch_wordle(target_date)
        if solution is None:
            log.error("[WordleRecap] Could not fetch Wordle answer for %s.", target_date)
            await channel.send(embed=discord.Embed(
                title="Wordle Recap Unavailable",
                description=f"Could not retrieve the Wordle answer for {target_date.strftime('%B %d, %Y')}.",
                color=var.COLOR_ERROR,
            ))
            return

        number_label = f" #{wordle_number}" if wordle_number is not None else ""
        embed = discord.Embed(
            title=f"Wordle{number_label} — {target_date.strftime('%B %d, %Y')}",
            description=f"Yesterday's Wordle answer was:\n\n# **{solution.upper()}**",
            color=var.COLOR_INFO,
        )
        embed.set_footer(text="A new Wordle is available at nytimes.com/games/wordle")
        await channel.send(embed=embed)

    async def _fetch_wordle(self, target_date: date) -> tuple[str | None, int | None]:
        url = NYT_WORDLE_API.format(date=target_date.isoformat())
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        log.error("[WordleRecap] API returned HTTP %s for %s.", resp.status, target_date)
                        return None, None
                    data = await resp.json()
                    return data.get("solution"), data.get("days_since_launch")
        except Exception as exc:
            log.error("[WordleRecap] API request failed: %s", exc)
            return None, None

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

    # ── Slash commands ────────────────────────────────────────────────────────

    @app_commands.command(name="set_wordle_channel", description="Set the channel where the daily Wordle recap is posted.")
    @app_commands.describe(channel="Text channel to post the recap in")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_wordle_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self._set_cfg("channel_id", str(channel.id))
        await interaction.response.send_message(
            embed=discord.Embed(description=f"Wordle recap will be posted in {channel.mention}.", color=var.COLOR_INFO),
            ephemeral=True,
        )

    @app_commands.command(name="set_wordle_time", description="Set the time the daily Wordle recap is posted (uses your configured timezone).")
    @app_commands.describe(hour="Hour (0–23)", minute="Minute (0–59)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_wordle_time(self, interaction: discord.Interaction, hour: int, minute: int):
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            await interaction.response.send_message("Invalid time — hour must be 0–23 and minute 0–59.", ephemeral=True)
            return
        self.post_hour   = hour
        self.post_minute = minute
        self._set_cfg("post_hour",   str(hour))
        self._set_cfg("post_minute", str(minute))
        tz = self._get_tz()
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"Wordle recap will post daily at **{hour:02d}:{minute:02d}** ({tz.key}).",
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="set_wordle_timezone", description="Set the timezone for the Wordle recap post time (e.g. Europe/Brussels).")
    @app_commands.describe(timezone="Start typing to search — e.g. Brussels, New_York, London")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_wordle_timezone(self, interaction: discord.Interaction, timezone: str):
        try:
            tz = ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            await interaction.response.send_message(
                f"`{timezone}` is not a valid timezone. Use an IANA name like `Europe/Brussels` or `America/New_York`.",
                ephemeral=True,
            )
            return
        self._set_cfg("timezone", timezone)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"Timezone set to **{tz.key}**. Post time is now interpreted in that timezone.",
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )

    @set_wordle_timezone.autocomplete("timezone")
    async def timezone_autocomplete(self, _interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        lower   = current.lower()
        matches = [tz for tz in _SORTED_TIMEZONES if lower in tz.lower()]
        return [app_commands.Choice(name=tz, value=tz) for tz in matches[:25]]

    @app_commands.command(name="wordle_recap", description="Manually post yesterday's Wordle answer right now.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def wordle_recap_manual(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        yesterday = datetime.now(self._get_tz()).date() - timedelta(days=1)
        await self._post_wordle_recap(yesterday)
        await interaction.followup.send("Wordle recap posted!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WordleRecap(bot))
