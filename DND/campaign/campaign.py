import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
import random
import uuid
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu

_spec = _ilu.spec_from_file_location('dnd_campaign_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

# Load character variables for XP thresholds — unique name avoids module cache collision.
_char_spec = _ilu.spec_from_file_location(
    'dnd_char_vars_for_campaign', Path(__file__).parent.parent / 'character' / 'variables.py')
char_var = _ilu.module_from_spec(_char_spec)
_char_spec.loader.exec_module(char_var)

from forge_db import ForgeDB

log = logging.getLogger("launcher")

# ============================================================================
# VIEWS
# ============================================================================

class _WanderJoinView(discord.ui.View):
    """Posted publicly in the channel; party members click to opt into the run."""

    def __init__(self, cog: "CampaignCog", campaign: dict,
                 initiator_uid: str, initiator_name: str, party_members: list[str]):
        super().__init__(timeout=var.WANDER_JOIN_TIMEOUT)
        self.cog           = cog
        self.campaign      = campaign
        self.party_members = set(party_members)
        self.joiners: list[tuple[str, str]] = [(initiator_uid, initiator_name)]
        self._joiner_set: set[str]          = {initiator_uid}

    def build_embed(self) -> discord.Embed:
        c     = self.campaign
        names = ", ".join(n for _, n in self.joiners)
        embed = discord.Embed(
            title=f"{c['emoji']} {c['name']}  —  {c['difficulty']}",
            description=(
                f"*{c['intro']}*\n\n"
                f"**Min level:** {c['min_level']}  ·  "
                f"**Reward:** up to {c['reward_gold_max']:,} {var.CURRENCY_SYMBOL}  ·  {c['reward_xp']:,} XP\n\n"
                f"**Party:** {names}\n\n"
                f"⚔️ Click below to join! Window closes in **{var.WANDER_JOIN_TIMEOUT}s**."
            ),
            color=var.COLOR_CAMPAIGN,
        )
        embed.set_footer(text=var.SERVER_NAME)
        return embed

    @discord.ui.button(label="⚔️ Join the quest", style=discord.ButtonStyle.success)
    async def join_btn(self, interaction: discord.Interaction, btn: discord.ui.Button):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if uid not in self.party_members:
            await interaction.response.send_message(
                "Only party members can join this quest.", ephemeral=True)
            return
        if uid in self._joiner_set:
            await interaction.response.send_message(
                "You're already joining!", ephemeral=True)
            return
        if self.cog._is_in_run(uid, gid):
            await interaction.response.send_message(
                "You're already in an active campaign run.", ephemeral=True)
            return

        self._joiner_set.add(uid)
        self.joiners.append((uid, interaction.user.display_name))
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


class _CampaignSelectView(discord.ui.View):
    """Ephemeral select shown to the initiator for picking a campaign."""

    def __init__(self, cog: "CampaignCog", uid: str, gid: str, campaigns: list[dict]):
        super().__init__(timeout=60)
        self.cog       = cog
        self.uid       = uid
        self.gid       = gid
        self._map      = {c["id"]: c for c in campaigns}

        options = [
            discord.SelectOption(
                label=f"{c['emoji']} {c['name']}",
                value=c["id"],
                description=f"{c['difficulty']} · Min Lv {c['min_level']} · {c['reward_xp']} XP",
            )
            for c in campaigns
        ]
        sel = discord.ui.Select(placeholder="Choose a campaign…", options=options)
        sel.callback = self._on_select
        self.add_item(sel)

    async def _on_select(self, interaction: discord.Interaction):
        campaign = self._map[interaction.data["values"][0]]
        self.stop()
        await self.cog._start_wander(interaction, campaign, self.uid, self.gid)


# ============================================================================
# COG
# ============================================================================

class CampaignCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    async def cog_load(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS dnd_active_runs (
                user_id     TEXT NOT NULL,
                guild_id    TEXT NOT NULL,
                run_id      TEXT NOT NULL,
                campaign_id TEXT NOT NULL,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _err(msg: str) -> discord.Embed:
        return discord.Embed(description=msg, color=var.COLOR_ERROR)

    def _is_in_run(self, uid: str, gid: str) -> bool:
        return bool(self.db.execute(
            "SELECT 1 FROM dnd_active_runs WHERE user_id = ? AND guild_id = ?", (uid, gid)))

    def _fetch_char(self, uid: str, gid: str) -> dict | None:
        rows = self.db.execute(
            "SELECT level, xp, name FROM dnd_characters WHERE user_id = ? AND guild_id = ?",
            (uid, gid),
        )
        return {"level": rows[0][0], "xp": rows[0][1], "name": rows[0][2]} if rows else None

    def _claim_slot(self, uid: str, gid: str, run_id: str, campaign_id: str) -> bool:
        """Insert the initiator's run row. Returns False on PK conflict (already in a run)."""
        try:
            self.db.execute(
                "INSERT INTO dnd_active_runs (user_id, guild_id, run_id, campaign_id) VALUES (?, ?, ?, ?)",
                (uid, gid, run_id, campaign_id),
            )
            return True
        except Exception:
            return False

    def _add_to_run(self, uid: str, gid: str, run_id: str, campaign_id: str):
        self.db.execute(
            "INSERT OR IGNORE INTO dnd_active_runs (user_id, guild_id, run_id, campaign_id) VALUES (?, ?, ?, ?)",
            (uid, gid, run_id, campaign_id),
        )

    def _clear_run(self, run_id: str):
        self.db.execute("DELETE FROM dnd_active_runs WHERE run_id = ?", (run_id,))

    def _give_rewards(self, uid: str, gid: str, display_name: str, gold: int, xp: int):
        self.db.ensure_user(uid, gid, display_name)
        if gold > 0:
            self.db.update_balance(uid, gid, gold, "campaign_reward")

        rows = self.db.execute(
            "SELECT level, xp FROM dnd_characters WHERE user_id = ? AND guild_id = ?", (uid, gid))
        if not rows:
            return
        current_level, current_xp = rows[0]
        new_xp    = (current_xp or 0) + xp
        new_level = current_level or 1
        while new_level < char_var.MAX_LEVEL and new_xp >= char_var.XP_THRESHOLDS[new_level + 1]:
            new_level += 1
        self.db.execute(
            "UPDATE dnd_characters SET xp = ?, level = ? WHERE user_id = ? AND guild_id = ?",
            (new_xp, new_level, uid, gid),
        )
        return new_level

    def _available_campaigns(self, level: int) -> list[dict]:
        return [c for c in var.CAMPAIGNS if c["min_level"] <= level]

    def _parties_cog(self):
        return self.bot.cogs.get("PartiesCog")

    # ── /wander ───────────────────────────────────────────────────────────────

    @app_commands.command(name="wander", description="Choose a campaign and set off on an adventure.")
    async def wander(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        char = self._fetch_char(uid, gid)
        if not char:
            await interaction.response.send_message(
                embed=self._err(
                    "You don't have a character yet. Start with `/name`, then `/race` and `/class`."),
                ephemeral=True)
            return

        if self._is_in_run(uid, gid):
            await interaction.response.send_message(
                embed=self._err("You're already on a campaign. Finish it before starting another."),
                ephemeral=True)
            return

        available = self._available_campaigns(char["level"])
        if not available:
            await interaction.response.send_message(
                embed=self._err(
                    f"No campaigns available at level {char['level']} yet. "
                    "Level up to unlock harder bounties."),
                ephemeral=True)
            return

        embed = discord.Embed(
            title="🗺️ Choose your adventure",
            description=f"Campaigns available for **level {char['level']}**:",
            color=var.COLOR_CAMPAIGN,
        )
        await interaction.response.send_message(
            embed=embed,
            view=_CampaignSelectView(self, uid, gid, available),
            ephemeral=True,
        )

    # ── campaign start (called from the select callback) ──────────────────────

    async def _start_wander(
        self, interaction: discord.Interaction, campaign: dict, uid: str, gid: str,
    ):
        # Re-check in case of a near-simultaneous /wander
        if self._is_in_run(uid, gid):
            await interaction.response.edit_message(
                embed=self._err("You joined another run just now — can't start this one."),
                view=None)
            return

        parties_cog = self._parties_cog()
        party       = parties_cog._member_party(gid, uid) if parties_cog else None

        if party is not None:
            if party["active_run"] is not None:
                await interaction.response.edit_message(
                    embed=self._err("Your party is already on a campaign."), view=None)
                return
            # Claim the party slot atomically before any await
            party["active_run"] = "pending"

        run_id  = uuid.uuid4().hex
        claimed = self._claim_slot(uid, gid, run_id, campaign["id"])
        if not claimed:
            if party:
                party["active_run"] = None
            await interaction.response.edit_message(
                embed=self._err("Couldn't claim a run slot — you may already be in one."),
                view=None)
            return

        await interaction.response.edit_message(
            embed=discord.Embed(
                description=f"{campaign['emoji']} **{campaign['name']}** launched! Check the channel.",
                color=var.COLOR_CAMPAIGN,
            ),
            view=None,
        )

        if party is not None:
            join_view = _WanderJoinView(
                cog=self,
                campaign=campaign,
                initiator_uid=uid,
                initiator_name=interaction.user.display_name,
                party_members=party["members"],
            )
            join_msg = await interaction.channel.send(
                embed=join_view.build_embed(), view=join_view)
            asyncio.create_task(
                self._run_campaign(interaction, campaign, party, run_id, join_view, join_msg))
        else:
            asyncio.create_task(
                self._run_campaign(
                    interaction, campaign, None, run_id, None, None,
                    solo_participants=[(uid, interaction.user.display_name)],
                )
            )

    # ── background campaign runner ─────────────────────────────────────────────

    async def _run_campaign(
        self,
        interaction: discord.Interaction,
        campaign:    dict,
        party,
        run_id:      str,
        join_view:   "_WanderJoinView | None",
        join_msg:    "discord.Message | None",
        solo_participants: "list[tuple[str, str]] | None" = None,
    ):
        gid = str(interaction.guild_id)
        try:
            if join_view is not None:
                await asyncio.sleep(var.WANDER_JOIN_TIMEOUT)
                join_view.stop()
                for item in join_view.children:
                    item.disabled = True
                try:
                    await join_msg.edit(view=join_view)
                except Exception:
                    pass
                participants = join_view.joiners
                # Persist the joiners (initiator already has a row)
                for p_uid, p_name in participants[1:]:
                    self._add_to_run(p_uid, gid, run_id, campaign["id"])
            else:
                participants = solo_participants or []

            if party:
                party["active_run"] = campaign["id"]

            # ── intro ──────────────────────────────────────────────────────────
            names = ", ".join(n for _, n in participants)
            intro = discord.Embed(
                title=f"{campaign['emoji']} {campaign['name']}",
                description=f"*{campaign['intro']}*\n\n**Adventurers:** {names}",
                color=var.COLOR_CAMPAIGN,
            )
            intro.set_footer(text=var.SERVER_NAME)
            await interaction.channel.send(embed=intro)

            await asyncio.sleep(var.WANDER_RESULT_DELAY)

            # ── resolve outcome ────────────────────────────────────────────────
            levels = []
            for p_uid, _ in participants:
                rows = self.db.execute(
                    "SELECT level FROM dnd_characters WHERE user_id = ? AND guild_id = ?",
                    (p_uid, gid))
                levels.append(rows[0][0] if rows else 1)

            avg_level    = sum(levels) / max(1, len(levels))
            level_bonus  = min(0.15, (avg_level - campaign["min_level"]) * 0.02)
            success      = random.random() < min(0.95, campaign["success_chance"] + level_bonus)

            if success:
                total_gold = random.randint(campaign["reward_gold_min"], campaign["reward_gold_max"])
                gold_each  = max(1, total_gold // max(1, len(participants)))
                xp_each    = campaign["reward_xp"]

                result_lines = []
                for p_uid, p_name in participants:
                    new_level = self._give_rewards(p_uid, gid, p_name, gold_each, xp_each)
                    level_up  = f"  🎉 **Level up → {new_level}!**" if new_level and new_level > (levels[0] if levels else 1) else ""
                    result_lines.append(
                        f"• **{p_name}** — +{gold_each:,} {var.CURRENCY_SYMBOL}  ·  +{xp_each:,} XP{level_up}")

                result = discord.Embed(
                    title=f"✅ {campaign['name']} — Victory!",
                    description="\n".join(result_lines),
                    color=var.COLOR_WIN,
                )
            else:
                result = discord.Embed(
                    title=f"❌ {campaign['name']} — Defeated!",
                    description=(
                        "The party was overwhelmed and forced to retreat.\n"
                        "*(No rewards — regroup and try again.)*"
                    ),
                    color=var.COLOR_ERROR,
                )

            result.set_footer(text=var.SERVER_NAME)
            await interaction.channel.send(embed=result)

        finally:
            self._clear_run(run_id)
            if party:
                party["active_run"] = None


async def setup(bot: commands.Bot):
    await bot.add_cog(CampaignCog(bot))
    log.info("✅ DND/Campaign cog loaded")
