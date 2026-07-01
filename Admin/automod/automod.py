import re
import time
import logging
from collections import defaultdict, deque
from datetime import timedelta
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('automod_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

_cfg_spec = _ilu.spec_from_file_location('automod_config', Path(__file__).parent / 'automod_config.py')
_cfg_mod  = _ilu.module_from_spec(_cfg_spec)
_cfg_spec.loader.exec_module(_cfg_mod)
AutomodConfig = _cfg_mod.AutomodConfig

try:
    from Admin.panel.log_config import is_log_enabled as _is_log_enabled
except ImportError:
    try:
        from panel.log_config import is_log_enabled as _is_log_enabled
    except ImportError:
        def _is_log_enabled(category: str) -> bool:
            return True

log = logging.getLogger("launcher")

_URL_RE = re.compile(
    r'(?:https?://|www\.)\S+|discord\.gg/\S+',
    re.IGNORECASE,
)

# In-memory trackers (reset on restart)
_spam_buckets: dict[int, dict[int, deque]] = defaultdict(lambda: defaultdict(deque))
_violations:   dict[int, dict[int, int]]   = defaultdict(lambda: defaultdict(int))


# ============================================================================
# FILTER FUNCTIONS  — each returns a violation reason string or None
# ============================================================================

def _check_bad_words(content: str, cfg: AutomodConfig) -> str | None:
    if not cfg.bad_words_enabled():
        return None
    low = content.lower()
    for word in cfg.bad_words():
        if word in low:
            return f"Banned word detected: `{word}`"
    return None


def _check_spam(guild_id: int, user_id: int, cfg: AutomodConfig) -> str | None:
    sp = cfg.spam()
    if not cfg.spam_enabled():
        return None
    max_msgs = sp.get("max_messages",   var.DEFAULT_SPAM_MESSAGES)
    window   = sp.get("window_seconds", var.DEFAULT_SPAM_WINDOW)

    bucket = _spam_buckets[guild_id][user_id]
    now    = time.monotonic()
    while bucket and bucket[0] < now - window:
        bucket.popleft()
    bucket.append(now)

    if len(bucket) > max_msgs:
        return f"Spam — {len(bucket)} messages in {window}s"
    return None


def _check_caps(content: str, cfg: AutomodConfig) -> str | None:
    caps_cfg = cfg.caps()
    if not cfg.caps_enabled():
        return None
    min_len = caps_cfg.get("min_length", var.DEFAULT_CAPS_MIN_LEN)
    percent = caps_cfg.get("percent",    var.DEFAULT_CAPS_PERCENT)
    letters = [c for c in content if c.isalpha()]
    if len(letters) < min_len:
        return None
    ratio = sum(1 for c in letters if c.isupper()) / len(letters) * 100
    if ratio >= percent:
        return f"Excessive caps ({int(ratio)}%)"
    return None


def _check_mentions(message: discord.Message, cfg: AutomodConfig) -> str | None:
    if not cfg.mentions_enabled():
        return None
    max_count = cfg.mentions().get("max_count", var.DEFAULT_MAX_MENTIONS)
    total     = len(message.mentions) + len(message.role_mentions)
    if total > max_count:
        return f"Too many mentions ({total})"
    return None


def _check_links(content: str, cfg: AutomodConfig) -> str | None:
    if not cfg.links_enabled():
        return None
    matches  = _URL_RE.findall(content)
    if not matches:
        return None
    whitelist = [d.lower().lstrip("www.") for d in cfg.link_whitelist()]
    for url in matches:
        url_low = url.lower().lstrip("https://").lstrip("http://").lstrip("www.").split("/")[0]
        if not any(url_low == d or url_low.endswith("." + d) for d in whitelist):
            return f"Blocked link: `{url_low}`"
    return None


# ============================================================================
# LOG EMBED
# ============================================================================

def _log_embed(
    member:   discord.Member,
    channel:  discord.TextChannel,
    reason:   str,
    content:  str,
    action:   str,
    strike:   int,
    threshold: int,
) -> discord.Embed:
    embed = discord.Embed(
        title="🛡️ AutoMod Action",
        color=var.COLOR_STRIKE,
    )
    embed.add_field(name="User",     value=f"{member.mention} `{member.id}`",  inline=True)
    embed.add_field(name="Channel",  value=channel.mention,                    inline=True)
    embed.add_field(name="Reason",   value=reason,                             inline=False)
    embed.add_field(name="Action",   value=action,                             inline=True)
    embed.add_field(name="Strikes",  value=f"{strike} / {threshold}",         inline=True)
    if content:
        preview = content[:300] + ("…" if len(content) > 300 else "")
        embed.add_field(name="Message", value=f"```{preview}```", inline=False)
    embed.timestamp = discord.utils.utcnow()
    embed.set_footer(text=var.SERVER_NAME)
    return embed


# ============================================================================
# COG
# ============================================================================

class AutomodCog(commands.Cog):

    # Commands live under /automod <subcommand>
    automod = app_commands.Group(
        name="automod",
        description="AutoMod configuration (admin only)",
        default_permissions=discord.Permissions(administrator=True),
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = AutomodConfig()

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        cid = self.cfg.log_channel_id
        if cid:
            ch = guild.get_channel(cid)
            if ch:
                return ch
        return discord.utils.get(guild.text_channels, name=var.DEFAULT_LOG_CHANNEL)

    def _is_exempt(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator:
            return True
        exempt_ids = set(self.cfg.whitelist_role_ids())
        return bool({r.id for r in member.roles} & exempt_ids)

    async def _handle_violation(
        self,
        message: discord.Message,
        reason:  str,
    ):
        guild  = message.guild
        member = message.author
        gid    = guild.id
        uid    = member.id

        # Delete the offending message
        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

        # Increment strike counter
        _violations[gid][uid] += 1
        strike    = _violations[gid][uid]
        threshold = self.cfg.warn_threshold()

        # Warn in channel (auto-deletes quickly via embed)
        action = "Message deleted"
        timed_out = False
        if strike >= threshold:
            mins = self.cfg.timeout_minutes()
            try:
                until = discord.utils.utcnow() + timedelta(minutes=mins)
                await member.timeout(until, reason=f"AutoMod: {reason}")
                action    = f"Message deleted + {mins}min timeout"
                timed_out = True
                _violations[gid][uid] = 0  # reset after timeout
            except discord.Forbidden:
                action = "Message deleted (timeout failed — missing permission)"

        # Warn in the channel
        try:
            warn_msg = await message.channel.send(
                embed=discord.Embed(
                    description=(
                        f"⚠️ {member.mention} — **{reason}**\n"
                        + (f"You have been timed out for {self.cfg.timeout_minutes()} minutes." if timed_out
                           else f"Strike **{strike}/{threshold}** before timeout.")
                    ),
                    color=var.COLOR_WARN,
                ),
                delete_after=8,
            )
        except discord.Forbidden:
            pass

        # Log to mod-logs
        log_ch = await self._get_log_channel(guild) if _is_log_enabled("automod") else None
        if log_ch:
            try:
                await log_ch.send(embed=_log_embed(
                    member    = member,
                    channel   = message.channel,
                    reason    = reason,
                    content   = message.content,
                    action    = action,
                    strike    = strike,
                    threshold = threshold,
                ))
            except discord.Forbidden:
                pass

    # ── on_message listener ───────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        if not self.cfg.enabled:
            return
        if not isinstance(message.author, discord.Member):
            return
        if self._is_exempt(message.author):
            return

        gid = message.guild.id
        uid = message.author.id

        for check, args in [
            (_check_bad_words, (message.content, self.cfg)),
            (_check_spam,      (gid, uid, self.cfg)),
            (_check_caps,      (message.content, self.cfg)),
            (_check_mentions,  (message, self.cfg)),
            (_check_links,     (message.content, self.cfg)),
        ]:
            reason = check(*args)
            if reason:
                await self._handle_violation(message, reason)
                return  # one violation per message

    # ── /automod toggle ───────────────────────────────────────────────────────

    @automod.command(name="toggle", description="Enable or disable AutoMod entirely.")
    @app_commands.describe(enabled="Turn AutoMod on or off")
    async def am_toggle(self, interaction: discord.Interaction, enabled: bool):
        self.cfg.set_enabled(enabled)
        state = "**enabled** ✅" if enabled else "**disabled** ❌"
        await interaction.response.send_message(
            embed=discord.Embed(description=f"AutoMod is now {state}.", color=var.COLOR_OK),
            ephemeral=True,
        )

    # ── /automod settings ─────────────────────────────────────────────────────

    @automod.command(name="settings", description="View current AutoMod configuration.")
    async def am_settings(self, interaction: discord.Interaction):
        cfg = self.cfg

        def _yn(val): return "✅ On" if val else "❌ Off"

        sp = cfg.spam()
        ca = cfg.caps()
        me = cfg.mentions()
        lk = cfg.links()

        log_ch = f"<#{cfg.log_channel_id}>" if cfg.log_channel_id else f"*(default: #{var.DEFAULT_LOG_CHANNEL})*"
        exempt = ", ".join(f"<@&{r}>" for r in cfg.whitelist_role_ids()) or "*(none)*"
        words  = cfg.bad_words()
        words_val = f"{len(words)} word{'s' if len(words) != 1 else ''}" + (
            f": {', '.join(f'`{w}`' for w in words[:10])}" + ("…" if len(words) > 10 else "")
            if words else " *(none set)*"
        )
        whitelist_domains = ", ".join(f"`{d}`" for d in lk.get("whitelisted_domains", [])) or "*(none)*"

        embed = discord.Embed(title="🛡️ AutoMod Settings", color=var.COLOR_INFO)
        embed.add_field(name="Status",         value=_yn(cfg.enabled),                                   inline=True)
        embed.add_field(name="Log Channel",    value=log_ch,                                             inline=True)
        embed.add_field(name="Exempt Roles",   value=exempt,                                             inline=False)
        embed.add_field(
            name="🚫 Bad Words",
            value=f"{_yn(cfg.bad_words_enabled())}\n{words_val}",
            inline=False,
        )
        embed.add_field(
            name="📨 Spam",
            value=(
                f"{_yn(cfg.spam_enabled())}\n"
                f"Max **{sp.get('max_messages', var.DEFAULT_SPAM_MESSAGES)}** msgs / "
                f"**{sp.get('window_seconds', var.DEFAULT_SPAM_WINDOW)}**s"
            ),
            inline=True,
        )
        embed.add_field(
            name="🔠 Caps",
            value=(
                f"{_yn(cfg.caps_enabled())}\n"
                f"≥ **{ca.get('percent', var.DEFAULT_CAPS_PERCENT)}%** caps, "
                f"min **{ca.get('min_length', var.DEFAULT_CAPS_MIN_LEN)}** letters"
            ),
            inline=True,
        )
        embed.add_field(
            name="📢 Mentions",
            value=(
                f"{_yn(cfg.mentions_enabled())}\n"
                f"Max **{me.get('max_count', var.DEFAULT_MAX_MENTIONS)}** per message"
            ),
            inline=True,
        )
        embed.add_field(
            name="🔗 Links",
            value=f"{_yn(cfg.links_enabled())}\nWhitelist: {whitelist_domains}",
            inline=False,
        )
        embed.add_field(
            name="⚡ Actions",
            value=(
                f"Timeout after **{cfg.warn_threshold()}** strikes → "
                f"**{cfg.timeout_minutes()}** min"
            ),
            inline=False,
        )
        embed.set_footer(text=var.SERVER_NAME)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /automod log_channel ──────────────────────────────────────────────────

    @automod.command(name="log_channel", description="Set the channel where AutoMod logs violations.")
    @app_commands.describe(channel="Channel to post violation logs in")
    async def am_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.cfg.set_log_channel(channel.id, channel.name)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Violation logs will be posted in {channel.mention}.",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )

    # ── /automod badword_add ──────────────────────────────────────────────────

    @automod.command(name="badword_add", description="Add a word to the banned words list.")
    @app_commands.describe(word="Word to ban (case-insensitive, partial match)")
    async def am_badword_add(self, interaction: discord.Interaction, word: str):
        self.cfg.add_bad_word(word)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ `{word.lower().strip()}` added to banned words.",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )

    # ── /automod badword_remove ───────────────────────────────────────────────

    @automod.command(name="badword_remove", description="Remove a word from the banned words list.")
    @app_commands.describe(word="Word to remove")
    async def am_badword_remove(self, interaction: discord.Interaction, word: str):
        removed = self.cfg.remove_bad_word(word)
        if removed:
            desc  = f"✅ `{word.lower().strip()}` removed from banned words."
            color = var.COLOR_OK
        else:
            desc  = f"⚠️ `{word.lower().strip()}` was not in the list."
            color = var.COLOR_WARN
        await interaction.response.send_message(
            embed=discord.Embed(description=desc, color=color),
            ephemeral=True,
        )

    # ── /automod badword_list ─────────────────────────────────────────────────

    @automod.command(name="badword_list", description="List all currently banned words.")
    async def am_badword_list(self, interaction: discord.Interaction):
        words = self.cfg.bad_words()
        if not words:
            desc = "*(no banned words configured)*"
        else:
            desc = "  ".join(f"`{w}`" for w in words)
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"🚫 Banned Words ({len(words)})",
                description=desc,
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )

    # ── /automod spam_threshold ───────────────────────────────────────────────

    @automod.command(name="spam_threshold", description="Set how many messages in a window counts as spam.")
    @app_commands.describe(
        messages="Max messages allowed in the window (min 2)",
        seconds="Time window in seconds (min 2)",
    )
    async def am_spam(self, interaction: discord.Interaction, messages: int, seconds: int):
        if messages < 2 or seconds < 2:
            return await interaction.response.send_message(
                embed=discord.Embed(description="Both values must be at least 2.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
        self.cfg.set_spam(messages, seconds)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Spam filter: max **{messages}** messages per **{seconds}s**.",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )

    # ── /automod caps_threshold ───────────────────────────────────────────────

    @automod.command(name="caps_threshold", description="Set the % of uppercase letters that triggers caps filter (0 to disable).")
    @app_commands.describe(
        percent="Uppercase % threshold (0 = disable, max 100)",
        min_length="Minimum message length to check (default 15)",
    )
    async def am_caps(self, interaction: discord.Interaction, percent: int, min_length: int = 15):
        if not 0 <= percent <= 100:
            return await interaction.response.send_message(
                embed=discord.Embed(description="Percent must be 0–100.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
        self.cfg.set_caps(percent, min_length)
        if percent == 0:
            desc = "✅ Caps filter **disabled**."
        else:
            desc = f"✅ Caps filter: ≥ **{percent}%** uppercase on messages ≥ **{min_length}** letters."
        await interaction.response.send_message(
            embed=discord.Embed(description=desc, color=var.COLOR_OK),
            ephemeral=True,
        )

    # ── /automod max_mentions ─────────────────────────────────────────────────

    @automod.command(name="max_mentions", description="Set the max @mentions per message (0 to disable).")
    @app_commands.describe(count="Max allowed mentions per message (0 = disable)")
    async def am_mentions(self, interaction: discord.Interaction, count: int):
        if count < 0:
            return await interaction.response.send_message(
                embed=discord.Embed(description="Count cannot be negative.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
        self.cfg.set_max_mentions(count)
        desc = "✅ Mention filter **disabled**." if count == 0 else f"✅ Max **{count}** mentions per message."
        await interaction.response.send_message(
            embed=discord.Embed(description=desc, color=var.COLOR_OK),
            ephemeral=True,
        )

    # ── /automod links_toggle ─────────────────────────────────────────────────

    @automod.command(name="links_toggle", description="Enable or disable the link filter.")
    @app_commands.describe(enabled="Turn link filter on or off")
    async def am_links_toggle(self, interaction: discord.Interaction, enabled: bool):
        self.cfg.set_links_enabled(enabled)
        state = "**enabled** ✅" if enabled else "**disabled** ❌"
        await interaction.response.send_message(
            embed=discord.Embed(description=f"Link filter is now {state}.", color=var.COLOR_OK),
            ephemeral=True,
        )

    # ── /automod links_whitelist ──────────────────────────────────────────────

    @automod.command(name="links_whitelist", description="Add or remove a domain from the link whitelist.")
    @app_commands.describe(
        domain="Domain to whitelist (e.g. youtube.com)",
        action="Add or remove",
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
    ])
    async def am_links_whitelist(self, interaction: discord.Interaction, domain: str, action: str):
        if action == "add":
            added = self.cfg.add_link_whitelist(domain)
            desc  = f"✅ `{domain}` added to link whitelist." if added else f"⚠️ `{domain}` already whitelisted."
            color = var.COLOR_OK if added else var.COLOR_WARN
        else:
            removed = self.cfg.remove_link_whitelist(domain)
            desc    = f"✅ `{domain}` removed from whitelist." if removed else f"⚠️ `{domain}` was not in the whitelist."
            color   = var.COLOR_OK if removed else var.COLOR_WARN
        await interaction.response.send_message(
            embed=discord.Embed(description=desc, color=color),
            ephemeral=True,
        )

    # ── /automod warn_threshold ───────────────────────────────────────────────

    @automod.command(name="warn_threshold", description="Set how many strikes before a user is timed out.")
    @app_commands.describe(count="Violations before auto-timeout (min 1)")
    async def am_warn_threshold(self, interaction: discord.Interaction, count: int):
        if count < 1:
            return await interaction.response.send_message(
                embed=discord.Embed(description="Must be at least 1.", color=var.COLOR_ERROR),
                ephemeral=True,
            )
        self.cfg.set_warn_threshold(count)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Users will be timed out after **{count}** strike{'s' if count != 1 else ''}.",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )

    # ── /automod timeout_duration ─────────────────────────────────────────────

    @automod.command(name="timeout_duration", description="Set how long (in minutes) auto-timeouts last.")
    @app_commands.describe(minutes="Timeout duration in minutes (min 1, max 40320)")
    async def am_timeout_duration(self, interaction: discord.Interaction, minutes: int):
        if not 1 <= minutes <= 40320:
            return await interaction.response.send_message(
                embed=discord.Embed(description="Must be between 1 and 40320 minutes (28 days).", color=var.COLOR_ERROR),
                ephemeral=True,
            )
        self.cfg.set_timeout_minutes(minutes)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Auto-timeout duration set to **{minutes} minute{'s' if minutes != 1 else ''}**.",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )

    # ── /automod whitelist_role ───────────────────────────────────────────────

    @automod.command(name="whitelist_role", description="Add or remove a role that is exempt from AutoMod.")
    @app_commands.describe(
        role="Role to exempt",
        action="Add or remove exemption",
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
    ])
    async def am_whitelist_role(self, interaction: discord.Interaction, role: discord.Role, action: str):
        if action == "add":
            added = self.cfg.add_whitelist_role(role.id)
            desc  = f"✅ {role.mention} is now exempt from AutoMod." if added else f"⚠️ {role.mention} was already exempt."
            color = var.COLOR_OK if added else var.COLOR_WARN
        else:
            removed = self.cfg.remove_whitelist_role(role.id)
            desc    = f"✅ {role.mention} is no longer exempt." if removed else f"⚠️ {role.mention} was not on the whitelist."
            color   = var.COLOR_OK if removed else var.COLOR_WARN
        await interaction.response.send_message(
            embed=discord.Embed(description=desc, color=color),
            ephemeral=True,
        )

    # ── /automod reset_strikes ────────────────────────────────────────────────

    @automod.command(name="reset_strikes", description="Reset the strike count for a specific user.")
    @app_commands.describe(member="Member whose strikes to clear")
    async def am_reset_strikes(self, interaction: discord.Interaction, member: discord.Member):
        _violations[interaction.guild_id][member.id] = 0
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Strike count for {member.mention} has been reset.",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AutomodCog(bot))
    log.info("✅ Admin/Automod cog loaded")
