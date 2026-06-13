import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('lb_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")


class LeaderboardCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    @app_commands.command(name="bal_top", description="View the richest players on the server.")
    async def bal_top(self, interaction: discord.Interaction):
        gid  = str(interaction.guild_id)
        rows = self.db.execute(
            """SELECT u.user_id, u.balance, COALESCE(c.games_played, 0)
               FROM users u
               LEFT JOIN casino_stats c ON u.user_id = c.user_id AND u.guild_id = c.guild_id
               WHERE u.guild_id = ?
               ORDER BY u.balance DESC LIMIT ?""",
            (gid, var.LEADERBOARD_TOP_COUNT),
        )
        embed = discord.Embed(
            title=f"🏆 {var.CURRENCY_NAME.capitalize()} Leaderboard",
            color=var.COLOR_INFO,
        )
        if not rows:
            embed.description = "No players yet — start gambling to appear here!"
        else:
            lines = []
            for i, (uid, balance, games) in enumerate(rows, 1):
                try:
                    user = await self.bot.fetch_user(int(uid))
                    name = user.display_name
                except Exception:
                    name = f"User {uid}"
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                lines.append(
                    f"{medal} {name} — {var.CURRENCY_SYMBOL} **{balance:,}** "
                    f"*({games:,} game{'s' if games != 1 else ''})*"
                )
            embed.description = "\n".join(lines)
        embed.set_footer(text=f"{var.SERVER_NAME} Casino")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
    log.info("✅ User/Leaderboard cog loaded")
