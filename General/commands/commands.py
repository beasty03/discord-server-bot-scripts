import discord
from discord.ext import commands
from discord import app_commands
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('cmd_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")

# ── Category definitions ───────────────────────────────────────────────────────

# These sections are excluded from the public command channel but shown via /see_admin_commands.
_ADMIN_SECTIONS = [
    ("⚙️ Config",          "ConfigCog"),
    ("👋 Welcome System",  "WelcomeSystem"),
    ("📜 Rules",           "Rules"),
    ("📋 Commands",        "CommandsCog"),
]

# Admin category is intentionally excluded — admin commands are for server owners only
# and should not appear in the public command channel.
_CATEGORIES = [
    {
        "label":   "🎰 Casino",
        "color":   var.COLOR_CASINO,
        "sections": [
            ("🎲 Gamble",              "GambleCog"),
            ("🃏 Blackjack",           "BlackjackCog"),
            ("🎡 Roulette",            "RouletteCog"),
            ("🎴 Higher or Lower",     "HigherLowerCog"),
            ("🃏 Baccarat",            "BaccaratCog"),
            ("🎰 Slots",               "SlotsCog"),
            ("🏇 Horse Racing",        "HorseRacingCog"),
            ("🐸 Crossy Road",         "CrossyRoadCog"),
            ("🪙 Coin Flip",           "CoinFlipCog"),
            ("✂️ Rock Paper Scissors", "RPSCog"),
            ("🃏 Poker",               "PokerCog"),
            ("💣 Diamond Mines",       "DiamondMinesCog"),
            ("🚀 Rocket",              "RocketCog"),
            ("🎡 Spin the Wheel",      "SpinWheelCog"),
            ("🎲 Craps",               "CrapsCog"),
            ("🎯 Under/Over",          "UnderOverCog"),
        ],
    },
    {
        "label":   "👤 User",
        "color":   var.COLOR_USER,
        "sections": [
            ("🏦 Bank",        "BankCog"),
            ("📊 Stats",       "StatsCog"),
            ("🏆 Leaderboard", "LeaderboardCog"),
        ],
    },
    {
        "label":   "📋 General",
        "color":   var.COLOR_GENERAL,
        "sections": [
            ("🎭 Self Roles",    "SelfRoles"),
            ("💬 Quotes",        "QuotesCog"),
            ("📖 Help",          "HelpCog"),
        ],
    },
    {
        "label":   "🎉 Events",
        "color":   var.COLOR_EVENTS,
        "sections": [
            ("🎰 Casino Events",    "CasinoEventCog"),
            ("💰 Multiplier Event", "MultiplierEventCog"),
        ],
    },
    {
        "label":   "⚔️ DnD",
        "color":   var.COLOR_DND,
        "sections": [
            ("📜 Character",       "CharacterCog"),
            ("🛡️ Parties",        "PartiesCog"),
            ("🗡️ Dungeon Master", "DungeonMasterCog"),
            ("🏪 Shop",           "ShopCog"),
            ("⚗️ Recipes",        "RecipesCog"),
            ("📖 Scribe",         "ScribeCog"),
        ],
    },
    {
        "label":   "🔗 Webhooks",
        "color":   var.COLOR_HOOKS,
        "sections": [
            ("📰 Wordle Recap", "WordleRecap"),
        ],
    },
]


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _get_cfg(db, key: str) -> str | None:
    try:
        rows = db.execute("SELECT value FROM command_channel_config WHERE key = ?", (key,))
        return rows[0][0] if rows else None
    except Exception:
        return None


def _set_cfg(db, key: str, value: str):
    db.execute(
        "INSERT OR REPLACE INTO command_channel_config (key, value) VALUES (?, ?)",
        (key, str(value)),
    )


# ── Status checks ──────────────────────────────────────────────────────────────

def _status_line(ok: bool, ok_text: str, fail_text: str) -> str:
    return f"{'✅' if ok else '⚠️'} {ok_text if ok else fail_text}"


def _check_welcome(db) -> list[str]:
    lines = []

    try:
        rows = db.execute("SELECT value FROM welcome_config WHERE key = 'welcome_channel_id'")
        if rows:
            lines.append(f"✅ Welcome channel: <#{rows[0][0]}>")
        else:
            lines.append("⚠️ **Welcome channel not set** — run `/set_welcome_channel`")
    except Exception:
        lines.append("⚠️ **Welcome channel not set** — run `/set_welcome_channel`")

    try:
        rows = db.execute("SELECT value FROM welcome_config WHERE key = 'welcome_role_id'")
        if rows:
            lines.append(f"✅ Member role: <@&{rows[0][0]}>")
        else:
            lines.append("⚠️ **Member role not set** — run `/set_welcome_role`")
    except Exception:
        lines.append("⚠️ **Member role not set** — run `/set_welcome_role`")

    return lines


def _check_self_roles(db) -> str:
    try:
        rows = db.execute("SELECT value FROM self_roles_config WHERE key = 'channel_id'")
        if rows:
            return f"✅ Self-roles panel: <#{rows[0][0]}>"
        return "⚠️ **Roles panel not configured** — run `/self_roles_panel`"
    except Exception:
        return "⚠️ **Roles panel not configured** — run `/self_roles_panel`"


def _check_command_channel(db) -> str:
    cid = _get_cfg(db, "channel_id")
    if cid:
        return f"✅ Command channel: <#{cid}>"
    return "⚠️ **Command channel not set** — run `/set_command_channel`"


# ── Bot logs helper ────────────────────────────────────────────────────────────

def _bot_logs(guild: discord.Guild) -> discord.TextChannel | None:
    return discord.utils.get(guild.text_channels, name="bot-logs")


async def _post_or_update_status_in_logs(guild: discord.Guild, db):
    """Keep a single pinned status embed in #bot-logs, editing it in place on refresh."""
    ch = _bot_logs(guild)
    if not ch:
        return

    lines = _check_welcome(db)
    lines.append(_check_self_roles(db))
    lines.append(_check_command_channel(db))

    all_ok = all(l.startswith("✅") for l in lines)
    embed = discord.Embed(
        title="📊 Server Setup Status",
        description="\n".join(lines),
        color=var.COLOR_OK if all_ok else var.COLOR_WARN,
    )
    embed.set_footer(
        text=f"🤖 {var.SERVER_NAME}  •  Last refreshed {datetime.utcnow().strftime('%d %b %Y · %H:%M')} UTC"
    )

    mid = _get_cfg(db, "status_message_id")
    if mid:
        try:
            msg = await ch.fetch_message(int(mid))
            await msg.edit(embed=embed)
            return
        except discord.NotFound:
            pass
        except Exception as exc:
            log.warning("Commands: failed to edit status message in bot-logs: %s", exc)

    msg = await ch.send(embed=embed)
    _set_cfg(db, "status_message_id", str(msg.id))
    try:
        await msg.pin()
    except discord.Forbidden:
        log.warning("Commands: no permission to pin in #bot-logs")


# ── Embed builders ─────────────────────────────────────────────────────────────

def _build_status_embed(db) -> discord.Embed:
    lines = _check_welcome(db)
    lines.append(_check_self_roles(db))
    lines.append(_check_command_channel(db))

    all_ok = all(l.startswith("✅") for l in lines)

    embed = discord.Embed(
        title="📊 Server Setup Status",
        description="\n".join(lines),
        color=var.COLOR_OK if all_ok else var.COLOR_WARN,
    )
    embed.set_footer(
        text=f"🤖 {var.SERVER_NAME}  •  Last refreshed {datetime.utcnow().strftime('%d %b %Y · %H:%M')} UTC"
    )
    return embed


def _build_category_embed(bot: commands.Bot, cat: dict) -> discord.Embed | None:
    embed = discord.Embed(title=cat["label"], color=cat["color"])
    any_field = False

    for section_name, cog_name in cat["sections"]:
        cog  = bot.cogs.get(cog_name)
        if cog is None:
            continue
        cmds = [c for c in cog.get_app_commands() if not c.name.startswith("set_")]
        if not cmds:
            continue
        any_field = True
        lines = [
            f"`/{cmd.name}` — {cmd.description}" if cmd.description else f"`/{cmd.name}`"
            for cmd in sorted(cmds, key=lambda c: c.name)
        ]
        value = "\n".join(lines)
        if len(value) > 1020:
            value = value[:1020] + "\n…"
        embed.add_field(name=section_name, value=value, inline=False)

    return embed if any_field else None


def _build_all_embeds(bot: commands.Bot, db) -> list[discord.Embed]:
    embeds = []
    for cat in _CATEGORIES:
        e = _build_category_embed(bot, cat)
        if e:
            embeds.append(e)
        if len(embeds) >= 10:   # Discord allows max 10 embeds per message
            break
    return embeds


# ── Cog ────────────────────────────────────────────────────────────────────────

class CommandsCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    async def cog_load(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS command_channel_config (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

    @commands.Cog.listener()
    async def on_ready(self):
        """Auto-refresh the command list every time the bot starts up."""
        guild = self.bot.get_guild(var.GUILD_ID)
        if guild is None:
            return
        cid = _get_cfg(self.db, "channel_id")
        if not cid:
            return
        try:
            await self._post_or_update(guild)
            log.info("Commands: command list auto-updated on ready")
        except Exception as exc:
            log.warning("Commands: auto-update on ready failed: %s", exc)
        try:
            await _post_or_update_status_in_logs(guild, self.db)
        except Exception as exc:
            log.warning("Commands: status check on ready failed: %s", exc)

    # ── Internal: post or edit ─────────────────────────────────────────────────

    async def _post_or_update(self, guild: discord.Guild) -> discord.Message | None:
        cid = _get_cfg(self.db, "channel_id")
        if not cid:
            return None
        channel = guild.get_channel(int(cid))
        if not channel or not isinstance(channel, discord.TextChannel):
            return None

        embeds = _build_all_embeds(self.bot, self.db)
        mid    = _get_cfg(self.db, "message_id")

        if mid:
            try:
                msg = await channel.fetch_message(int(mid))
                await msg.edit(embeds=embeds)
                return msg
            except discord.NotFound:
                pass  # message was deleted — post a fresh one
            except Exception as exc:
                log.warning("Commands: failed to edit message: %s", exc)

        # Post fresh message and pin it
        msg = await channel.send(embeds=embeds)
        _set_cfg(self.db, "message_id", str(msg.id))
        try:
            await msg.pin()
        except discord.Forbidden:
            log.warning("Commands: no permission to pin in #%s", channel.name)
        return msg

    # ── Commands ───────────────────────────────────────────────────────────────

    @app_commands.command(
        name="set_command_channel",
        description="Set a channel where the bot posts and maintains the full command list.",
    )
    @app_commands.describe(channel="Channel to post the command list in")
    @app_commands.default_permissions(administrator=True)
    async def set_command_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        await interaction.response.defer(ephemeral=True)

        _set_cfg(self.db, "channel_id", str(channel.id))
        _set_cfg(self.db, "message_id", "")  # clear so a fresh post is made

        msg = await self._post_or_update(interaction.guild)
        if msg:
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"✅ Command list posted and pinned in {channel.mention}.",
                    color=var.COLOR_OK,
                ),
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"⚠️ Could not post to {channel.mention}. Check my **Send Messages** and **Pin Messages** permissions.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )

    @app_commands.command(
        name="see_admin_commands",
        description="Show all admin-only commands (visible only to you).",
    )
    @app_commands.default_permissions(administrator=True)
    async def see_admin_commands(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛡️ Admin Commands",
            description="These commands are hidden from the public command channel.",
            color=var.COLOR_ADMIN,
        )

        any_field = False
        for section_name, cog_name in _ADMIN_SECTIONS:
            cog  = self.bot.cogs.get(cog_name)
            if cog is None:
                embed.add_field(
                    name=f"{section_name} *(not loaded)*",
                    value="—",
                    inline=False,
                )
                continue
            cmds = cog.get_app_commands()
            if not cmds:
                continue
            any_field = True
            lines = [
                f"`/{cmd.name}` — {cmd.description}" if cmd.description else f"`/{cmd.name}`"
                for cmd in sorted(cmds, key=lambda c: c.name)
            ]
            embed.add_field(name=section_name, value="\n".join(lines), inline=False)

        if not any_field:
            embed.description = "*No admin commands found — cogs may not be loaded.*"

        embed.set_footer(text=f"🛡️ {var.SERVER_NAME}  •  Only visible to you")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="refresh_commands",
        description="Refresh the command list and server status in the command channel.",
    )
    @app_commands.default_permissions(administrator=True)
    async def refresh_commands(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        cid = _get_cfg(self.db, "channel_id")
        if not cid:
            await interaction.followup.send(
                embed=discord.Embed(
                    description="⚠️ No command channel set yet. Run `/set_command_channel` first.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        msg = await self._post_or_update(interaction.guild)
        if msg:
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"✅ Command list refreshed in <#{cid}>.",
                    color=var.COLOR_OK,
                ),
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"⚠️ The configured channel (<#{cid}>) no longer exists or I can't reach it.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )

        try:
            await _post_or_update_status_in_logs(interaction.guild, self.db)
        except Exception as exc:
            log.warning("Commands: status check on refresh failed: %s", exc)


async def setup(bot: commands.Bot):
    await bot.add_cog(CommandsCog(bot))
    log.info("✅ General/Commands cog loaded")
