import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime, timezone
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('iq_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")

_QUOTE_TRACKER_ROLE  = "quote tracker"
_GIF_WINDOW_SECONDS  = 300  # max gap between quote message and following gif message


def _require_quote_tracker(interaction: discord.Interaction) -> bool:
    if not isinstance(interaction.user, discord.Member):
        return False
    return any(r.name.lower() == _QUOTE_TRACKER_ROLE for r in interaction.user.roles)


def _is_gif(message: discord.Message) -> bool:
    if any(a.filename.lower().endswith('.gif') for a in message.attachments):
        return True
    for embed in message.embeds:
        if embed.type == 'gifv':
            return True
        url = (embed.url or '').lower()
        if 'tenor.com' in url or 'giphy.com' in url:
            return True
    content = (message.content or '').lower()
    return 'tenor.com' in content or 'giphy.com' in content


def _extract_gif_url(message: discord.Message) -> str:
    content = (message.content or '').strip()
    for word in content.split():
        if 'tenor.com' in word or 'giphy.com' in word:
            return word
    for embed in message.embeds:
        if embed.type == 'gifv' and embed.url:
            return embed.url
    for a in message.attachments:
        if a.filename.lower().endswith('.gif'):
            return a.proxy_url
    return ''


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


class ImportQuotesCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    async def cog_load(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id           TEXT NOT NULL,
                quoted_user_id     TEXT NOT NULL,
                quoted_user_name   TEXT NOT NULL,
                quoted_user_avatar TEXT,
                quoter_user_id     TEXT NOT NULL,
                quoter_user_name   TEXT NOT NULL,
                quote_text         TEXT NOT NULL,
                embed_message_id   TEXT,
                gif_url            TEXT,
                channel_id         TEXT NOT NULL,
                created_at         TEXT NOT NULL
            )
        """)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            msg = "❌ You need the **Quote Tracker** role to use this command."
        else:
            raise error
        if interaction.response.is_done():
            await interaction.followup.send(
                embed=discord.Embed(description=msg, color=var.COLOR_ERROR), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=discord.Embed(description=msg, color=var.COLOR_ERROR), ephemeral=True
            )

    # ── /quote_import ─────────────────────────────────────────────────────────

    @app_commands.command(
        name="quote_import",
        description="Scan a channel and import old quotes in 'quote - Name' format.",
    )
    @app_commands.describe(channel="Channel to scan for old quotes")
    @app_commands.check(_require_quote_tracker)
    async def quote_import(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        _spec.loader.exec_module(var)  # reload so NAME_MAP changes take effect without restart

        gid = str(interaction.guild_id)
        imported      = 0
        updated       = 0
        skipped       = 0
        duplicates    = 0
        unknown_names: set[str] = set()

        # Fetch full history oldest-first so we can look ahead for the gif message
        messages: list[discord.Message] = []
        async for msg in channel.history(limit=None, oldest_first=True):
            messages.append(msg)

        i = 0
        while i < len(messages):
            msg     = messages[i]
            content = (msg.content or '').strip()

            # Must contain ' - ' and not be a pure gif/link message
            sep = content.rfind(' - ')
            if sep == -1:
                i += 1
                continue

            quote_text = content[:sep].strip().strip('"').strip("'")
            raw_name   = content[sep + 3:].strip()

            # Skip if name looks like a URL or is empty
            if not quote_text or not raw_name or raw_name.startswith('http'):
                i += 1
                continue

            # GIF: check current message first, then the immediately following message
            gif_url    = _extract_gif_url(msg)
            skip_next  = False

            if not gif_url and i + 1 < len(messages):
                nxt = messages[i + 1]
                gap = (_utc(nxt.created_at) - _utc(msg.created_at)).total_seconds()
                if _is_gif(nxt) and gap <= _GIF_WINDOW_SECONDS:
                    gif_url   = _extract_gif_url(nxt)
                    skip_next = True

            # Resolve quoted user via NAME_MAP
            name_entry = var.NAME_MAP.get(raw_name)
            if name_entry:
                quoted_uid, quoted_uname = name_entry
            else:
                unknown_names.add(raw_name)
                quoted_uid   = "0"
                quoted_uname = raw_name

            # Submitter = whoever posted the original message
            quoter_uid   = str(msg.author.id)
            quoter_uname = msg.author.display_name

            # Use the original message timestamp
            date_str = msg.created_at.isoformat()

            existing = self.db.execute(
                "SELECT id, quoted_user_id FROM quotes WHERE guild_id = ? AND quote_text = ? AND quoted_user_name = ?",
                (gid, quote_text, quoted_uname),
            )
            if existing:
                existing_id, existing_uid = existing[0]
                if existing_uid == "0" and quoted_uid != "0":
                    self.db.execute(
                        "UPDATE quotes SET quoted_user_id = ? WHERE id = ?",
                        (quoted_uid, existing_id),
                    )
                    updated += 1
                else:
                    duplicates += 1
                i += 2 if skip_next else 1
                continue

            try:
                self.db.execute(
                    """INSERT INTO quotes
                           (guild_id, quoted_user_id, quoted_user_name, quoted_user_avatar,
                            quoter_user_id, quoter_user_name, quote_text,
                            embed_message_id, gif_url, channel_id, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        gid,
                        quoted_uid,
                        quoted_uname,
                        None,
                        quoter_uid,
                        quoter_uname,
                        quote_text,
                        str(msg.id),
                        gif_url,
                        str(channel.id),
                        date_str,
                    ),
                )
                imported += 1
            except Exception as e:
                log.error("ImportQuotesCog: failed to insert quote: %s", e)
                skipped += 1

            i += 2 if skip_next else 1

        out = [f"✅ Imported **{imported}** quote(s) from {channel.mention}."]
        if updated:
            out.append(f"🔄 Updated **{updated}** quote(s) that had an unresolved name — user ID now set.")
        if duplicates:
            out.append(f"⏭️ Skipped **{duplicates}** duplicate(s) already in the database.")
        if skipped:
            out.append(f"⚠️ **{skipped}** entr{'ies' if skipped != 1 else 'y'} failed to insert.")
        if unknown_names:
            names_fmt = ", ".join(f"`{n}`" for n in sorted(unknown_names))
            out.append(
                f"❓ Names not found in `NAME_MAP` (stored as-is with ID `0`): {names_fmt}\n"
                f"Add them to `Quotes/import_quotes/variables.py` and re-import — duplicates are skipped automatically."
            )

        color = var.COLOR_WIN if imported else var.COLOR_ERROR
        await interaction.followup.send(
            embed=discord.Embed(description="\n".join(out), color=color),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ImportQuotesCog(bot))
    log.info("✅ ImportQuotes cog loaded")
