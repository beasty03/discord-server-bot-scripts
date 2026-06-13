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

    async def _build_board(
        self,
        interaction: discord.Interaction,
        title: str,
        rows: list,
        value_fmt: str,
    ) -> None:
        embed = discord.Embed(title=title, color=var.COLOR_INFO)
        if not rows:
            embed.description = "No data yet!"
        else:
            lines = []
            for i, row in enumerate(rows, 1):
                uid, value, *extras = row
                try:
                    user = await self.bot.fetch_user(int(uid))
                    name = user.display_name
                except Exception:
                    name = f"User {uid}"
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                kwargs = {
                    "v":   value,
                    "v_s": "" if value == 1 else "s",
                    "sym": var.CURRENCY_SYMBOL,
                    "cur": var.CURRENCY_NAME,
                    **{f"e{j}": v for j, v in enumerate(extras)},
                    **{f"e{j}_s": ("" if v == 1 else "s") for j, v in enumerate(extras) if isinstance(v, int)},
                }
                lines.append(f"{medal} {name} — {value_fmt.format(**kwargs)}")
            embed.description = "\n".join(lines)
        embed.set_footer(text=var.SERVER_NAME)
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="top_bal", description="Top players by current balance.")
    async def top_bal(self, interaction: discord.Interaction):
        gid  = str(interaction.guild_id)
        rows = self.db.execute(
            "SELECT user_id, balance FROM users WHERE guild_id = ? ORDER BY balance DESC LIMIT ?",
            (gid, var.LEADERBOARD_TOP_COUNT),
        )
        await self._build_board(
            interaction,
            "🏆 Richest Players",
            [(r[0], r[1]) for r in rows],
            "{sym} **{v:,}** {cur}",
        )

    @app_commands.command(name="top_wins", description="Top players by games played, with total winnings.")
    async def top_wins(self, interaction: discord.Interaction):
        gid  = str(interaction.guild_id)
        rows = self.db.execute(
            "SELECT user_id, games_played, total_won FROM casino_stats WHERE guild_id = ? ORDER BY games_played DESC LIMIT ?",
            (gid, var.LEADERBOARD_TOP_COUNT),
        )
        await self._build_board(
            interaction,
            "🎰 Most Active Players",
            [(r[0], r[1], r[2]) for r in rows],
            "**{v:,}** game{v_s} · {sym} {e0:,} won",
        )

    @app_commands.command(name="top_losses", description="Top players by games played, with total losses.")
    async def top_losses(self, interaction: discord.Interaction):
        gid  = str(interaction.guild_id)
        rows = self.db.execute(
            "SELECT user_id, games_played, total_lost FROM casino_stats WHERE guild_id = ? ORDER BY games_played DESC LIMIT ?",
            (gid, var.LEADERBOARD_TOP_COUNT),
        )
        await self._build_board(
            interaction,
            "📉 Most Games Lost",
            [(r[0], r[1], r[2]) for r in rows],
            "**{v:,}** game{v_s} · {sym} {e0:,} lost",
        )

    @app_commands.command(name="top_give", description="Top players by total coins given to others.")
    async def top_give(self, interaction: discord.Interaction):
        gid  = str(interaction.guild_id)
        rows = self.db.execute(
            """SELECT user_id, SUM(-amount) as total_given
               FROM transactions
               WHERE guild_id = ? AND transaction_type = 'transfer_out'
               GROUP BY user_id
               ORDER BY total_given DESC
               LIMIT ?""",
            (gid, var.LEADERBOARD_TOP_COUNT),
        )
        await self._build_board(
            interaction,
            "🎁 Most Generous Players",
            [(r[0], r[1]) for r in rows],
            "{sym} **{v:,}** given",
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
    log.info("✅ User/Leaderboard cog loaded")
