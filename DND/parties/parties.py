import discord
from discord.ext import commands
from discord import app_commands
import logging
import time
import uuid
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('dnd_parties_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

from forge_db import ForgeDB

log = logging.getLogger("launcher")

# ============================================================================
# VIEWS
# ============================================================================

class _JoinListView(discord.ui.View):
    """Ephemeral picker: one button per joinable public party."""

    def __init__(self, cog: "PartiesCog", gid: str, parties: list[dict]):
        super().__init__(timeout=var.JOIN_LIST_TIMEOUT)
        self.cog = cog
        self.gid = gid
        for p in parties[:var.MAX_JOIN_BUTTONS]:
            btn = discord.ui.Button(
                label=f"{p['creator_name']}'s party  ({len(p['members'])}/{p['max_size']})",
                style=discord.ButtonStyle.primary,
            )
            btn.callback = self._make_callback(p["party_id"])
            self.add_item(btn)

    def _make_callback(self, party_id: str):
        async def _cb(interaction: discord.Interaction):
            ok, msg = self.cog._try_join(
                self.gid, str(interaction.user.id), interaction.user.display_name, party_id,
            )
            for item in self.children:
                item.disabled = True
            color = var.COLOR_WIN if ok else var.COLOR_ERROR
            await interaction.response.edit_message(
                embed=discord.Embed(description=msg, color=color), view=None,
            )
            self.stop()
        return _cb


class _InviteView(discord.ui.View):
    """Accept/Decline buttons sent to an invited player. Only the target may use them."""

    def __init__(self, cog: "PartiesCog", gid: str, party_id: str, target_uid: str):
        super().__init__(timeout=var.INVITE_TIMEOUT)
        self.cog = cog
        self.gid = gid
        self.party_id = party_id
        self.target_uid = target_uid

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.target_uid:
            await interaction.response.send_message(
                "This invite isn't for you.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, _b: discord.ui.Button):
        ok, msg = self.cog._try_join(
            self.gid, self.target_uid, interaction.user.display_name, self.party_id,
        )
        color = var.COLOR_WIN if ok else var.COLOR_ERROR
        await interaction.response.edit_message(
            embed=discord.Embed(description=msg, color=color), view=None)
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.secondary)
    async def decline(self, interaction: discord.Interaction, _b: discord.ui.Button):
        party = self.cog._parties.get(self.gid, {}).get(self.party_id)
        if party:
            party["invites"].discard(self.target_uid)
        await interaction.response.edit_message(
            embed=discord.Embed(description="Invite declined.", color=var.COLOR_INFO), view=None)
        self.stop()

# ============================================================================
# COG
# ============================================================================

class PartiesCog(commands.Cog):

    party = app_commands.Group(name="party", description="Form and manage adventuring parties.")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()
        # gid -> { party_id -> party dict }
        self._parties: dict[str, dict[str, dict]] = {}

    # ── helpers ───────────────────────────────────────────────────────────────

    def _has_character(self, uid: str, gid: str) -> bool:
        """Query dnd_characters directly so we don't depend on the character cog being loaded."""
        try:
            rows = self.db.execute(
                "SELECT 1 FROM dnd_characters WHERE user_id = ? AND guild_id = ?", (uid, gid))
            return bool(rows)
        except Exception:
            return False

    def _member_party(self, gid: str, uid: str) -> dict | None:
        for p in self._parties.get(gid, {}).values():
            if uid in p["members"]:
                return p
        return None

    def _try_join(self, gid: str, uid: str, name: str, party_id: str) -> tuple[bool, str]:
        """Re-validate everything at click/accept time, then join. Returns (ok, message)."""
        if not self._has_character(uid, gid):
            return False, "You need a character first — use `/name`, `/race`, `/class`."
        if self._member_party(gid, uid):
            return False, "You're already in a party. Use `/party leave` first."

        party = self._parties.get(gid, {}).get(party_id)
        if not party:
            return False, "That party no longer exists."
        if party["active_run"] is not None:
            return False, "That party is already on a campaign."
        if len(party["members"]) >= party["max_size"]:
            return False, f"That party is full ({party['max_size']}/{party['max_size']})."
        if party["visibility"] == "private" and uid not in party["invites"]:
            return False, "That party is private — you need an invite."

        party["members"].append(uid)
        party["invites"].discard(uid)
        return True, f"✅ You joined **{party['creator_name']}'s party** ({len(party['members'])}/{party['max_size']})."

    @staticmethod
    def _err(msg: str) -> discord.Embed:
        return discord.Embed(description=msg, color=var.COLOR_ERROR)

    # ── /party create ───────────────────────────────────────────────────────────

    @party.command(name="create", description="Create a new party (public or private).")
    @app_commands.describe(visibility="Public parties show in /party join; private ones are invite-only.")
    @app_commands.choices(visibility=[
        app_commands.Choice(name="Public",  value="public"),
        app_commands.Choice(name="Private", value="private"),
    ])
    async def party_create(self, interaction: discord.Interaction, visibility: app_commands.Choice[str] | None = None):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)
        vis = visibility.value if visibility else "public"

        if self.db.execute("SELECT 1 FROM dnd_active_runs WHERE user_id=? AND guild_id=?", (uid, gid)):
            await interaction.response.send_message(
                embed=discord.Embed(description="⚔️ You're on an active campaign — finish the adventure before forming a new party.", color=0xe74c3c),
                ephemeral=True)
            return

        if not self._has_character(uid, gid):
            await interaction.response.send_message(
                embed=self._err("You need a character first — use `/name`, `/race`, `/class`."),
                ephemeral=True)
            return
        if self._member_party(gid, uid):
            await interaction.response.send_message(
                embed=self._err("You're already in a party. Use `/party leave` first."),
                ephemeral=True)
            return

        pid = uuid.uuid4().hex[:6]
        self._parties.setdefault(gid, {})[pid] = {
            "party_id":     pid,
            "creator_uid":  uid,
            "creator_name": interaction.user.display_name,
            "members":      [uid],
            "visibility":   vis,
            "invites":      set(),
            "max_size":     var.MAX_PARTY_SIZE,
            "active_run":   None,
            "created_ts":   int(time.time()),
        }

        if vis == "public":
            embed = discord.Embed(
                title="🛡️ A party has formed!",
                description=(
                    f"{interaction.user.mention} started a **public** party.\n"
                    f"Use `/party join` to hop in — up to **{var.MAX_PARTY_SIZE}** adventurers."
                ),
                color=var.COLOR_PARTY,
            )
            embed.set_footer(text=var.SERVER_NAME)
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="🔒 Private party created",
                description=(
                    f"Only people you `/party invite` can join.\n"
                    f"Up to **{var.MAX_PARTY_SIZE}** adventurers."
                ),
                color=var.COLOR_PARTY,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /party join ───────────────────────────────────────────────────────────

    @party.command(name="join", description="Browse and join an open public party.")
    async def party_join(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if self.db.execute("SELECT 1 FROM dnd_active_runs WHERE user_id=? AND guild_id=?", (uid, gid)):
            await interaction.response.send_message(
                embed=discord.Embed(description="⚔️ You're on an active campaign — finish the adventure before joining another party.", color=0xe74c3c),
                ephemeral=True)
            return

        if not self._has_character(uid, gid):
            await interaction.response.send_message(
                embed=self._err("You need a character first — use `/name`, `/race`, `/class`."),
                ephemeral=True)
            return
        if self._member_party(gid, uid):
            await interaction.response.send_message(
                embed=self._err("You're already in a party. Use `/party leave` first."),
                ephemeral=True)
            return

        open_parties = [
            p for p in self._parties.get(gid, {}).values()
            if p["visibility"] == "public"
            and p["active_run"] is None
            and len(p["members"]) < p["max_size"]
        ]
        if not open_parties:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="No open parties right now. Start one with `/party create`.",
                    color=var.COLOR_INFO),
                ephemeral=True)
            return

        embed = discord.Embed(
            title="🛡️ Open parties",
            description="Pick a party to join:",
            color=var.COLOR_PARTY,
        )
        await interaction.response.send_message(
            embed=embed, view=_JoinListView(self, gid, open_parties), ephemeral=True)

    # ── /party invite ───────────────────────────────────────────────────────────

    @party.command(name="invite", description="Invite a player to your party (any member can invite).")
    @app_commands.describe(member="The player to invite")
    async def party_invite(self, interaction: discord.Interaction, member: discord.Member):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)
        tid = str(member.id)

        party = self._member_party(gid, uid)
        if party is None:
            await interaction.response.send_message(
                embed=self._err("You're not in a party. Create one with `/party create`."),
                ephemeral=True)
            return
        if party["active_run"] is not None:
            await interaction.response.send_message(
                embed=self._err("Your party is already on a campaign."), ephemeral=True)
            return
        if len(party["members"]) >= party["max_size"]:
            await interaction.response.send_message(
                embed=self._err(f"Your party is full ({party['max_size']}/{party['max_size']})."),
                ephemeral=True)
            return
        if member.bot:
            await interaction.response.send_message(
                embed=self._err("You can't invite a bot."), ephemeral=True)
            return
        if tid == uid:
            await interaction.response.send_message(
                embed=self._err("You're already in this party."), ephemeral=True)
            return
        if not self._has_character(tid, gid):
            await interaction.response.send_message(
                embed=self._err(f"{member.display_name} doesn't have a character yet."),
                ephemeral=True)
            return
        if self._member_party(gid, tid):
            await interaction.response.send_message(
                embed=self._err(f"{member.display_name} is already in a party."), ephemeral=True)
            return
        if tid in party["invites"]:
            await interaction.response.send_message(
                embed=self._err(f"{member.display_name} already has a pending invite."),
                ephemeral=True)
            return

        party["invites"].add(tid)

        invite_embed = discord.Embed(
            title="🛡️ Party invite",
            description=(
                f"{member.mention}, {interaction.user.display_name} invited you to their party "
                f"({len(party['members'])}/{party['max_size']})."
            ),
            color=var.COLOR_PARTY,
        )
        invite_embed.set_footer(text=f"Invite expires in {var.INVITE_TIMEOUT // 60} min · {var.SERVER_NAME}")
        await interaction.response.send_message(
            content=member.mention,
            embed=invite_embed,
            view=_InviteView(self, gid, party["party_id"], tid),
        )

    # ── /party leave ───────────────────────────────────────────────────────────

    @party.command(name="leave", description="Leave your current party.")
    async def party_leave(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if self.db.execute("SELECT 1 FROM dnd_active_runs WHERE user_id=? AND guild_id=?", (uid, gid)):
            await interaction.response.send_message(
                embed=discord.Embed(description="⚔️ You're on an active campaign — you can't leave your party mid-adventure.", color=0xe74c3c),
                ephemeral=True)
            return

        party = self._member_party(gid, uid)
        if party is None:
            await interaction.response.send_message(
                embed=self._err("You're not in a party."), ephemeral=True)
            return

        party["members"].remove(uid)
        party["invites"].discard(uid)

        if not party["members"]:
            # Last one out — clean up the empty party.
            self._parties.get(gid, {}).pop(party["party_id"], None)
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="You left — the party was empty and has disbanded.",
                    color=var.COLOR_INFO),
                ephemeral=True)
            return

        # No real leader: if the creator (the display label) left, relabel to a remaining member.
        if party["creator_uid"] == uid:
            new_uid = party["members"][0]
            party["creator_uid"] = new_uid
            new_member = interaction.guild.get_member(int(new_uid)) if interaction.guild else None
            party["creator_name"] = new_member.display_name if new_member else "A party"

        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"You left the party ({len(party['members'])}/{party['max_size']} remain).",
                color=var.COLOR_INFO),
            ephemeral=True)

    # ── /party status ─────────────────────────────────────────────────────────

    @party.command(name="status", description="Check your current party details.")
    async def party_status(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        party = self._member_party(gid, uid)
        if party is None:
            await interaction.response.send_message(
                embed=self._err("You're not in a party. Create one with `/party create` or join with `/party join`."),
                ephemeral=True)
            return

        vis_badge  = "🔒 Private" if party["visibility"] == "private" else "🔓 Public"
        run_status = f"⚔️ On campaign: `{party['active_run']}`" if party["active_run"] else "💤 Idle"

        member_lines = []
        for m_uid in party["members"]:
            crown  = " 👑" if m_uid == party["creator_uid"] else ""
            member = interaction.guild.get_member(int(m_uid)) if interaction.guild else None
            name   = member.display_name if member else m_uid
            member_lines.append(f"• {name}{crown}")

        embed = discord.Embed(
            title=f"🛡️ {party['creator_name']}'s Party",
            color=var.COLOR_PARTY,
        )
        embed.add_field(
            name=f"Members ({len(party['members'])}/{party['max_size']})",
            value="\n".join(member_lines),
            inline=False,
        )
        embed.add_field(name="Visibility", value=vis_badge, inline=True)
        embed.add_field(name="Status",     value=run_status, inline=True)
        embed.set_footer(text=var.SERVER_NAME)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PartiesCog(bot))
    log.info("✅ DND/Parties cog loaded")
