import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('stats_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")


def _get_level(uid: str, gid: str, db) -> int:
    # Placeholder — replace with real XP lookup once the XP system is added
    return 1


class StatsCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    @app_commands.command(name="stats", description="View your player profile — level, balance & more.")
    @app_commands.describe(member="Another user to look up (leave empty for yourself)")
    async def stats(self, interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        uid    = str(target.id)
        gid    = str(interaction.guild_id)
        self.db.ensure_user(uid, gid, target.display_name)

        balance = self.db.get_balance(uid, gid)
        level   = _get_level(uid, gid, self.db)

        embed = discord.Embed(
            title=f"📊 {target.display_name}",
            color=var.COLOR_INFO,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(
            name="💰 Balance",
            value=f"{var.CURRENCY_SYMBOL} **{balance:,}** {var.CURRENCY_NAME}",
            inline=True,
        )
        embed.add_field(
            name="⭐ Level",
            value=f"**{level}**",
            inline=True,
        )
        embed.set_footer(text=var.SERVER_NAME)
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(StatsCog(bot))
    log.info("✅ User/Stats cog loaded")
