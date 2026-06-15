import asyncio
import importlib.util as _ilu
import json
import logging
import random
import re
import uuid
from datetime import date, datetime
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

_spec = _ilu.spec_from_file_location('dm_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

_cspec = _ilu.spec_from_file_location(
    'dm_char_vars', Path(__file__).parent.parent / 'character' / 'variables.py')
char_var = _ilu.module_from_spec(_cspec)
_cspec.loader.exec_module(char_var)

from forge_db import ForgeDB

log = logging.getLogger("launcher")

# ============================================================================
# DICE ENGINE
# ============================================================================

def roll_expr(expr: str) -> tuple[int, str]:
    """Parse '2d6+3', 'd20', '1d8' etc → (total, detail). Returns (0, 'error') on bad input."""
    expr = expr.strip().lower()
    if expr.startswith("d"):
        expr = "1" + expr
    m = re.match(r'^(\d+)d(\d+)([+-]\d+)?$', expr)
    if not m:
        return 0, "error"
    count  = int(m.group(1))
    sides  = int(m.group(2))
    bonus  = int(m.group(3)) if m.group(3) else 0
    rolls  = [random.randint(1, sides) for _ in range(max(1, count))]
    total  = max(1, sum(rolls) + bonus)
    detail = f"[{'+'.join(str(r) for r in rolls)}]{f'{bonus:+d}' if bonus else ''}"
    return total, detail


def _roll(expr: str) -> int:
    return roll_expr(expr)[0]

# ============================================================================
# MODALS
# ============================================================================

class KillDescriptionModal(discord.ui.Modal):
    def __init__(self, log_entry: dict, enemy_name: str):
        super().__init__(title="How do you finish them?")
        self._log_entry = log_entry
        self.flavor = discord.ui.TextInput(
            label=f"Killing blow on {enemy_name[:40]}",
            placeholder="I grab them by the collar and throw them off the bridge...",
            style=discord.TextStyle.paragraph,
            max_length=200,
            required=False,
        )
        self.add_item(self.flavor)

    async def on_submit(self, interaction: discord.Interaction):
        text = self.flavor.value.strip()
        self._log_entry["kill_flavor"] = text or None
        reply = f'*"{text}"*\n\nYour legend grows. 🗡️' if text else "A swift end. 🗡️"
        await interaction.response.send_message(reply, ephemeral=True)


class SkillFlavorModal(discord.ui.Modal):
    def __init__(self, view: "InteractionView", uid: str, skill: str):
        super().__init__(title=f"{skill.title()} Check")
        self._view = view
        self._uid  = uid
        self.flavor = discord.ui.TextInput(
            label="What do you do or say? (optional)",
            placeholder="I lean in and lower my voice...",
            style=discord.TextStyle.paragraph,
            max_length=200,
            required=False,
        )
        self.add_item(self.flavor)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("🎲 Rolling...", ephemeral=True)
        self._view.result = {
            "action": "skill",
            "uid":    self._uid,
            "flavor": self.flavor.value.strip() or None,
        }
        self._view._done.set()
        self._view.stop()

# ============================================================================
# VIEWS
# ============================================================================

class InitiativeRollView(discord.ui.View):
    """Each player clicks to roll their own initiative instead of an auto-roll."""

    def __init__(self, active_uids: list[str], name_map: dict[str, str],
                 cog: "DungeonMasterCog", gid: str):
        super().__init__(timeout=var.ROUND_TIMEOUT)
        self._active  = set(active_uids)
        self._names   = name_map
        self._cog     = cog
        self._gid     = gid
        self.rolls:   dict[str, tuple[int, int, int]] = {}  # uid → (d20, mod, total)
        self._done    = asyncio.Event()

    def build_embed(self) -> discord.Embed:
        lines = []
        for uid in self._active:
            name = self._names.get(uid, uid)
            if uid in self.rolls:
                d20, mod, total = self.rolls[uid]
                mod_txt = f" {mod:+d}" if mod != 0 else ""
                lines.append(f"✅ **{name}** — {d20}{mod_txt} = **{total}**")
            else:
                lines.append(f"⏳ **{name}** — *waiting...*")
        return discord.Embed(
            title="🎲 Initiative — Click to Roll!",
            description="\n".join(lines),
            color=var.COLOR_COMBAT,
        )

    @discord.ui.button(label="🎲 Roll Initiative!", style=discord.ButtonStyle.primary)
    async def roll_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        uid = str(interaction.user.id)
        if uid not in self._active:
            await interaction.response.send_message("You're not in this combat.", ephemeral=True)
            return
        if uid in self.rolls:
            await interaction.response.send_message("You already rolled!", ephemeral=True)
            return
        stats   = self._cog._get_char_combat_stats(uid, self._gid)
        dex_mod = stats["mods"]["dexterity"] if stats else 0
        d20     = random.randint(1, 20)
        total   = d20 + dex_mod
        self.rolls[uid] = (d20, dex_mod, total)
        if set(self.rolls.keys()) >= self._active:
            self._done.set()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


class TargetSelectView(discord.ui.View):
    """Second step of item use — pick which party member to target."""

    def __init__(self, combat_view: "CombatView", uid: str, item_id: str,
                 active_members: list[tuple[str, str]]):
        super().__init__(timeout=30)
        self._cv      = combat_view
        self._uid     = uid
        self._item_id = item_id

        options = [
            discord.SelectOption(
                label=f"{name}{' (you)' if m_uid == uid else ''}",
                value=m_uid,
            )
            for m_uid, name in active_members
        ]
        sel = discord.ui.Select(placeholder="Who gets the potion?", options=options)
        sel.callback = self._on_target
        self.add_item(sel)

    async def _on_target(self, interaction: discord.Interaction):
        target_uid = interaction.data["values"][0]
        self._cv.actions[self._uid] = {"action": "use_item", "item_id": self._item_id, "target_uid": target_uid}
        if all(v is not None for v in self._cv.actions.values()):
            self._cv._done.set()
        await interaction.response.edit_message(
            embed=discord.Embed(description="🧪 Item use locked in!", color=0x57F287), view=None)
        self.stop()


class CombatView(discord.ui.View):
    """One round of combat — each active participant picks an action."""

    def __init__(self, active_uids: list[str], cog: "DungeonMasterCog",
                 gid: str, participants: list[tuple[str, str]]):
        super().__init__(timeout=None)
        self.actions:      dict[str, str | dict | None] = {uid: None for uid in active_uids}
        self._done         = asyncio.Event()
        self._active_set   = set(active_uids)
        self._cog          = cog
        self._gid          = gid
        self._participants = participants

    async def _record(self, interaction: discord.Interaction, action: str):
        uid = str(interaction.user.id)
        if uid not in self.actions:
            await interaction.response.send_message("You're not in this combat.", ephemeral=True)
            return
        if self.actions[uid] is not None:
            await interaction.response.send_message(
                f"Already locked in: **{self.actions[uid] if isinstance(self.actions[uid], str) else 'item use'}**.",
                ephemeral=True)
            return
        self.actions[uid] = action
        await interaction.response.send_message(f"✅ **{action.title()}** locked in!", ephemeral=True)
        if all(v is not None for v in self.actions.values()):
            self._done.set()

    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.danger,     row=0)
    async def attack(self, i: discord.Interaction, _): await self._record(i, "attack")

    @discord.ui.button(label="🛡️ Dodge",  style=discord.ButtonStyle.secondary,  row=0)
    async def dodge(self, i: discord.Interaction, _): await self._record(i, "dodge")

    @discord.ui.button(label="🏃 Flee",   style=discord.ButtonStyle.primary,    row=0)
    async def flee(self, i: discord.Interaction, _): await self._record(i, "flee")

    @discord.ui.button(label="🧪 Item",   style=discord.ButtonStyle.secondary,  row=1)
    async def use_item(self, interaction: discord.Interaction, _: discord.ui.Button):
        uid = str(interaction.user.id)
        if uid not in self.actions:
            await interaction.response.send_message("You're not in this combat.", ephemeral=True)
            return
        if self.actions[uid] is not None:
            await interaction.response.send_message("You've already chosen your action.", ephemeral=True)
            return
        rows = self._cog.db.execute(
            "SELECT item_id, qty FROM dnd_inventory WHERE user_id=? AND guild_id=? AND qty>0",
            (uid, self._gid))
        all_items   = self._cog._all_char_items()
        consumables = [
            (iid, qty) for iid, qty in rows
            if next((i for i in all_items if i["id"] == iid and i.get("slot") == "consumable"), None)
        ]
        if not consumables:
            await interaction.response.send_message(
                "You have no usable items. (Buy potions from the shop!)", ephemeral=True)
            return
        options = []
        for iid, qty in consumables:
            item = next((i for i in all_items if i["id"] == iid), None)
            if item:
                options.append(discord.SelectOption(
                    label=f"{item['name']} ×{qty}",
                    description=f"Heals {item.get('heal_expr', '?')} HP",
                    value=iid,
                ))
        active_members = [(uid2, name) for uid2, name in self._participants if uid2 in self._active_set]
        view = _ItemPickView(self, uid, active_members, options)
        await interaction.response.send_message(
            embed=discord.Embed(description="🧪 Pick an item to use:", color=var.COLOR_INFO),
            view=view,
            ephemeral=True,
        )


class _ItemPickView(discord.ui.View):
    """Ephemeral first step: which consumable?"""

    def __init__(self, combat_view: CombatView, uid: str,
                 active_members: list[tuple[str, str]], options: list):
        super().__init__(timeout=30)
        self._cv             = combat_view
        self._uid            = uid
        self._active_members = active_members
        sel = discord.ui.Select(placeholder="Choose an item…", options=options)
        sel.callback = self._on_item
        self.add_item(sel)

    async def _on_item(self, interaction: discord.Interaction):
        item_id = interaction.data["values"][0]
        await interaction.response.edit_message(
            embed=discord.Embed(description="🧪 Who should receive it?", color=var.COLOR_INFO),
            view=TargetSelectView(self._cv, self._uid, item_id, self._active_members),
        )
        self.stop()


class InteractionView(discord.ui.View):
    """Skill check / interaction encounter — one player acts for the group."""

    def __init__(self, active_uids: list[str], encounter: dict):
        super().__init__(timeout=None)
        self.active_uids = set(active_uids)
        self.encounter   = encounter
        self.result: dict | None = None
        self._done = asyncio.Event()

        skill_btn = discord.ui.Button(
            label=encounter["skill_label"],
            style=discord.ButtonStyle.primary,
            row=0,
        )
        skill_btn.callback = self._skill_cb
        self.add_item(skill_btn)

        if encounter.get("combat_fallback"):
            fight_btn = discord.ui.Button(
                label="⚔️ Fight Instead",
                style=discord.ButtonStyle.danger,
                row=0,
            )
            fight_btn.callback = self._fight_cb
            self.add_item(fight_btn)

    async def _skill_cb(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        if uid not in self.active_uids:
            await interaction.response.send_message("You're not in this run.", ephemeral=True)
            return
        if self._done.is_set():
            await interaction.response.send_message("Already resolved.", ephemeral=True)
            return
        await interaction.response.send_modal(
            SkillFlavorModal(self, uid, self.encounter["skill"]))

    async def _fight_cb(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        if uid not in self.active_uids:
            await interaction.response.send_message("You're not in this run.", ephemeral=True)
            return
        if self._done.is_set():
            await interaction.response.send_message("Already resolved.", ephemeral=True)
            return
        await interaction.response.send_message("⚔️ Drawing weapons...", ephemeral=True)
        self.result = {"action": "fight", "uid": uid, "flavor": None}
        self._done.set()
        self.stop()


class KillConfirmView(discord.ui.View):
    """Non-blocking button that lets the killer describe the finishing move."""

    def __init__(self, killer_uid: str, enemy_name: str, log_entry: dict):
        super().__init__(timeout=var.KILL_MODAL_TIMEOUT)
        self.killer_uid = killer_uid
        self.enemy_name = enemy_name
        self.log_entry  = log_entry

    @discord.ui.button(label="🗡️ Describe the kill", style=discord.ButtonStyle.danger)
    async def describe(self, interaction: discord.Interaction, _: discord.ui.Button):
        if str(interaction.user.id) != self.killer_uid:
            await interaction.response.send_message(
                "Only the one who landed the killing blow can do this.", ephemeral=True)
            return
        await interaction.response.send_modal(
            KillDescriptionModal(self.log_entry, self.enemy_name))
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except Exception:
            pass


class WanderJoinView(discord.ui.View):
    """Public join window posted in the channel for party members."""

    def __init__(self, cog: "DungeonMasterCog", campaign: dict,
                 initiator_uid: str, initiator_name: str, party_members: list[str]):
        super().__init__(timeout=var.WANDER_JOIN_TIMEOUT)
        self.cog           = cog
        self.campaign      = campaign
        self.party_members = party_members
        self.joiners: list[tuple[str, str]] = [(initiator_uid, initiator_name)]
        self._joiner_set: set[str]          = {initiator_uid}
        self._all_joined   = asyncio.Event()
        # If the initiator is already the whole party, fire immediately
        if len(self._joiner_set) >= len(self.party_members):
            self._all_joined.set()

    def _build_embed(self) -> discord.Embed:
        c     = self.campaign
        max_p = c.get("max_players", 4)
        names = ", ".join(n for _, n in self.joiners)
        embed = discord.Embed(
            title=f"{c['emoji']} {c['name']}  —  {c['difficulty']}",
            description=(
                f"*{c['intro']}*\n\n"
                f"**Min level:** {c['min_level']}  ·  "
                f"**Players:** {c.get('min_players', 1)}–{max_p}  ·  "
                f"**Reward:** up to {c['reward_gold_max']:,} {var.CURRENCY_SYMBOL}  ·  {c['reward_xp']:,} XP\n\n"
                f"**Joining ({len(self.joiners)}/{max_p}):** {names}\n\n"
                f"⚔️ Click below to join! Window closes in **{var.WANDER_JOIN_TIMEOUT}s**."
            ),
            color=var.COLOR_CAMPAIGN,
        )
        embed.set_footer(text=var.SERVER_NAME)
        return embed

    @discord.ui.button(label="⚔️ Join the quest", style=discord.ButtonStyle.success)
    async def join_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        uid   = str(interaction.user.id)
        gid   = str(interaction.guild_id)
        max_p = self.campaign.get("max_players", 4)
        if uid not in self.party_members:
            await interaction.response.send_message("Only party members can join.", ephemeral=True)
            return
        if uid in self._joiner_set:
            await interaction.response.send_message("You're already joining!", ephemeral=True)
            return
        if len(self.joiners) >= max_p:
            await interaction.response.send_message(
                f"This campaign is full ({max_p}/{max_p} players).", ephemeral=True)
            return
        if self.cog._is_in_run(uid, gid):
            await interaction.response.send_message(
                "You're already in an active campaign run.", ephemeral=True)
            return
        self._joiner_set.add(uid)
        self.joiners.append((uid, interaction.user.display_name))
        await interaction.response.edit_message(embed=self._build_embed(), view=self)
        if self._joiner_set >= set(self.party_members):
            self._all_joined.set()


class CampaignSelectView(discord.ui.View):
    """Ephemeral select shown to the initiator for picking a campaign."""

    def __init__(self, cog: "DungeonMasterCog", uid: str, gid: str, campaigns: list[dict]):
        super().__init__(timeout=60)
        self._cog = cog
        self._uid = uid
        self._gid = gid
        self._map = {c["id"]: c for c in campaigns}

        options = [
            discord.SelectOption(
                label=f"{c['emoji']} {c['name']}",
                value=c["id"],
                description=(
                    f"{c['difficulty']} · Lv {c['min_level']}+ · "
                    f"👥 {c.get('min_players', 1)}-{c.get('max_players', 4)} · "
                    f"{c['reward_xp']} XP"
                ),
            )
            for c in campaigns
        ]
        sel = discord.ui.Select(placeholder="Choose a campaign…", options=options)
        sel.callback = self._on_select
        self.add_item(sel)

    async def _on_select(self, interaction: discord.Interaction):
        campaign = self._map[interaction.data["values"][0]]
        self.stop()
        await self._cog._start_wander(interaction, campaign, self._uid, self._gid)

# ============================================================================
# COG
# ============================================================================

class DungeonMasterCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot  = bot
        self.db   = ForgeDB.get()
        # in-memory run state: run_id → {gid, participants, player_hp, player_max_hp, fled, log}
        self._runs: dict[str, dict] = {}
        # DLC registries — populated by DND_DLC cogs via register_*
        self._extra_campaigns: list[dict] = []
        self._extra_races:     list[dict] = []
        self._extra_classes:   list[dict] = []

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
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS dnd_run_log (
                run_id        TEXT PRIMARY KEY,
                guild_id      TEXT NOT NULL,
                campaign_id   TEXT NOT NULL,
                campaign_name TEXT NOT NULL,
                participants  TEXT NOT NULL,
                success       INTEGER NOT NULL,
                log_json      TEXT NOT NULL,
                created_at    TEXT NOT NULL
            )
        """)

    # ── DLC registration (called from DND_DLC cog setup functions) ────────────

    def register_campaign(self, campaign: dict):
        self._extra_campaigns.append(campaign)
        log.info("DungeonMaster: registered DLC campaign '%s'", campaign.get("name"))

    def register_race(self, race: dict):
        self._extra_races.append(race)
        log.info("DungeonMaster: registered DLC race '%s'", race.get("name"))

    def register_class(self, klass: dict):
        self._extra_classes.append(klass)
        log.info("DungeonMaster: registered DLC class '%s'", klass.get("name"))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _all_char_items(self) -> list[dict]:
        char_cog = self.bot.cogs.get("CharacterCog")
        return char_var.ITEMS + (char_cog._extra_items if char_cog else [])

    def _find_item(self, item_id: str) -> dict | None:
        return next((i for i in self._all_char_items() if i["id"] == item_id), None)

    @staticmethod
    def _err(msg: str) -> discord.Embed:
        return discord.Embed(description=msg, color=var.COLOR_ERROR)

    def _parties_cog(self):
        return self.bot.cogs.get("PartiesCog")

    def _is_in_run(self, uid: str, gid: str) -> bool:
        return bool(self.db.execute(
            "SELECT 1 FROM dnd_active_runs WHERE user_id=? AND guild_id=?", (uid, gid)))

    def _claim_slot(self, uid: str, gid: str, run_id: str, campaign_id: str) -> bool:
        try:
            self.db.execute(
                "INSERT INTO dnd_active_runs (user_id, guild_id, run_id, campaign_id) VALUES (?,?,?,?)",
                (uid, gid, run_id, campaign_id))
            return True
        except Exception:
            return False

    def _add_to_run(self, uid: str, gid: str, run_id: str, campaign_id: str):
        self.db.execute(
            "INSERT OR IGNORE INTO dnd_active_runs (user_id, guild_id, run_id, campaign_id) VALUES (?,?,?,?)",
            (uid, gid, run_id, campaign_id))

    def _clear_run(self, run_id: str):
        self.db.execute("DELETE FROM dnd_active_runs WHERE run_id=?", (run_id,))

    def _available_campaigns(self, level: int) -> list[dict]:
        all_camps = var.CAMPAIGNS + self._extra_campaigns
        available = [c for c in all_camps if c["min_level"] <= level]
        if len(available) > var.MAX_SHOWN_CAMPAIGNS:
            # Daily rotation — same window all day, rotates at midnight
            seed   = int(date.today().toordinal()) % len(available)
            double = available + available
            available = double[seed: seed + var.MAX_SHOWN_CAMPAIGNS]
        return available

    def _fetch_char_basic(self, uid: str, gid: str) -> dict | None:
        rows = self.db.execute(
            "SELECT level, xp, name FROM dnd_characters WHERE user_id=? AND guild_id=?",
            (uid, gid))
        return {"level": rows[0][0], "xp": rows[0][1], "name": rows[0][2]} if rows else None

    def _get_char_combat_stats(self, uid: str, gid: str) -> dict | None:
        rows = self.db.execute(
            "SELECT strength, dexterity, constitution, intelligence, wisdom, charisma, "
            "level, char_class, race, hp "
            "FROM dnd_characters WHERE user_id=? AND guild_id=?",
            (uid, gid))
        if not rows:
            return None
        str_, dex, con, int_, wis, cha, level, char_class, race_id, current_hp = rows[0]

        race  = next((r for r in char_var.RACES  if r["id"] == race_id),    None)
        klass = next((c for c in char_var.CLASSES if c["id"] == char_class), None)

        # Apply racial modifiers
        rm = race["mods"] if race else {}
        finals = {
            "strength":     (str_ or 10) + rm.get("strength",     0),
            "dexterity":    (dex  or 10) + rm.get("dexterity",    0),
            "constitution": (con  or 10) + rm.get("constitution", 0),
            "intelligence": (int_ or 10) + rm.get("intelligence", 0),
            "wisdom":       (wis  or 10) + rm.get("wisdom",       0),
            "charisma":     (cha  or 10) + rm.get("charisma",     0),
        }
        mods = {ab: (v - 10) // 2 for ab, v in finals.items()}
        prof = 2 + (max(1, level or 1) - 1) // 4

        hit_die = klass["hit_die"] if klass else 6
        avg_gain = hit_die // 2 + 1
        max_hp = max(1, (hit_die + mods["constitution"])
                     + (max(1, level or 1) - 1) * (avg_gain + mods["constitution"]))
        ac = 10 + mods["dexterity"] + (klass.get("armor", 0) if klass else 0)

        # Equipped weapon
        weapon = self._get_equipped_weapon(uid, gid)
        if weapon:
            atk_ability = weapon.get("ability", "strength")
            dmg_expr    = weapon.get("damage", "1d6")
            atk_bonus   = mods[atk_ability] + prof
        else:
            atk_ability = "strength"
            dmg_expr    = "1d4"
            atk_bonus   = mods["strength"] + prof

        return {
            "mods":      mods,
            "prof":      prof,
            "ac":        ac,
            "max_hp":    max_hp,
            "current_hp": current_hp or max_hp,
            "atk_bonus": atk_bonus,
            "dmg_expr":  f"{dmg_expr}+{mods[atk_ability]}" if mods[atk_ability] >= 0
                         else f"{dmg_expr}{mods[atk_ability]}",
        }

    def _get_equipped_weapon(self, uid: str, gid: str) -> dict | None:
        rows = self.db.execute(
            "SELECT item_id FROM dnd_inventory WHERE user_id=? AND guild_id=? AND equipped=1",
            (uid, gid))
        if not rows:
            return None
        return self._find_item(rows[0][0])

    async def _drop_materials(self, channel: discord.TextChannel,
                              run: dict, gid: str, enemy: dict):
        drops = enemy.get("drops", [])
        if not drops:
            return
        alive_uids = {uid for uid, _ in run["participants"]
                      if uid not in run["fled"] and run["player_hp"].get(uid, 0) > 0}
        if not alive_uids:
            return
        drop_lines = []
        for uid, name in run["participants"]:
            if uid not in alive_uids:
                continue
            got = []
            for drop in drops:
                if random.randint(1, 100) <= drop["chance"]:
                    self.db.execute(
                        """INSERT INTO dnd_inventory (user_id, guild_id, item_id, qty, equipped)
                           VALUES (?,?,?,1,0)
                           ON CONFLICT(user_id,guild_id,item_id) DO UPDATE SET qty=qty+1""",
                        (uid, gid, drop["id"]))
                    item_data = self._find_item(drop["id"])
                    label = f"{item_data.get('emoji','📦')} {item_data['name']}" if item_data else drop["id"]
                    got.append(label)
            if got:
                drop_lines.append(f"• **{name}**: {', '.join(got)}")
        if drop_lines:
            await channel.send(embed=discord.Embed(
                title="🎒 Materials Found",
                description="\n".join(drop_lines),
                color=var.COLOR_WIN,
            ))

    def _give_rewards(self, uid: str, gid: str, display_name: str, gold: int, xp: int) -> int:
        self.db.ensure_user(uid, gid, display_name)
        if gold > 0:
            self.db.update_balance(uid, gid, gold, "campaign_reward")
        rows = self.db.execute(
            "SELECT level, xp FROM dnd_characters WHERE user_id=? AND guild_id=?", (uid, gid))
        if not rows:
            return 1
        current_level, current_xp = rows[0]
        new_xp    = (current_xp or 0) + xp
        new_level = current_level or 1
        while new_level < char_var.MAX_LEVEL and new_xp >= char_var.XP_THRESHOLDS[new_level + 1]:
            new_level += 1
        self.db.execute(
            "UPDATE dnd_characters SET xp=?, level=? WHERE user_id=? AND guild_id=?",
            (new_xp, new_level, uid, gid))
        return new_level

    def _save_run_log(self, run_id: str, gid: str, campaign: dict,
                      participants: list, success: bool, run_log: list):
        self.db.execute(
            """INSERT INTO dnd_run_log
               (run_id, guild_id, campaign_id, campaign_name, participants, success, log_json, created_at)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(run_id) DO NOTHING""",
            (run_id, gid, campaign["id"], campaign["name"],
             json.dumps([[uid, name] for uid, name in participants]),
             1 if success else 0,
             json.dumps(run_log),
             datetime.utcnow().isoformat()))

    # ── /roll ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="roll", description="Roll dice. Examples: d20 · 2d6 · 1d8+3")
    @app_commands.describe(dice="Dice expression (e.g. d20, 2d6, 1d8+3)")
    async def roll(self, interaction: discord.Interaction, dice: str):
        total, detail = roll_expr(dice)
        if detail == "error":
            await interaction.response.send_message(
                embed=self._err("Invalid expression. Try `d20`, `2d6`, `1d8+3`."),
                ephemeral=True)
            return
        embed = discord.Embed(
            title=f"🎲 {dice.upper()}",
            description=f"**{total}**\n`{detail}`",
            color=var.COLOR_INFO,
        )
        embed.set_footer(text=interaction.user.display_name)
        await interaction.response.send_message(embed=embed)

    # ── /wander ───────────────────────────────────────────────────────────────

    @app_commands.command(name="wander", description="Browse the quest board and set off on an adventure.")
    async def wander(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        char = self._fetch_char_basic(uid, gid)
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
                    f"No campaigns available at level {char['level']} yet. Level up to unlock harder bounties."),
                ephemeral=True)
            return

        embed = discord.Embed(
            title="🗺️ Quest Board",
            description=f"Campaigns available for **level {char['level']}**:",
            color=var.COLOR_CAMPAIGN,
        )
        await interaction.response.send_message(
            embed=embed,
            view=CampaignSelectView(self, uid, gid, available),
            ephemeral=True)

    # ── Campaign start ────────────────────────────────────────────────────────

    async def _start_wander(self, interaction: discord.Interaction,
                             campaign: dict, uid: str, gid: str):
        if self._is_in_run(uid, gid):
            await interaction.response.edit_message(
                embed=self._err("You just joined another run — can't start this one."), view=None)
            return

        parties_cog = self._parties_cog()
        party       = parties_cog._member_party(gid, uid) if parties_cog else None

        if party and party["active_run"] is not None:
            await interaction.response.edit_message(
                embed=self._err("Your party is already on a campaign."), view=None)
            return
        if party:
            party["active_run"] = "pending"

        run_id = uuid.uuid4().hex
        if not self._claim_slot(uid, gid, run_id, campaign["id"]):
            if party:
                party["active_run"] = None
            await interaction.response.edit_message(
                embed=self._err("Couldn't claim a run slot — you may already be in one."), view=None)
            return

        await interaction.response.edit_message(
            embed=discord.Embed(
                description=f"{campaign['emoji']} **{campaign['name']}** launched! Check the channel.",
                color=var.COLOR_CAMPAIGN),
            view=None)

        if party:
            join_view = WanderJoinView(
                cog=self,
                campaign=campaign,
                initiator_uid=uid,
                initiator_name=interaction.user.display_name,
                party_members=party["members"],
            )
            other_members = [m for m in party["members"] if m != uid]
            ping_content  = " ".join(f"<@{m}>" for m in other_members) if other_members else None
            join_msg = await interaction.channel.send(
                content=ping_content, embed=join_view._build_embed(), view=join_view)
            asyncio.create_task(
                self._run_campaign(interaction, campaign, party, run_id, join_view, join_msg))
        else:
            asyncio.create_task(
                self._run_campaign(
                    interaction, campaign, None, run_id, None, None,
                    solo=[(uid, interaction.user.display_name)]))

    # ── Campaign runner ───────────────────────────────────────────────────────

    async def _run_campaign(
        self,
        interaction: discord.Interaction,
        campaign:    dict,
        party,
        run_id:      str,
        join_view:   "WanderJoinView | None",
        join_msg:    "discord.Message | None",
        solo:        "list[tuple[str, str]] | None" = None,
    ):
        gid = str(interaction.guild_id)
        try:
            # Wait for party join window (closes early if everyone joins)
            if join_view is not None:
                try:
                    await asyncio.wait_for(join_view._all_joined.wait(), timeout=var.WANDER_JOIN_TIMEOUT)
                except asyncio.TimeoutError:
                    pass
                join_view.stop()
                for item in join_view.children:
                    item.disabled = True
                try:
                    await join_msg.edit(view=join_view)
                except Exception:
                    pass
                participants = join_view.joiners
                for p_uid, p_name in participants[1:]:
                    self._add_to_run(p_uid, gid, run_id, campaign["id"])
            else:
                participants = solo or []

            if party:
                party["active_run"] = campaign["id"]

            # Load combat HP for each participant
            run_state: dict = {
                "gid":         gid,
                "participants": participants,
                "player_hp":    {},
                "player_max_hp":{},
                "fled":         set(),
                "log":          [],
            }
            for uid, name in participants:
                stats = self._get_char_combat_stats(uid, gid)
                hp = stats["max_hp"] if stats else 10
                run_state["player_hp"][uid]     = hp
                run_state["player_max_hp"][uid]  = hp
            self._runs[run_id] = run_state

            # Intro
            names = ", ".join(f"**{n}**" for _, n in participants)
            intro = discord.Embed(
                title=f"{campaign['emoji']} {campaign['name']}",
                description=f"*{campaign['intro']}*\n\n**Adventurers:** {names}",
                color=var.COLOR_CAMPAIGN,
            )
            intro.set_footer(text=var.SERVER_NAME)
            await interaction.channel.send(embed=intro)
            await asyncio.sleep(2)

            # Run encounters
            success = True
            for encounter in campaign["encounters"]:
                if encounter["type"] == "combat":
                    result = await self._run_combat(interaction.channel, encounter, run_id)
                else:
                    result = await self._run_interaction(interaction.channel, encounter, run_id)

                if result in ("defeat", "all_fled"):
                    success = False
                    break

            # Final rewards
            run   = self._runs[run_id]
            alive = [(uid, name) for uid, name in participants
                     if uid not in run["fled"] and run["player_hp"].get(uid, 0) > 0]

            if success and alive:
                total_gold = random.randint(campaign["reward_gold_min"], campaign["reward_gold_max"])
                gold_each  = max(1, total_gold // max(1, len(alive)))
                xp_each    = campaign["reward_xp"]
                lines      = []
                for uid, name in alive:
                    lvl_rows  = self.db.execute(
                        "SELECT level FROM dnd_characters WHERE user_id=? AND guild_id=?", (uid, gid))
                    old_level = lvl_rows[0][0] if lvl_rows else 1
                    new_level = self._give_rewards(uid, gid, name, gold_each, xp_each)
                    lvl_up    = f"  🎉 **Level {new_level}!**" if new_level > old_level else ""
                    lines.append(
                        f"• **{name}** — +{gold_each:,} {var.CURRENCY_SYMBOL}  ·  +{xp_each:,} XP{lvl_up}")
                result_embed = discord.Embed(
                    title=f"✅ {campaign['name']} — Victory!",
                    description="\n".join(lines),
                    color=var.COLOR_WIN,
                )
            else:
                result_embed = discord.Embed(
                    title=f"❌ {campaign['name']} — Defeated!",
                    description=(
                        "The party was overwhelmed and forced to retreat.\n"
                        "*(No rewards — regroup and try again.)*"),
                    color=var.COLOR_ERROR,
                )

            result_embed.set_footer(text=var.SERVER_NAME)
            await interaction.channel.send(embed=result_embed)
            self._save_run_log(run_id, gid, campaign, participants, success, run["log"])

        finally:
            self._clear_run(run_id)
            self._runs.pop(run_id, None)
            if party:
                party["active_run"] = None

    # ── Combat encounter ──────────────────────────────────────────────────────

    async def _run_combat(self, channel: discord.TextChannel,
                          encounter: dict, run_id: str) -> str:
        run   = self._runs[run_id]
        gid   = run["gid"]
        enemy      = dict(encounter["enemy"])
        party_size = len(run["participants"])
        e_hp       = enemy["hp"] + (party_size - 1) * max(1, enemy["hp"] // 3)
        e_max      = e_hp
        rnd        = 0
        last_hitter = None
        kill_entry: dict = {}

        scale_note  = f" *(+{e_hp - enemy['hp']} for party)*" if party_size > 1 else ""
        intro_embed = discord.Embed(
            title=f"⚔️ {encounter['name']}",
            description=(
                f"*{encounter['intro']}*\n\n"
                f"{enemy['emoji']} **{enemy['name']}**  —  "
                f"HP **{e_hp}**{scale_note}  ·  AC **{enemy['ac']}**"
            ),
            color=var.COLOR_COMBAT,
        )
        await channel.send(embed=intro_embed)
        await asyncio.sleep(1)

        # ── Initiative — button roll, each player clicks ───────────────────────
        active_init  = [uid for uid, _ in run["participants"]
                        if uid not in run["fled"] and run["player_hp"].get(uid, 0) > 0]
        name_map     = {uid: name for uid, name in run["participants"]}
        init_view    = InitiativeRollView(active_init, name_map, self, gid)
        init_msg     = await channel.send(embed=init_view.build_embed(), view=init_view)
        try:
            await asyncio.wait_for(init_view._done.wait(), timeout=var.ROUND_TIMEOUT)
        except asyncio.TimeoutError:
            for uid in active_init:
                if uid not in init_view.rolls:
                    stats   = self._get_char_combat_stats(uid, gid)
                    dex_mod = stats["mods"]["dexterity"] if stats else 0
                    d20     = random.randint(1, 20)
                    init_view.rolls[uid] = (d20, dex_mod, d20 + dex_mod)
        for item in init_view.children:
            item.disabled = True

        # Enemy initiative
        enemy_init_bonus = enemy.get("initiative_bonus", 0)
        enemy_init_roll  = random.randint(1, 20)
        enemy_init_total = enemy_init_roll + enemy_init_bonus

        # Build sorted results
        init_rows: list[tuple[int, str]] = []
        player_inits: dict[str, int] = {}
        for uid in active_init:
            d20, mod, total = init_view.rolls.get(uid, (0, 0, 0))
            name = name_map.get(uid, uid)
            player_inits[uid] = total
            mod_txt = f" {mod:+d}" if mod != 0 else ""
            init_rows.append((total, f"🎲 **{name}** — {d20}{mod_txt} = **{total}**"))
        e_mod_txt = f" {enemy_init_bonus:+d}" if enemy_init_bonus != 0 else ""
        init_rows.append((enemy_init_total,
                          f"🐾 **{enemy['name']}** — {enemy_init_roll}{e_mod_txt} = **{enemy_init_total}**"))
        init_rows.sort(key=lambda x: x[0], reverse=True)

        best_player_init = max(player_inits.values(), default=0)
        enemy_first      = enemy_init_total > best_player_init
        order_txt        = (f"⚡ **{enemy['name']} acts first!**" if enemy_first
                            else "⚔️ **Players act first!**")
        final_init_embed = discord.Embed(
            title="🎲 Initiative Results",
            description="\n".join(line for _, line in init_rows) + f"\n\n{order_txt}",
            color=var.COLOR_COMBAT,
        )
        try:
            await init_msg.edit(embed=final_init_embed, view=init_view)
        except Exception:
            pass
        await asyncio.sleep(var.RESULT_DELAY)

        # ── Combat loop ────────────────────────────────────────────────────────
        while e_hp > 0:
            rnd += 1
            active = [uid for uid, _ in run["participants"]
                      if uid not in run["fled"] and run["player_hp"].get(uid, 0) > 0]
            if not active:
                return "defeat"

            # Enemy strikes first if it won initiative
            if enemy_first and e_hp > 0:
                non_fled = [uid for uid in active if uid not in run["fled"]]
                if non_fled:
                    t_uid  = random.choice(non_fled)
                    t_name = next((n for u, n in run["participants"] if u == t_uid), t_uid)
                    t_stat = self._get_char_combat_stats(t_uid, gid)
                    if t_stat:
                        e_roll = random.randint(1, 20)
                        e_tot  = e_roll + enemy["atk_bonus"]
                        if e_roll == 20 or e_tot >= t_stat["ac"]:
                            dmg = _roll(enemy["dmg"])
                            run["player_hp"][t_uid] = max(0, run["player_hp"][t_uid] - dmg)
                            crit_txt = " ✨ **CRIT!**" if e_roll == 20 else ""
                            ko_txt   = f"\n💀 **{t_name}** goes down before they can act!" \
                                       if run["player_hp"][t_uid] <= 0 else ""
                            pre_desc = (f"💥 **{enemy['name']}** strikes first!\n"
                                        f"Hits **{t_name}** → `{dmg}` dmg{crit_txt}{ko_txt}")
                            run["log"].append({
                                "type": "enemy_hit", "enemy": enemy["name"],
                                "target": t_uid, "target_name": t_name,
                                "dmg": dmg, "round": rnd, "initiative": True,
                            })
                        else:
                            pre_desc = (f"💨 **{enemy['name']}** lunges first at **{t_name}** — MISS!")
                        pre_embed = discord.Embed(
                            title=f"⚡ Round {rnd} — {enemy['name']} goes first!",
                            description=pre_desc,
                            color=var.COLOR_COMBAT,
                        )
                        await channel.send(embed=pre_embed)
                        await asyncio.sleep(1)

                # Refresh active after possible KO
                active = [uid for uid, _ in run["participants"]
                          if uid not in run["fled"] and run["player_hp"].get(uid, 0) > 0]
                if not active:
                    return "defeat"

            # HP bars + action buttons
            hp_lines = "\n".join(
                f"❤️ **{name}** — {run['player_hp'].get(uid, 0)}/{run['player_max_hp'].get(uid, 1)} HP"
                for uid, name in run["participants"] if uid in active
            )
            filled = int((e_hp / e_max) * 10)
            e_bar  = "█" * filled + "░" * (10 - filled)

            status = discord.Embed(
                title=f"⚔️ Round {rnd}  —  {enemy['name']}",
                description=(
                    f"{enemy['emoji']} **{enemy['name']}**\n"
                    f"HP: `{e_bar}` {e_hp}/{e_max}\n\n"
                    f"{hp_lines}"
                ),
                color=var.COLOR_COMBAT,
            )
            status.set_footer(text=f"⏱️ {var.ROUND_TIMEOUT}s — choose ⚔️ Attack · 🛡️ Dodge · 🏃 Flee · 🧪 Item")

            view = CombatView(active, self, gid, run["participants"])
            msg  = await channel.send(embed=status, view=view)

            try:
                await asyncio.wait_for(view._done.wait(), timeout=var.ROUND_TIMEOUT)
            except asyncio.TimeoutError:
                for uid in list(view.actions):
                    if view.actions[uid] is None:
                        view.actions[uid] = "dodge"

            for item in view.children:
                item.disabled = True
            try:
                await msg.edit(view=view)
            except Exception:
                pass

            round_lines = []
            dodgers: set[str] = set()

            # Process each player's action
            for uid, name in run["participants"]:
                if uid not in active:
                    continue
                action = view.actions.get(uid, "dodge")

                if action == "flee":
                    run["fled"].add(uid)
                    round_lines.append(f"🏃 **{name}** flees the battle!")
                    run["log"].append({"type": "flee", "uid": uid, "name": name, "round": rnd})

                elif action == "dodge":
                    dodgers.add(uid)
                    round_lines.append(f"🛡️ **{name}** takes a defensive stance.")

                elif isinstance(action, dict) and action.get("action") == "use_item":
                    item_id    = action["item_id"]
                    target_uid = action["target_uid"]
                    item       = self._find_item(item_id)
                    if item and item.get("heal_expr") and target_uid in run["player_hp"]:
                        heal       = _roll(item["heal_expr"])
                        max_hp     = run["player_max_hp"].get(target_uid, 999)
                        old_hp     = run["player_hp"].get(target_uid, 0)
                        actual     = min(max_hp, old_hp + heal) - old_hp
                        run["player_hp"][target_uid] = old_hp + actual
                        t_name     = next((n for u, n in run["participants"] if u == target_uid), target_uid)
                        self.db.execute(
                            "UPDATE dnd_inventory SET qty=qty-1 WHERE user_id=? AND guild_id=? AND item_id=?",
                            (uid, gid, item_id))
                        self.db.execute(
                            "DELETE FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id=? AND qty<=0",
                            (uid, gid, item_id))
                        target_txt = "themselves" if target_uid == uid else f"**{t_name}**"
                        round_lines.append(
                            f"🧪 **{name}** uses a {item['name']} on {target_txt} → +{actual} HP")
                        run["log"].append({
                            "type": "item_use", "uid": uid, "name": name,
                            "item": item_id, "target": target_uid, "heal": actual, "round": rnd,
                        })

                elif action == "attack":
                    stats = self._get_char_combat_stats(uid, gid)
                    if stats:
                        roll  = random.randint(1, 20)
                        total = roll + stats["atk_bonus"]
                        crit  = roll == 20
                        if crit or total >= enemy["ac"]:
                            dmg1 = _roll(stats["dmg_expr"])
                            if crit:
                                dmg2 = _roll(stats["dmg_expr"])
                                dmg  = dmg1 + dmg2
                            else:
                                dmg  = dmg1
                            e_hp = max(0, e_hp - dmg)
                            last_hitter = (uid, name)
                            bonus_txt = f"{stats['atk_bonus']:+d}"
                            if crit:
                                round_lines.append(
                                    f"⚔️ **{name}** ✨ **CRIT!** — {dmg1} + {dmg2} = **{dmg} dmg**")
                            else:
                                round_lines.append(
                                    f"⚔️ **{name}** rolled {roll} {bonus_txt} = **{total}** vs AC {enemy['ac']} → {dmg} dmg")
                            run["log"].append({
                                "type": "attack", "uid": uid, "name": name,
                                "roll": roll, "total": total, "dmg": dmg,
                                "hit": True, "crit": crit, "round": rnd, "enemy": enemy["name"],
                            })
                        else:
                            bonus_txt = f"{stats['atk_bonus']:+d}"
                            round_lines.append(
                                f"⚔️ **{name}** rolled {roll} {bonus_txt} = **{total}** vs AC {enemy['ac']} → MISS")
                            run["log"].append({
                                "type": "attack", "uid": uid, "name": name,
                                "roll": roll, "total": total, "dmg": 0,
                                "hit": False, "crit": False, "round": rnd, "enemy": enemy["name"],
                            })
                    else:
                        round_lines.append(f"⚔️ **{name}** swings wildly and misses!")

                    if e_hp <= 0:
                        break

            # Enemy retaliates only when players went first
            if not enemy_first and e_hp > 0:
                non_fled = [uid for uid in active if uid not in run["fled"]]
                if non_fled:
                    target_uid  = random.choice(non_fled)
                    target_name = next((n for u, n in run["participants"] if u == target_uid), target_uid)
                    stats       = self._get_char_combat_stats(target_uid, gid)
                    if stats:
                        roll      = random.randint(1, 20)
                        total_atk = roll + enemy["atk_bonus"]
                        dodge_ac  = stats["ac"] + (2 if target_uid in dodgers else 0)
                        if roll == 20 or total_atk >= dodge_ac:
                            dmg1 = _roll(enemy["dmg"])
                            if roll == 20:
                                dmg2 = _roll(enemy["dmg"])
                                dmg  = dmg1 + dmg2
                            else:
                                dmg  = dmg1
                            if target_uid in dodgers:
                                dmg = max(1, dmg // 2)
                            run["player_hp"][target_uid] = max(0, run["player_hp"][target_uid] - dmg)
                            dodge_txt = " *(half dmg — dodged)*" if target_uid in dodgers else ""
                            if roll == 20:
                                round_lines.append(
                                    f"💥 **{enemy['name']}** ✨ **CRIT!** on **{target_name}** — {dmg1} + {dmg2} = **{dmg} dmg**{dodge_txt}")
                            else:
                                round_lines.append(
                                    f"💥 **{enemy['name']}** hits **{target_name}** → {dmg} dmg{dodge_txt}")
                            run["log"].append({
                                "type": "enemy_hit", "enemy": enemy["name"],
                                "target": target_uid, "target_name": target_name,
                                "dmg": dmg, "round": rnd,
                            })
                            if run["player_hp"][target_uid] <= 0:
                                round_lines.append(f"💀 **{target_name}** goes down!")
                        else:
                            round_lines.append(f"💨 **{enemy['name']}** attacks **{target_name}** — MISS!")

            # Round result
            still_active = [uid for uid, _ in run["participants"]
                            if uid not in run["fled"] and run["player_hp"].get(uid, 0) > 0]
            color = var.COLOR_WIN if e_hp <= 0 else var.COLOR_COMBAT

            result_embed = discord.Embed(
                title=f"Round {rnd} — Results",
                description="\n".join(round_lines) or "*(nothing happened)*",
                color=color,
            )
            await channel.send(embed=result_embed)

            if e_hp <= 0:
                if last_hitter:
                    kill_entry = {
                        "type": "kill", "uid": last_hitter[0], "name": last_hitter[1],
                        "enemy": enemy["name"], "kill_flavor": None,
                    }
                    run["log"].append(kill_entry)
                    async with channel.typing():
                        await asyncio.sleep(1.5)
                    await channel.send(
                        f"<@{last_hitter[0]}> delivers the killing blow on **{enemy['name']}**!",
                        view=KillConfirmView(last_hitter[0], enemy["name"], kill_entry),
                    )
                await self._drop_materials(channel, run, gid, enemy)
                await asyncio.sleep(2)
                return "victory"

            if not still_active:
                if all(uid in run["fled"] for uid, _ in run["participants"]):
                    return "all_fled"
                return "defeat"

            await asyncio.sleep(var.RESULT_DELAY)

        return "victory"

    # ── Interaction encounter ─────────────────────────────────────────────────

    async def _run_interaction(self, channel: discord.TextChannel,
                                encounter: dict, run_id: str) -> str:
        run    = self._runs[run_id]
        gid    = run["gid"]
        active = [uid for uid, _ in run["participants"]
                  if uid not in run["fled"] and run["player_hp"].get(uid, 0) > 0]
        if not active:
            return "defeat"

        embed = discord.Embed(
            title=f"💬 {encounter['name']}",
            description=f"*{encounter['intro']}*",
            color=var.COLOR_INTERACTION,
        )
        embed.set_footer(text=f"⏱️ {var.INTERACTION_TIMEOUT}s to decide")

        view = InteractionView(active, encounter)
        msg  = await channel.send(embed=embed, view=view)

        try:
            await asyncio.wait_for(view._done.wait(), timeout=var.INTERACTION_TIMEOUT)
        except asyncio.TimeoutError:
            view.result = {"action": "timeout", "uid": active[0], "flavor": None}

        for item in view.children:
            item.disabled = True
        try:
            await msg.edit(view=view)
        except Exception:
            pass

        result = view.result or {"action": "timeout", "uid": active[0], "flavor": None}

        # Fight branch
        if result["action"] == "fight":
            fallback = encounter.get("combat_fallback")
            if fallback:
                fight_enc = {
                    "type":  "combat",
                    "name":  encounter["name"],
                    "intro": "You draw your weapons!",
                    "enemy": fallback,
                }
                run["log"].append({"type": "interaction_fight", "encounter": encounter["name"]})
                return await self._run_combat(channel, fight_enc, run_id)
            return "victory"

        # Skill check branch
        roller_uid  = result.get("uid") or active[0]
        flavor      = result.get("flavor")
        roller_name = next((n for u, n in run["participants"] if u == roller_uid), roller_uid)
        stats       = self._get_char_combat_stats(roller_uid, gid)
        skill       = encounter["skill"]
        mod         = stats["mods"][skill] if stats else 0
        roll        = random.randint(1, 20)
        total       = roll + mod
        dc          = encounter["dc"]
        success     = total >= dc

        flavor_line = f'\n*"{flavor}"*\n' if flavor else ""
        desc_lines  = [
            f"**{roller_name}** attempts a **{skill.title()}** check!",
            flavor_line,
            f"🎲 Rolled **{roll}** {mod:+d} = **{total}** vs DC **{dc}**",
            "",
        ]

        async with channel.typing():
            await asyncio.sleep(2)

        if success:
            desc_lines.append(f"✅ **Success!**  {encounter['success_text']}")
            run["log"].append({
                "type": "skill_success", "uid": roller_uid, "name": roller_name,
                "skill": skill, "roll": roll, "total": total, "dc": dc,
                "flavor": flavor, "encounter": encounter["name"],
            })
            res_embed = discord.Embed(
                title=f"✅ {encounter['name']} — Success",
                description="\n".join(desc_lines),
                color=var.COLOR_WIN,
            )
            await channel.send(embed=res_embed)
            await asyncio.sleep(2)
            return "victory"

        else:
            desc_lines.append(f"❌ **Failed.**  {encounter['failure_text']}")
            run["log"].append({
                "type": "skill_fail", "uid": roller_uid, "name": roller_name,
                "skill": skill, "roll": roll, "total": total, "dc": dc,
                "flavor": flavor, "encounter": encounter["name"],
            })
            res_embed = discord.Embed(
                title=f"❌ {encounter['name']} — Failed",
                description="\n".join(desc_lines),
                color=var.COLOR_ERROR,
            )
            await channel.send(embed=res_embed)
            await asyncio.sleep(2)

            fallback = encounter.get("combat_fallback")
            if fallback:
                fight_enc = {
                    "type":  "combat",
                    "name":  encounter["name"],
                    "intro": "The situation erupts into violence!",
                    "enemy": fallback,
                }
                return await self._run_combat(channel, fight_enc, run_id)
            return "victory"  # no fallback — failure is narrative only, run continues


async def setup(bot: commands.Bot):
    await bot.add_cog(DungeonMasterCog(bot))
    log.info("✅ DND/DungeonMaster cog loaded")
