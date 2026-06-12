import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import aiohttp
from datetime import datetime, timezone, date, timedelta
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('wordle_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from cogs.Database_management.database_manager import DatabaseManager

db_manager = DatabaseManager(starting_balance=0)

log = logging.getLogger("launcher")

NYT_WORDLE_API = "https://www.nytimes.com/svc/wordle/v2/{date}.json"


class WordleRecap(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.post_hour   = var.WORDLE_POST_HOUR
        self.post_minute = var.WORDLE_POST_MINUTE
        self._last_posted: date | None = None
        self._register_tables()
        self._load_settings()

    def cog_unload(self):
        if self.wordle_timer.is_running():
            self.wordle_timer.cancel()

    # ── Database ─────────────────────────────────────────────────────────────

    def _register_tables(self):
        db_manager.register_table("""
            CREATE TABLE IF NOT EXISTS wordle_config (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

    def _get_cfg(self, key: str) -> str | None:
        rows = db_manager.execute("SELECT value FROM wordle_config WHERE key = ?", (key,))
        return rows[0][0] if rows else None

    def _set_cfg(self, key: str, value: str):
        db_manager.execute(
            "INSERT OR REPLACE INTO wordle_config (key, value) VALUES (?, ?)",
            (key, str(value)),
        )

    def _load_settings(self):
        h = self._get_cfg("post_hour")
        m = self._get_cfg("post_minute")
        if h is not None:
            self.post_hour = int(h)
        if m is not None:
            self.post_minute = int(m)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.wordle_timer.is_running():
            self.wordle_timer.start()
        log.info(
            "[WordleRecap] Ready — posting daily recap at %02d:%02d UTC in #%s",
            self.post_hour, self.post_minute, var.DEFAULT_CHANNEL_NAME,
        )

    # ── Scheduled task ────────────────────────────────────────────────────────

    @tasks.loop(minutes=1)
    async def wordle_timer(self):
        now = datetime.now(timezone.utc)
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

    @app_commands.command(
        name="set_wordle_channel",
        description="Set the channel where the daily Wordle recap is posted.",
    )
    @app_commands.describe(channel="Text channel to post the recap in")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_wordle_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self._set_cfg("channel_id", str(channel.id))
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"Wordle recap will be posted in {channel.mention}.",
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="set_wordle_time",
        description="Set the UTC time the daily Wordle recap is posted (default 00:05).",
    )
    @app_commands.describe(hour="Hour in UTC (0–23)", minute="Minute (0–59)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_wordle_time(self, interaction: discord.Interaction, hour: int, minute: int):
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            await interaction.response.send_message(
                "Invalid time — hour must be 0–23 and minute 0–59.", ephemeral=True
            )
            return
        self.post_hour   = hour
        self.post_minute = minute
        self._set_cfg("post_hour",   str(hour))
        self._set_cfg("post_minute", str(minute))
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"Wordle recap will post daily at **{hour:02d}:{minute:02d} UTC**.",
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="wordle_recap",
        description="Manually post yesterday's Wordle answer right now.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def wordle_recap_manual(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
        await self._post_wordle_recap(yesterday)
        await interaction.followup.send("Wordle recap posted!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WordleRecap(bot))
