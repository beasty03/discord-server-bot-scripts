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

_QUOTE_TRACKER_ROLE = "quote tracker"
_GIF_WINDOW_SECONDS = 300


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


def _build_quote_embed(q: dict) -> discord.Embed:
    action = "🔄 updated" if q["is_update"] else "✅ imported"
    e = discord.Embed(
        description=f'{action} **"{q["quote_text"]}"** — {q["quoted_uname"]}',
        color=var.COLOR_WIN,
    )
    if q.get("gif_url"):
        e.set_image(url=q["gif_url"])
    return e


class _ConfirmView(discord.ui.View):

    def __init__(self, cog: "ImportQuotesCog", gid: str, pending: list[dict],
                 unknown_names: set[str], channel_mention: str):
        super().__init__(timeout=120)
        self.cog             = cog
        self.gid             = gid
        self.pending         = pending
        self.unknown_names   = unknown_names
        self.channel_mention = channel_mention

    def _disable(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="Import", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._disable()
        await interaction.response.edit_message(view=self)

        imported = 0
        updated  = 0
        skipped  = 0
        embeds: list[discord.Embed] = []

        for q in self.pending:
            try:
                if q["is_update"]:
                    self.cog.db.execute(
                        "UPDATE quotes SET quoted_user_id = ? WHERE id = ?",
                        (q["quoted_uid"], q["existing_id"]),
                    )
                    updated += 1
                else:
                    self.cog.db.execute(
                        """INSERT INTO quotes
                               (guild_id, quoted_user_id, quoted_user_name, quoted_user_avatar,
                                quoter_user_id, quoter_user_name, quote_text,
                                embed_message_id, gif_url, channel_id, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            self.gid,
                            q["quoted_uid"],
                            q["quoted_uname"],
                            None,
                            q["quoter_uid"],
                            q["quoter_uname"],
                            q["quote_text"],
                            q["msg_id"],
                            q["gif_url"],
                            q["channel_id"],
                            q["date_str"],
                        ),
                    )
                    imported += 1
                embeds.append(_build_quote_embed(q))
            except Exception as e:
                log.error("ImportQuotesCog: failed to insert/update quote: %s", e)
                skipped += 1

        out = []
        if imported:
            out.append(f"✅ Imported **{imported}** quote(s) from {self.channel_mention}.")
        if updated:
            out.append(f"🔄 Updated **{updated}** quote(s) with a now-resolved user ID.")
        if skipped:
            out.append(f"⚠️ **{skipped}** failed to insert.")
        if self.unknown_names:
            names_fmt = ", ".join(f"`{n}`" for n in sorted(self.unknown_names))
            out.append(
                f"❓ Names not in `NAME_MAP` (stored with ID `0`): {names_fmt}\n"
                f"Add them and re-import — duplicates are skipped automatically."
            )

        summary = "\n".join(out) if out else "Nothing was imported."

        # Send summary + one embed per quote, batched in groups of 10
        for batch_start in range(0, max(len(embeds), 1), 10):
            batch = embeds[batch_start:batch_start + 10]
            if batch_start == 0:
                await interaction.followup.send(summary, embeds=batch, ephemeral=True)
            else:
                await interaction.followup.send(embeds=batch, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._disable()
        await interaction.response.edit_message(
            embed=discord.Embed(description="❌ Import cancelled.", color=var.COLOR_ERROR),
            view=self,
        )


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

    @app_commands.command(
        name="quote_import",
        description="Scan a channel and import old quotes in 'quote - Name' format.",
    )
    @app_commands.describe(channel="Channel to scan for old quotes")
    @app_commands.check(_require_quote_tracker)
    async def quote_import(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        _spec.loader.exec_module(var)  # reload so NAME_MAP changes take effect without restart

        gid           = str(interaction.guild_id)
        pending: list[dict] = []
        duplicates    = 0
        unknown_names: set[str] = set()

        messages: list[discord.Message] = []
        async for msg in channel.history(limit=None, oldest_first=True):
            messages.append(msg)

        i = 0
        while i < len(messages):
            msg     = messages[i]
            content = (msg.content or '').strip()

            sep = content.rfind(' - ')
            if sep != -1:
                name_start = sep + 3
            else:
                sep = content.rfind(' -')
                if sep == -1:
                    i += 1
                    continue
                name_start = sep + 2

            quote_text = content[:sep].strip().strip('"').strip("'")
            raw_name   = content[name_start:].strip()

            if not quote_text or not raw_name or raw_name.startswith('http'):
                i += 1
                continue

            gif_url   = _extract_gif_url(msg)
            skip_next = False

            if not gif_url and i + 1 < len(messages):
                nxt = messages[i + 1]
                gap = (_utc(nxt.created_at) - _utc(msg.created_at)).total_seconds()
                if _is_gif(nxt) and gap <= _GIF_WINDOW_SECONDS:
                    gif_url   = _extract_gif_url(nxt)
                    skip_next = True

            name_entry = var.NAME_MAP.get(raw_name)
            if name_entry:
                quoted_uid, quoted_uname = name_entry
            else:
                unknown_names.add(raw_name)
                quoted_uid   = "0"
                quoted_uname = raw_name

            quoter_uid   = str(msg.author.id)
            quoter_uname = msg.author.display_name
            date_str     = msg.created_at.isoformat()

            existing = self.db.execute(
                "SELECT id, quoted_user_id FROM quotes WHERE guild_id = ? AND quote_text = ? AND quoted_user_name = ?",
                (gid, quote_text, quoted_uname),
            )
            if existing:
                existing_id, existing_uid = existing[0]
                if existing_uid == "0" and quoted_uid != "0":
                    pending.append({
                        "quote_text":  quote_text,
                        "quoted_uid":  quoted_uid,
                        "quoted_uname": quoted_uname,
                        "quoter_uid":  quoter_uid,
                        "quoter_uname": quoter_uname,
                        "date_str":    date_str,
                        "msg_id":      str(msg.id),
                        "gif_url":     gif_url,
                        "channel_id":  str(channel.id),
                        "is_update":   True,
                        "existing_id": existing_id,
                    })
                else:
                    duplicates += 1
                i += 2 if skip_next else 1
                continue

            pending.append({
                "quote_text":  quote_text,
                "quoted_uid":  quoted_uid,
                "quoted_uname": quoted_uname,
                "quoter_uid":  quoter_uid,
                "quoter_uname": quoter_uname,
                "date_str":    date_str,
                "msg_id":      str(msg.id),
                "gif_url":     gif_url,
                "channel_id":  str(channel.id),
                "is_update":   False,
                "existing_id": None,
            })

            i += 2 if skip_next else 1

        if not pending:
            msg_text = "No new quotes found in that channel."
            if duplicates:
                msg_text += f"\n⏭️ **{duplicates}** already in the database."
            await interaction.followup.send(
                embed=discord.Embed(description=msg_text, color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        # Build preview
        new_count    = sum(1 for q in pending if not q["is_update"])
        update_count = sum(1 for q in pending if q["is_update"])

        lines = []
        if duplicates:
            lines.append(f"⏭️ **{duplicates}** already in the database (will be skipped)")
        if update_count:
            lines.append(f"🔄 **{update_count}** existing quote(s) with unresolved name (user ID will be updated)")
        if unknown_names:
            names_fmt = ", ".join(f"`{n}`" for n in sorted(unknown_names))
            lines.append(f"❓ Unknown names (stored with ID `0`): {names_fmt}")

        embed = discord.Embed(
            title=f"Found {new_count} new quote(s) to import from #{channel.name}",
            description="\n".join(lines) if lines else None,
            color=var.COLOR_WIN,
        )

        view = _ConfirmView(self, gid, pending, unknown_names, channel.mention)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ImportQuotesCog(bot))
    log.info("✅ ImportQuotes cog loaded")
