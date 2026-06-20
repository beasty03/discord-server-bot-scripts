import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('q_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")
_SETTINGS_FILE = Path(__file__).parent / 'quotes_settings.json'


def _load_settings() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            return json.loads(_SETTINGS_FILE.read_text('utf-8'))
        except Exception:
            pass
    return {}


def _save_settings(data: dict):
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2), 'utf-8')


def _get_period_filter() -> tuple[str, list]:
    settings = _load_settings()
    from_date = settings.get('period_from')
    to_date   = settings.get('period_to')
    clauses, params = [], []
    if from_date:
        clauses.append("created_at >= ?")
        params.append(from_date)
    if to_date:
        clauses.append("created_at <= ?")
        params.append(to_date + "T23:59:59")
    return (" AND " + " AND ".join(clauses)) if clauses else "", params


def _period_label() -> str:
    settings = _load_settings()
    from_date = settings.get('period_from')
    to_date   = settings.get('period_to')
    if from_date and to_date:
        return f"{from_date} → {to_date}"
    if from_date:
        return f"from {from_date}"
    if to_date:
        return f"until {to_date}"
    return ""


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
    """Pull a stable gif URL from a message for DB storage."""
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


_QUOTE_TRACKER_ROLE = "quote tracker"


def _require_quote_tracker(interaction: discord.Interaction) -> bool:
    if not isinstance(interaction.user, discord.Member):
        return False
    return any(r.name.lower() == _QUOTE_TRACKER_ROLE for r in interaction.user.roles)


class QuotesCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()
        # guild_id -> pending quote data (before gif is submitted)
        self._pending: dict[str, dict] = {}

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "❌ You need administrator permissions to use this command."
        elif isinstance(error, app_commands.CheckFailure):
            msg = f"❌ You need the **Quote Tracker** role to use this command."
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

    def _get_channel(self) -> discord.TextChannel | None:
        cid = _load_settings().get('quote_channel_id')
        return self.bot.get_channel(int(cid)) if cid else None

    # ── Gif timeout task ──────────────────────────────────────────────────────

    async def _gif_timeout_task(self, gid: str, embed_msg: discord.Message,
                                channel: discord.TextChannel, uid: int):
        try:
            # Stage 1: public reminder after GIF_REMINDER_DELAY seconds
            await asyncio.sleep(var.GIF_REMINDER_DELAY)
            if gid not in self._pending:
                return

            try:
                reminder = await channel.send(
                    f"📸 <@{uid}> ⬆️ Don't forget to drop a GIF here to complete your quote!"
                )
                self._pending[gid]["reminder_msg"] = reminder
            except Exception:
                reminder = None

            # Stage 2: cancel + DM after remaining time
            remaining = max(0, var.GIF_TIMEOUT - var.GIF_REMINDER_DELAY)
            await asyncio.sleep(remaining)
            if gid not in self._pending:
                return

            pending = self._pending.pop(gid)

            for msg in (embed_msg, pending.get("reminder_msg")):
                if msg:
                    try:
                        await msg.delete()
                    except Exception:
                        pass

            dm_embed = discord.Embed(
                title="⏰ Quote Cancelled — No GIF Dropped",
                description=(
                    f"Your quote in **{channel.guild.name}** was removed because no GIF was "
                    f"dropped within {var.GIF_TIMEOUT // 60} minutes.\n\n"
                    f"**Quote info to resubmit:**\n"
                    f"> {pending['text']}\n"
                    f"**— {pending['quoted_uname']}**\n\n"
                    f"Use `/quote` with the text above and drop a GIF right after!"
                ),
                color=var.COLOR_ERROR,
            )
            dm_sent = False
            try:
                user = await self.bot.fetch_user(uid)
                await user.send(embed=dm_embed)
                dm_sent = True
            except discord.Forbidden:
                pass
            except Exception:
                pass

            if not dm_sent:
                try:
                    await channel.send(
                        f"<@{uid}> Your quote was removed (no GIF dropped in time). "
                        f"Enable DMs from server members so I can send you the quote info, "
                        f"or use `/quote` again.",
                        delete_after=60,
                    )
                except Exception:
                    pass

        except asyncio.CancelledError:
            pass

    # ── Gif listener ──────────────────────────────────────────────────────────

    async def _handle_gif_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        gid = str(message.guild.id)
        pending = self._pending.get(gid)
        if pending is None:
            return
        if message.author.id != pending["uid"] or message.channel.id != pending["cid"]:
            return
        if not _is_gif(message):
            return

        # Cancel the timeout task and clean up the public reminder
        if pending.get("task"):
            pending["task"].cancel()
        if pending.get("reminder_msg"):
            try:
                await pending["reminder_msg"].delete()
            except Exception:
                pass

        del self._pending[gid]

        gif_url = _extract_gif_url(message)
        ch = message.channel

        # Re-post gif cleanly under the quote embed
        sent_gif_url = gif_url
        try:
            if message.attachments:
                gif_files = [
                    await a.to_file()
                    for a in message.attachments
                    if a.filename.lower().endswith('.gif')
                ]
                if gif_files:
                    sent = await ch.send(files=gif_files)
                    if sent.attachments:
                        sent_gif_url = sent.attachments[0].proxy_url
            else:
                content = (message.content or '').strip()
                if content:
                    await ch.send(content)
        except Exception:
            pass

        try:
            await message.delete()
        except Exception:
            pass

        # Save to DB
        try:
            self.db.execute(
                """INSERT INTO quotes
                       (guild_id, quoted_user_id, quoted_user_name, quoted_user_avatar,
                        quoter_user_id, quoter_user_name, quote_text,
                        embed_message_id, gif_url, channel_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    gid,
                    str(pending["quoted_uid"]),
                    pending["quoted_uname"],
                    pending["quoted_avatar"],
                    str(pending["uid"]),
                    pending["uname"],
                    pending["text"],
                    str(pending["mid"]),
                    sent_gif_url,
                    str(pending["cid"]),
                    datetime.utcnow().isoformat(),
                ),
            )
        except Exception as e:
            log.error("QuotesCog: failed to save quote to DB: %s", e)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self._handle_gif_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self, _before: discord.Message, after: discord.Message):
        # Discord edits messages to inject Tenor/Giphy embeds — catch that here
        await self._handle_gif_message(after)

    # ── /quote ────────────────────────────────────────────────────────────────

    @app_commands.command(name="quote", description="Post a quote from someone to the quotes channel.")
    @app_commands.describe(
        user="The person being quoted",
        quote="What they said",
    )
    async def quote(self, interaction: discord.Interaction, user: discord.Member, quote: str):
        gid = str(interaction.guild_id)

        pending = self._pending.get(gid)
        if pending:
            ch = self.bot.get_channel(pending["cid"])
            ch_mention = ch.mention if ch else "the quotes channel"
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"⏳ <@{pending['uid']}> still needs to drop a gif in {ch_mention} first!",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        channel = self._get_channel()
        if channel is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ No quotes channel set. Ask an admin to use `/set_quote_channel` first.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            description=f'> {quote}\n\n**— {user.display_name}**',
            color=var.COLOR_QUOTE,
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"Quoted by {interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()

        msg = await channel.send(embed=embed)

        self._pending[gid] = {
            "uid":           interaction.user.id,
            "uname":         interaction.user.display_name,
            "cid":           channel.id,
            "mid":           msg.id,
            "quoted_uid":    user.id,
            "quoted_uname":  user.display_name,
            "quoted_avatar": str(user.display_avatar.url),
            "text":          quote,
            "reminder_msg":  None,
            "task":          None,
        }
        task = asyncio.create_task(
            self._gif_timeout_task(gid, msg, channel, interaction.user.id)
        )
        self._pending[gid]["task"] = task

        await interaction.response.send_message(
            embed=discord.Embed(
                description=(
                    f"✅ Quote posted in {channel.mention}!\n"
                    f"Drop a GIF there now to complete it — "
                    f"it'll be cancelled if no GIF is dropped within {var.GIF_TIMEOUT // 60} minutes."
                ),
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )

    # ── /quote_edit ───────────────────────────────────────────────────────────

    @app_commands.command(name="quote_edit", description="Edit your most recently submitted quote.")
    @app_commands.describe(
        text="New quote text (leave blank to keep current)",
        user="New person being quoted (leave blank to keep current)",
    )
    async def quote_edit(
        self,
        interaction: discord.Interaction,
        text: str | None = None,
        user: discord.Member | None = None,
    ):
        if text is None and user is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="Provide a new **text** and/or a new **user** to change.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        gid        = str(interaction.guild_id)
        quoter_uid = str(interaction.user.id)

        rows = self.db.execute(
            """SELECT id, quoted_user_id, quoted_user_name, quote_text,
                      embed_message_id, channel_id
               FROM quotes
               WHERE guild_id = ? AND quoter_user_id = ?
               ORDER BY id DESC LIMIT 1""",
            (gid, quoter_uid),
        )
        if not rows:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="You haven't submitted any completed quotes yet.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        row = rows[0]
        quote_id, old_quoted_uid, old_quoted_uname, old_text, embed_mid, ch_id = row

        new_text        = text if text is not None else old_text
        new_quoted_uid  = str(user.id) if user else old_quoted_uid
        new_quoted_uname = user.display_name if user else old_quoted_uname
        new_avatar      = str(user.display_avatar.url) if user else None

        self.db.execute(
            """UPDATE quotes
               SET quote_text = ?, quoted_user_id = ?, quoted_user_name = ?
                   {avatar_clause}
               WHERE id = ?""".replace(
                "{avatar_clause}",
                ", quoted_user_avatar = ?" if new_avatar else "",
            ),
            (new_text, new_quoted_uid, new_quoted_uname, new_avatar, quote_id)
            if new_avatar else
            (new_text, new_quoted_uid, new_quoted_uname, quote_id),
        )

        # Edit the live Discord embed if we can reach it
        if embed_mid and ch_id:
            ch = self.bot.get_channel(int(ch_id))
            if ch:
                try:
                    orig = await ch.fetch_message(int(embed_mid))
                    old_embed = orig.embeds[0] if orig.embeds else None
                    new_embed = discord.Embed(
                        description=f'> {new_text}\n\n**— {new_quoted_uname}**',
                        color=var.COLOR_QUOTE,
                    )
                    if user:
                        new_embed.set_thumbnail(url=user.display_avatar.url)
                    elif old_embed and old_embed.thumbnail:
                        new_embed.set_thumbnail(url=old_embed.thumbnail.url)
                    if old_embed and old_embed.footer:
                        new_embed.set_footer(text=old_embed.footer.text)
                    new_embed.timestamp = old_embed.timestamp if old_embed else datetime.utcnow()
                    await orig.edit(embed=new_embed)
                except Exception:
                    pass

        await interaction.response.send_message(
            embed=discord.Embed(description="✅ Quote updated!", color=var.COLOR_WIN),
            ephemeral=True,
        )

    # ── /quote_count ──────────────────────────────────────────────────────────

    @app_commands.command(name="quote_count", description="Show quote statistics for a user.")
    @app_commands.describe(user="User to check (defaults to yourself)")
    @app_commands.check(_require_quote_tracker)
    async def quote_count(self, interaction: discord.Interaction, user: discord.Member | None = None):
        target = user or interaction.user
        uid    = str(target.id)
        gid    = str(interaction.guild_id)

        period_sql, period_params = _get_period_filter()

        rows = self.db.execute(
            f"SELECT COUNT(*) FROM quotes WHERE guild_id = ? AND quoted_user_id = ?{period_sql}",
            (gid, uid, *period_params),
        )
        times_quoted = rows[0][0] if rows else 0

        rows = self.db.execute(
            f"SELECT COUNT(*) FROM quotes WHERE guild_id = ? AND quoter_user_id = ?{period_sql}",
            (gid, uid, *period_params),
        )
        times_quoter = rows[0][0] if rows else 0

        period = _period_label()
        embed = discord.Embed(
            title=f"📖 Quote Stats — {target.display_name}",
            color=var.COLOR_QUOTE,
        )
        embed.add_field(name="Times Quoted",      value=f"**{times_quoted:,}**", inline=True)
        embed.add_field(name="Quotes Submitted",  value=f"**{times_quoter:,}**", inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"{period} · {var.SERVER_NAME}" if period else var.SERVER_NAME)
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    # ── /quote_random ─────────────────────────────────────────────────────────

    @app_commands.command(name="quote_random", description="Show a random quote from the archives.")
    async def quote_random(self, interaction: discord.Interaction):
        gid = str(interaction.guild_id)

        rows = self.db.execute(
            """SELECT quoted_user_name, quoted_user_avatar, quoter_user_name,
                      quote_text, gif_url
               FROM quotes
               WHERE guild_id = ?
               ORDER BY RANDOM() LIMIT 1""",
            (gid,),
        )
        if not rows:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="No quotes in the archives yet! Use `/quote` to add some.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        quoted_name, quoted_avatar, quoter_name, text, gif_url = rows[0]

        embed = discord.Embed(
            description=f'> {text}\n\n**— {quoted_name}**',
            color=var.COLOR_QUOTE,
        )
        if quoted_avatar:
            embed.set_thumbnail(url=quoted_avatar)
        embed.set_footer(text=f"Quoted by {quoter_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()

        await interaction.response.send_message(embed=embed)

        if gif_url:
            await interaction.followup.send(gif_url)

    # ── /quote_top_quoted ─────────────────────────────────────────────────────

    @app_commands.command(name="quote_top_quoted", description="Show who has been quoted the most on this server.")
    @app_commands.check(_require_quote_tracker)
    async def quote_top_quoted(self, interaction: discord.Interaction):
        gid = str(interaction.guild_id)

        period_sql, period_params = _get_period_filter()
        rows = self.db.execute(
            f"""SELECT quoted_user_name, COUNT(*) as cnt
               FROM quotes WHERE guild_id = ?{period_sql}
               GROUP BY quoted_user_id
               ORDER BY cnt DESC LIMIT 10""",
            (gid, *period_params),
        )

        if not rows:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="No quotes in the archives yet! Use `/quote` to add some.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (name, cnt) in enumerate(rows):
            prefix = medals[i] if i < 3 else f"**{i + 1}.**"
            lines.append(f"{prefix} **{name}** — {cnt:,} quote{'s' if cnt != 1 else ''}")

        period = _period_label()
        embed = discord.Embed(
            title="📖 Most Quoted",
            description="\n".join(lines),
            color=var.COLOR_QUOTE,
        )
        embed.set_footer(text=f"{period} · {var.SERVER_NAME}" if period else var.SERVER_NAME)
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    # ── /quote_search ─────────────────────────────────────────────────────────

    @app_commands.command(name="quote_search", description="Browse quotes by a specific person.")
    @app_commands.describe(
        user="Person to look up",
        filter="'quoted' = things they said, 'submitted' = quotes they submitted (default: quoted)",
    )
    @app_commands.choices(filter=[
        app_commands.Choice(name="quoted",    value="quoted"),
        app_commands.Choice(name="submitted", value="submitted"),
    ])
    @app_commands.check(_require_quote_tracker)
    async def quote_search(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        filter: str = "quoted",
    ):
        gid = str(interaction.guild_id)
        uid = str(user.id)

        period_sql, period_params = _get_period_filter()

        if filter == "submitted":
            rows = self.db.execute(
                f"""SELECT quote_text, quoted_user_name, quoter_user_name, created_at
                   FROM quotes
                   WHERE guild_id = ? AND quoter_user_id = ?{period_sql}
                   ORDER BY id DESC LIMIT 8""",
                (gid, uid, *period_params),
            )
            label = f"Quotes submitted by {user.display_name}"
        else:
            rows = self.db.execute(
                f"""SELECT quote_text, quoted_user_name, quoter_user_name, created_at
                   FROM quotes
                   WHERE guild_id = ? AND quoted_user_id = ?{period_sql}
                   ORDER BY id DESC LIMIT 8""",
                (gid, uid, *period_params),
            )
            label = f"Quotes from {user.display_name}"

        if not rows:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"No quotes found for **{user.display_name}** ({filter}).",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        def fmt_row(r):
            text, quoted_name, quoter_name, created_at = r
            date = created_at[:10] if created_at else "?"
            return f'> {text}\n**— {quoted_name}** · *Submitted by {quoter_name} · {date}*'

        description = "\n\n".join(fmt_row(r) for r in rows)
        if len(description) > 4096:
            description = description[:4090] + "…"

        period = _period_label()
        footer_parts = ["Showing up to 8 most recent"]
        if period:
            footer_parts.append(period)
        footer_parts.append(var.SERVER_NAME)

        embed = discord.Embed(
            title=f"📖 {label}",
            description=description,
            color=var.COLOR_QUOTE,
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=" · ".join(footer_parts))
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    # ── /quote_lookup ─────────────────────────────────────────────────────────

    @app_commands.command(name="quote_lookup", description="Search quotes containing a specific word or phrase.")
    @app_commands.describe(word="Word or phrase to search for in the quote text")
    @app_commands.check(_require_quote_tracker)
    async def quote_lookup(self, interaction: discord.Interaction, word: str):
        gid = str(interaction.guild_id)

        period_sql, period_params = _get_period_filter()
        rows = self.db.execute(
            f"""SELECT quote_text, quoted_user_name, quoter_user_name, created_at
               FROM quotes
               WHERE guild_id = ? AND LOWER(quote_text) LIKE ?{period_sql}
               ORDER BY id DESC LIMIT 8""",
            (gid, f"%{word.lower()}%", *period_params),
        )

        if not rows:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f'No quotes found containing **"{word}"**.',
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        def fmt_row(r):
            text, quoted_name, quoter_name, created_at = r
            date = created_at[:10] if created_at else "?"
            return f'> {text}\n**— {quoted_name}** · *Submitted by {quoter_name} · {date}*'

        description = "\n\n".join(fmt_row(r) for r in rows)
        if len(description) > 4096:
            description = description[:4090] + "…"

        period = _period_label()
        footer_parts = ["Showing up to 8 results"]
        if period:
            footer_parts.append(period)
        footer_parts.append(var.SERVER_NAME)

        embed = discord.Embed(
            title=f'📖 Quotes containing "{word}"',
            description=description,
            color=var.COLOR_QUOTE,
        )
        embed.set_footer(text=" · ".join(footer_parts))
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    # ── /quote_top_quoters ────────────────────────────────────────────────────

    @app_commands.command(name="quote_top_quoters", description="Show who has submitted the most quotes on this server.")
    @app_commands.check(_require_quote_tracker)
    async def quote_top_quoters(self, interaction: discord.Interaction):
        gid = str(interaction.guild_id)

        period_sql, period_params = _get_period_filter()
        rows = self.db.execute(
            f"""SELECT quoter_user_name, COUNT(*) as cnt
               FROM quotes WHERE guild_id = ?{period_sql}
               GROUP BY quoter_user_id
               ORDER BY cnt DESC LIMIT 10""",
            (gid, *period_params),
        )

        if not rows:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="No quotes in the archives yet! Use `/quote` to add some.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (name, cnt) in enumerate(rows):
            prefix = medals[i] if i < 3 else f"**{i + 1}.**"
            lines.append(f"{prefix} **{name}** — {cnt:,} quote{'s' if cnt != 1 else ''}")

        period = _period_label()
        embed = discord.Embed(
            title="📖 Top Quoters",
            description="\n".join(lines),
            color=var.COLOR_QUOTE,
        )
        embed.set_footer(text=f"{period} · {var.SERVER_NAME}" if period else var.SERVER_NAME)
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    # ── /quote_statsdate ──────────────────────────────────────────────────────

    @app_commands.command(name="quote_statsdate", description="Set or clear the date range all stat commands filter by.")
    @app_commands.describe(
        from_date="Start date (YYYY-MM-DD). Leave blank to clear the filter.",
        to_date="End date (YYYY-MM-DD, optional — leave blank for no end).",
    )
    @app_commands.check(_require_quote_tracker)
    async def quote_statsdate(
        self,
        interaction: discord.Interaction,
        from_date: str | None = None,
        to_date: str | None = None,
    ):
        if from_date is None and to_date is None:
            data = _load_settings()
            data.pop('period_from', None)
            data.pop('period_to', None)
            _save_settings(data)
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="✅ Date filter cleared — all stat commands now show all-time.",
                    color=var.COLOR_WIN,
                ),
                ephemeral=True,
            )
            return

        for label, d in [("from_date", from_date), ("to_date", to_date)]:
            if d is None:
                continue
            try:
                datetime.strptime(d, "%Y-%m-%d")
            except ValueError:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description=f'❌ Invalid date **"{d}"**. Use **YYYY-MM-DD** (e.g. `2024-06-15`).',
                        color=var.COLOR_ERROR,
                    ),
                    ephemeral=True,
                )
                return

        data = _load_settings()
        data['period_from'] = from_date
        if to_date:
            data['period_to'] = to_date
        else:
            data.pop('period_to', None)
        _save_settings(data)

        label = f"**{from_date}** → **{to_date}**" if to_date else f"**{from_date}** onwards"
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Stat commands will now filter to {label}.",
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )

    # ── /set_quote_channel ────────────────────────────────────────────────────

    @app_commands.command(name="set_quote_channel", description="Set the channel where quotes are posted.")
    @app_commands.describe(channel="Channel to post quotes in")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_quote_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        data = _load_settings()
        data['quote_channel_id'] = channel.id
        _save_settings(data)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Quotes will be posted in {channel.mention}.",
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(QuotesCog(bot))
    log.info("✅ Quotes cog loaded")
