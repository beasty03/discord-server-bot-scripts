import importlib.util as _ilu
import json
import logging
from datetime import datetime
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

_spec = _ilu.spec_from_file_location('scribe_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

from forge_db import ForgeDB

log = logging.getLogger("launcher")


def _generate_story(campaign_name: str, participants: list[list],
                    success: bool, run_log: list[dict]) -> str:
    """
    Build a narrative recap from the run log.
    TODO: replace body with an Ollama API call for richer prose.
    """
    names   = " and ".join(f"**{name}**" for _, name in participants)
    outcome = "emerged victorious" if success else "were defeated"
    lines   = [f"{names} ventured into **{campaign_name}** — and {outcome}.\n"]

    for event in run_log:
        t = event.get("type")

        if t == "attack" and event.get("hit"):
            crit = " *(critical hit!)*" if event.get("crit") else ""
            lines.append(
                f"**{event['name']}** struck **{event['enemy']}** for {event['dmg']} damage{crit}.")

        elif t == "kill":
            if event.get("kill_flavor"):
                lines.append(
                    f"**{event['name']}** finished off **{event['enemy']}** — "
                    f"*\"{event['kill_flavor']}\"*")
            else:
                lines.append(
                    f"**{event['name']}** delivered the killing blow to **{event['enemy']}**.")

        elif t == "skill_success":
            if event.get("flavor"):
                lines.append(
                    f"**{event['name']}** faced **{event['encounter']}** and said: "
                    f"*\"{event['flavor']}\"* — a {event['skill'].title()} check of "
                    f"**{event['total']}** against DC {event['dc']} sealed the deal.")
            else:
                lines.append(
                    f"**{event['name']}** passed the {event['skill'].title()} check "
                    f"(**{event['total']}** vs DC {event['dc']}) for **{event['encounter']}**.")

        elif t == "skill_fail":
            lines.append(
                f"**{event['name']}** failed the {event['skill'].title()} check "
                f"(**{event['total']}** vs DC {event['dc']}) — **{event['encounter']}** went sideways.")

        elif t == "enemy_hit":
            lines.append(
                f"**{event['enemy']}** landed a blow on **{event['target_name']}** "
                f"for {event['dmg']} damage.")

        elif t == "flee":
            lines.append(f"**{event['name']}** fled from the battle!")

        elif t == "interaction_fight":
            lines.append(f"The party chose to fight rather than negotiate at **{event['encounter']}**.")

    return "\n".join(lines)


class ScribeCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    # ── /story ────────────────────────────────────────────────────────────────

    @app_commands.command(name="story", description="Read the tale of a player's last campaign run.")
    @app_commands.describe(member="Whose last run to show (leave empty for yourself)")
    async def story(self, interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        uid    = str(target.id)
        gid    = str(interaction.guild_id)

        rows = self.db.execute(
            "SELECT run_id, campaign_name, participants, success, log_json, created_at "
            "FROM dnd_run_log "
            "WHERE guild_id=? AND participants LIKE ? "
            "ORDER BY created_at DESC LIMIT 1",
            (gid, f'%{uid}%'),
        )

        if not rows:
            who = "They haven't" if member else "You haven't"
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"{who} completed any campaigns yet.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        _, campaign_name, participants_json, success, log_json, created_at = rows[0]
        participants = json.loads(participants_json)
        run_log      = json.loads(log_json)

        story_text = _generate_story(campaign_name, participants, bool(success), run_log)

        try:
            ts = datetime.fromisoformat(created_at)
            date_str = ts.strftime("%B %d, %Y")
        except Exception:
            date_str = created_at[:10]

        embed = discord.Embed(
            title=f"📖 {campaign_name}",
            description=story_text,
            color=var.COLOR_STORY,
        )
        embed.set_footer(text=f"{var.SERVER_NAME} · {date_str}")
        await interaction.response.send_message(embed=embed)

    # ── /set_scribe_channel ───────────────────────────────────────────────────

    @app_commands.command(
        name="set_scribe_channel",
        description="Set the channel where the Scribe auto-posts campaign stories.")
    @app_commands.describe(channel="Channel to post stories in")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_scribe_channel(self, interaction: discord.Interaction,
                                  channel: discord.TextChannel):
        # Stored in the shared config so the DungeonMaster can reach it too
        from utils.config_loader import load_config, save_config
        cfg = load_config()
        cfg["scribe_channel_id"] = channel.id
        save_config(cfg)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ The Scribe will post campaign stories in {channel.mention}.",
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ScribeCog(bot))
    log.info("✅ DND/Scribe cog loaded")
