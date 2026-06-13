import discord
from discord.ext import commands
from discord import app_commands
import json
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('q_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

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


def _is_gif(message: discord.Message) -> bool:
    if any(a.filename.lower().endswith('.gif') for a in message.attachments):
        return True
    for embed in message.embeds:
        if embed.type == 'gifv':
            return True
        url = embed.url or ''
        if 'tenor.com' in url or 'giphy.com' in url:
            return True
    content = (message.content or '').lower()
    if 'tenor.com' in content or 'giphy.com' in content:
        return True
    return False


class QuotesCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # guild_id -> (user_id, channel_id)
        self._pending_gif: dict[str, tuple[int, int]] = {}

    def _get_channel(self) -> discord.TextChannel | None:
        cid = _load_settings().get('quote_channel_id')
        return self.bot.get_channel(int(cid)) if cid else None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        gid = str(message.guild.id)
        pending = self._pending_gif.get(gid)
        if pending is None:
            return
        pending_uid, pending_cid = pending
        if message.author.id == pending_uid and message.channel.id == pending_cid and _is_gif(message):
            del self._pending_gif[gid]

    @app_commands.command(name="quote", description="Post a quote from someone to the quotes channel.")
    @app_commands.describe(
        user="The person being quoted",
        quote="What they said",
    )
    async def quote(self, interaction: discord.Interaction, user: discord.Member, quote: str):
        gid = str(interaction.guild_id)

        pending = self._pending_gif.get(gid)
        if pending:
            pending_uid, pending_cid = pending
            ch = self.bot.get_channel(pending_cid)
            ch_mention = ch.mention if ch else "the quotes channel"
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"⏳ <@{pending_uid}> needs to drop a gif in {ch_mention} before the next quote!",
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

        await channel.send(embed=embed)
        self._pending_gif[gid] = (interaction.user.id, channel.id)

        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Quote posted! Drop a gif in {channel.mention} to unlock the next quote.",
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )

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
