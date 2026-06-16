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


def _n_attacks(char_class: str, level: int) -> int:
    """Extra Attack: Fighter Lv5=2/11=3/20=4; Barbarian/Ranger/Paladin Lv5=2."""
    if char_class == "fighter":
        if level >= 20: return 4
        if level >= 11: return 3
        if level >= 5:  return 2
    elif char_class in ("barbarian", "ranger", "paladin"):
        if level >= 5: return 2
    return 1


def _get_subclass(db, uid: str, gid: str, char_class: str) -> str | None:
    rows = db.execute(
        "SELECT choice_val FROM dnd_character_choices "
        "WHERE user_id=? AND guild_id=? AND choice_key=?",
        (uid, gid, f"{char_class}_subclass"))
    return rows[0][0] if rows else None


def _get_fighting_style(db, uid: str, gid: str, char_class: str = "fighter") -> str | None:
    rows = db.execute(
        "SELECT choice_val FROM dnd_character_choices "
        "WHERE user_id=? AND guild_id=? AND choice_key=?",
        (uid, gid, f"{char_class}_fighting_style"))
    return rows[0][0] if rows else None


def _get_human_feat(db, uid: str, gid: str) -> str | None:
    rows = db.execute(
        "SELECT choice_val FROM dnd_character_choices "
        "WHERE user_id=? AND guild_id=? AND choice_key=?",
        (uid, gid, "human_feat"))
    return rows[0][0] if rows else None


def _get_dwarf_trait(db, uid: str, gid: str) -> str | None:
    rows = db.execute(
        "SELECT choice_val FROM dnd_character_choices "
        "WHERE user_id=? AND guild_id=? AND choice_key=?",
        (uid, gid, "dwarf_trait"))
    return rows[0][0] if rows else None


def _get_favored_enemy(db, uid: str, gid: str) -> str | None:
    rows = db.execute(
        "SELECT choice_val FROM dnd_character_choices "
        "WHERE user_id=? AND guild_id=? AND choice_key=?",
        (uid, gid, "ranger_favored_enemy"))
    return rows[0][0] if rows else None


def _grant_wolf_if_needed(db, uid: str, gid: str) -> None:
    """Give a wolf_companion to a new Beast Master if they own no companion at all."""
    companion_ids = ["baby_dragon_companion", "bear_companion", "eagle_companion", "wolf_companion"]
    for cid in companion_ids:
        rows = db.execute(
            "SELECT qty FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id=? AND qty>0",
            (uid, gid, cid))
        if rows:
            return  # already has a companion
    db.execute(
        "INSERT OR IGNORE INTO dnd_inventory (user_id, guild_id, item_id, qty, equipped) VALUES (?,?,?,1,0)",
        (uid, gid, "wolf_companion"))


def _get_elf_subrace(db, uid: str, gid: str) -> str | None:
    rows = db.execute(
        "SELECT choice_val FROM dnd_character_choices "
        "WHERE user_id=? AND guild_id=? AND choice_key=?",
        (uid, gid, "elf_subrace"))
    return rows[0][0] if rows else None


def _get_wizard_known_spells(db, uid: str, gid: str) -> list[str]:
    rows = db.execute(
        "SELECT choice_val FROM dnd_character_choices "
        "WHERE user_id=? AND guild_id=? AND choice_key=?",
        (uid, gid, "wizard_known_spells"))
    if rows and rows[0][0]:
        return [s for s in rows[0][0].split(",") if s]
    return []


def _get_wizard_prepared_spells(db, uid: str, gid: str) -> list[str]:
    rows = db.execute(
        "SELECT choice_val FROM dnd_character_choices "
        "WHERE user_id=? AND guild_id=? AND choice_key=?",
        (uid, gid, "wizard_prepared_spells"))
    if rows and rows[0][0]:
        return [s for s in rows[0][0].split(",") if s]
    return []


def _is_help_used(db, uid: str, gid: str) -> bool:
    rows = db.execute(
        "SELECT 1 FROM dnd_character_choices "
        "WHERE user_id=? AND guild_id=? AND choice_key=?",
        (uid, gid, "help_long_rest_used"))
    return bool(rows)


def _set_help_used(db, uid: str, gid: str):
    db.execute(
        "INSERT OR REPLACE INTO dnd_character_choices "
        "(user_id, guild_id, choice_key, choice_val) VALUES (?,?,?,?)",
        (uid, gid, "help_long_rest_used", "1"))


_FAVORED_ENEMY_KEYWORDS: dict[str, list[str]] = {
    "humanoid": ["goblin", "bandit", "guard", "scout", "lieutenant", "chief", "soldier", "cultist"],
    "undead":   ["skeleton", "ghost", "spirit", "lich", "restless", "zombie", "wraith", "vampire"],
    "beast":    ["spider", "hound", "wolf", "bear", "rat", "serpent", "shadow hound"],
    "dragon":   ["dragon", "drake", "wyrm", "wyvern"],
    "fiend":    ["devil", "demon", "imp", "fiend", "infernal"],
}


def _enemy_matches_type(enemy_name: str, enemy_type: str) -> bool:
    name_lower = enemy_name.lower()
    return any(kw in name_lower for kw in _FAVORED_ENEMY_KEYWORDS.get(enemy_type, []))


def _sup_die_roll(die_type: str) -> int:
    sides = int(die_type.split("d")[1])
    return random.randint(1, sides)


def _roll_gwf(expr: str) -> int:
    """Roll damage for Great Weapon Fighting — reroll 1s and 2s once per die."""
    expr = expr.strip().lower()
    if expr.startswith("d"):
        expr = "1" + expr
    m = re.match(r'^(\d+)d(\d+)([+-]\d+)?$', expr)
    if not m:
        return max(1, _roll(expr))
    count = int(m.group(1))
    sides = int(m.group(2))
    bonus = int(m.group(3)) if m.group(3) else 0
    total = bonus
    for _ in range(max(1, count)):
        r = random.randint(1, sides)
        if r <= 2:
            r = random.randint(1, sides)
        total += r
    return max(1, total)


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
        stats    = self._cog._get_char_combat_stats(uid, self._gid)
        dex_mod  = stats["mods"]["dexterity"] if stats else 0
        feat     = _get_human_feat(self._cog.db, uid, self._gid)
        init_mod = dex_mod + (5 if feat == "alert" else 0)
        d20      = random.randint(1, 20)
        total    = d20 + init_mod
        self.rolls[uid] = (d20, init_mod, total)
        if set(self.rolls.keys()) >= self._active:
            self._done.set()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


class TargetSelectView(discord.ui.View):
    """Second step of item use — pick which party member to target."""

    def __init__(self, combat_view: "CombatView", uid: str, item_id: str,
                 active_members: list[tuple[str, str]], is_bonus: bool = False):
        super().__init__(timeout=30)
        self._cv       = combat_view
        self._uid      = uid
        self._item_id  = item_id
        self._is_bonus = is_bonus

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
        payload = {"action": "use_item", "item_id": self._item_id, "target_uid": target_uid}
        if self._is_bonus:
            self._cv.bonus_actions[self._uid] = payload
        else:
            self._cv.actions[self._uid] = payload
            if all(v is not None for v in self._cv.actions.values()):
                self._cv._done.set()
        await interaction.response.edit_message(
            embed=discord.Embed(description="🧪 Item use locked in!", color=0x57F287), view=None)
        self.stop()


class EnemyTargetView(discord.ui.View):
    """Ephemeral enemy target picker shown when ⚔️ Attack is clicked with multiple live enemies."""

    def __init__(self, combat_view: "CombatView", uid: str,
                 enemies: list[dict], run: dict):
        super().__init__(timeout=30)
        self._cv  = combat_view
        self._uid = uid

        options = [
            discord.SelectOption(
                label=f"{run.get('combat_enemy_base', {}).get('emoji', '⚔️')} {e['name']} ({e['hp']}/{e['max_hp']} HP)",
                value=str(e["idx"]),
            )
            for e in enemies if e["hp"] > 0
        ]
        sel = discord.ui.Select(placeholder="Which enemy do you attack?", options=options)
        sel.callback = self._on_target
        self.add_item(sel)

    async def _on_target(self, interaction: discord.Interaction):
        tidx = int(interaction.data["values"][0])
        self._cv.actions[self._uid]       = {"action": "attack", "target_idx": tidx}
        self._cv.enemy_targets[self._uid] = tidx
        if all(v is not None for v in self._cv.actions.values()):
            self._cv._done.set()
        await interaction.response.edit_message(
            embed=discord.Embed(description="⚔️ Target locked in!", color=0x57F287), view=None)
        self.stop()


class CombatView(discord.ui.View):
    """One round of combat — main action required; bonus action optional."""

    def __init__(self, active_uids: list[str], cog: "DungeonMasterCog",
                 gid: str, participants: list[tuple[str, str]], run: dict,
                 enemies: list[dict] | None = None):
        super().__init__(timeout=None)
        self.actions:       dict[str, str | dict | None] = {uid: None for uid in active_uids}
        self.bonus_actions: dict[str, dict | None]       = {uid: None for uid in active_uids}
        self.enemy_targets: dict[str, int]               = {uid: 0   for uid in active_uids}
        self._done         = asyncio.Event()
        self._active_set   = set(active_uids)
        self._cog          = cog
        self._gid          = gid
        self._participants = participants
        self._run          = run
        self._enemies      = enemies or []

    def _check_done(self):
        if all(v is not None for v in self.actions.values()):
            self._done.set()

    async def _record(self, interaction: discord.Interaction, action):
        uid = str(interaction.user.id)
        if uid not in self.actions:
            await interaction.response.send_message("You're not in this combat.", ephemeral=True)
            return
        if self.actions[uid] is not None:
            label = self.actions[uid] if isinstance(self.actions[uid], str) else "chosen"
            await interaction.response.send_message(f"Main action already locked in: **{label}**.", ephemeral=True)
            return
        self.actions[uid] = action
        label = action if isinstance(action, str) else action.get("action", "action")
        await interaction.response.send_message(f"✅ **{label.replace('_', ' ').title()}** locked in!", ephemeral=True)
        self._check_done()

    @discord.ui.button(label="⚔️ Attack", style=discord.ButtonStyle.danger,    row=0)
    async def attack(self, interaction: discord.Interaction, _: discord.ui.Button):
        uid = str(interaction.user.id)
        if uid not in self.actions:
            await interaction.response.send_message("You're not in this combat.", ephemeral=True)
            return
        if self.actions[uid] is not None:
            await interaction.response.send_message("Main action already locked in.", ephemeral=True)
            return
        alive_enemies = [e for e in self._enemies if e["hp"] > 0]
        if len(alive_enemies) > 1:
            await interaction.response.send_message(
                embed=discord.Embed(description="⚔️ Choose your target:", color=var.COLOR_COMBAT),
                view=EnemyTargetView(self, uid, alive_enemies, self._run),
                ephemeral=True)
        else:
            tidx = alive_enemies[0]["idx"] if alive_enemies else 0
            self.actions[uid]       = {"action": "attack", "target_idx": tidx}
            self.enemy_targets[uid] = tidx
            await interaction.response.send_message("⚔️ **Attack** locked in!", ephemeral=True)
            self._check_done()

    @discord.ui.button(label="🛡️ Dodge",  style=discord.ButtonStyle.secondary, row=0)
    async def dodge(self, i: discord.Interaction, _): await self._record(i, "dodge")

    @discord.ui.button(label="🏃 Flee",   style=discord.ButtonStyle.primary,   row=0)
    async def flee(self, i: discord.Interaction, _): await self._record(i, "flee")

    @discord.ui.button(label="🤝 Help",   style=discord.ButtonStyle.secondary, row=0)
    async def help_action(self, interaction: discord.Interaction, _: discord.ui.Button):
        uid = str(interaction.user.id)
        if uid not in self.actions:
            await interaction.response.send_message("You're not in this combat.", ephemeral=True)
            return
        if self.actions[uid] is not None:
            await interaction.response.send_message("Main action already chosen.", ephemeral=True)
            return
        if _is_help_used(self._cog.db, uid, self._gid):
            await interaction.response.send_message(
                "🤝 Help already used this long rest — use `/rest` to recover it.", ephemeral=True)
            return
        targets = [(u, n) for u, n in self._participants
                   if u != uid and u not in self._run.get("dead", set())]
        if not targets:
            await interaction.response.send_message("No allies to help.", ephemeral=True)
            return
        await interaction.response.send_message(
            embed=discord.Embed(description="🤝 Who do you help?", color=var.COLOR_INFO),
            view=_HelpTargetView(self, uid, targets, self._run),
            ephemeral=True)

    @discord.ui.button(label="⚡ Class Action", style=discord.ButtonStyle.success,   row=1)
    async def use_class_action(self, interaction: discord.Interaction, _: discord.ui.Button):
        uid = str(interaction.user.id)
        if uid not in self.actions:
            await interaction.response.send_message("You're not in this combat.", ephemeral=True)
            return
        if self.actions[uid] is not None:
            await interaction.response.send_message("Main action already chosen.", ephemeral=True)
            return
        rows = self._cog.db.execute(
            "SELECT char_class, level FROM dnd_characters WHERE user_id=? AND guild_id=?",
            (uid, self._gid))
        if not rows or not rows[0][0]:
            await interaction.response.send_message("You don't have a class set.", ephemeral=True)
            return
        char_class, level = rows[0]
        used       = self._run.get("features_used", {}).get(uid, set())
        surge_left = self._run.get("action_surge_uses", {}).get(uid, 0)
        available  = [
            f for f in char_var.COMBAT_FEATURES.get(char_class, [])
            if f.get("action_type") == "action"
            and f["level_req"] <= (level or 1)
            and (
                f["once_per"] != "combat"
                or (f["id"] == "action_surge" and surge_left > 0)
                or (f["id"] != "action_surge" and f["id"] not in used)
            )
        ]
        # Wizard: only show cantrips + prepared spells
        if char_class == "wizard":
            _wiz_prep    = self._run.get("wizard_prepared", {}).get(uid, [])
            _wiz_cantrips = char_var.WIZARD_CANTRIPS
            available    = [f for f in available
                            if f["id"] in _wiz_cantrips or f["id"] in _wiz_prep]
        # Include subclass action features (e.g. EK Fire Bolt)
        sc_rows2 = self._cog.db.execute(
            "SELECT choice_val FROM dnd_character_choices "
            "WHERE user_id=? AND guild_id=? AND choice_key=?",
            (uid, self._gid, f"{char_class}_subclass"))
        sc = sc_rows2[0][0] if sc_rows2 else None
        if sc:
            available += [
                f for f in char_var.SUBCLASS_COMBAT_FEATURES.get(sc, [])
                if f.get("action_type") == "action"
                and f["level_req"] <= (level or 1)
                and (f["once_per"] != "combat" or f["id"] not in used)
            ]
        if not available:
            await interaction.response.send_message(
                "No class actions available at your level / all used.", ephemeral=True)
            return
        active_members = [(u, n) for u, n in self._participants if u in self._active_set]
        await interaction.response.send_message(
            embed=discord.Embed(description="⚡ Choose a class action:", color=var.COLOR_INFO),
            view=_FeaturePickView(self, uid, available, active_members),
            ephemeral=True)

    @discord.ui.button(label="✨ Bonus Action", style=discord.ButtonStyle.secondary, row=1)
    async def use_bonus_action(self, interaction: discord.Interaction, _: discord.ui.Button):
        uid = str(interaction.user.id)
        if uid not in self.bonus_actions:
            await interaction.response.send_message("You're not in this combat.", ephemeral=True)
            return
        if self.bonus_actions[uid] is not None:
            await interaction.response.send_message("Bonus action already chosen.", ephemeral=True)
            return
        rows = self._cog.db.execute(
            "SELECT char_class, level FROM dnd_characters WHERE user_id=? AND guild_id=?",
            (uid, self._gid))
        if not rows or not rows[0][0]:
            await interaction.response.send_message("You don't have a class set.", ephemeral=True)
            return
        char_class, level = rows[0]
        used = self._run.get("features_used", {}).get(uid, set())
        available = [
            f for f in char_var.COMBAT_FEATURES.get(char_class, [])
            if f.get("action_type") == "bonus"
            and f["level_req"] <= (level or 1)
            and (f["once_per"] != "combat" or f["id"] not in used)
        ]
        # Wizard: only show prepared bonus spells (no cantrips are bonus actions)
        if char_class == "wizard":
            _wiz_prep_b   = self._run.get("wizard_prepared", {}).get(uid, [])
            _wiz_cants_b  = char_var.WIZARD_CANTRIPS
            available     = [f for f in available
                             if f["id"] in _wiz_cants_b or f["id"] in _wiz_prep_b]
        sc_rows = self._cog.db.execute(
            "SELECT choice_val FROM dnd_character_choices "
            "WHERE user_id=? AND guild_id=? AND choice_key=?",
            (uid, self._gid, f"{char_class}_subclass"))
        sc = sc_rows[0][0] if sc_rows else None
        _bm_ids    = {"bm_precision", "bm_trip", "bm_disarm", "bm_riposte", "bm_menacing"}
        _sup_left  = self._run.get("sup_dice", {}).get(uid, 0)
        if sc:
            sc_feats = [
                f for f in char_var.SUBCLASS_COMBAT_FEATURES.get(sc, [])
                if f.get("action_type") == "bonus"
                and f["level_req"] <= (level or 1)
                and (f["once_per"] != "combat" or f["id"] not in used)
                and not (f["id"] in _bm_ids and _sup_left == 0)
            ]
            available = available + sc_feats
        # Sharpshooter feat: offer stance toggle
        _feat = _get_human_feat(self._cog.db, uid, self._gid)
        if _feat == "sharpshooter":
            available.append({
                "id": "sharpshooter_stance", "name": "Sharpshooter Stance",
                "label": "🎯 Sharpshooter Stance",
                "action_type": "bonus", "level_req": 1, "once_per": None,
                "desc": "Next ranged attack: −5 to hit, +10 damage",
            })
        if not available:
            await interaction.response.send_message("No bonus actions available.", ephemeral=True)
            return
        all_members = [(u, n) for u, n in self._participants
                       if u not in self._run.get("dead", set())]
        await interaction.response.send_message(
            embed=discord.Embed(description="✨ Choose a bonus action:", color=var.COLOR_INFO),
            view=_BonusPickView(self, uid, available, all_members),
            ephemeral=True)

    @discord.ui.button(label="🧪 Item", style=discord.ButtonStyle.secondary, row=1)
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
        all_members = [(uid2, name) for uid2, name in self._participants
                       if uid2 not in self._run.get("dead", set())]
        view = _ItemPickView(self, uid, all_members, options)
        await interaction.response.send_message(
            embed=discord.Embed(description="🧪 Pick an item to use:", color=var.COLOR_INFO),
            view=view,
            ephemeral=True,
        )


class _ItemPickView(discord.ui.View):
    """Ephemeral first step: which consumable?"""

    def __init__(self, combat_view: CombatView, uid: str,
                 all_members: list[tuple[str, str]], options: list, is_bonus: bool = False):
        super().__init__(timeout=30)
        self._cv          = combat_view
        self._uid         = uid
        self._all_members = all_members
        self._is_bonus    = is_bonus
        sel = discord.ui.Select(placeholder="Choose an item…", options=options)
        sel.callback = self._on_item
        self.add_item(sel)

    async def _on_item(self, interaction: discord.Interaction):
        item_id = interaction.data["values"][0]
        await interaction.response.edit_message(
            embed=discord.Embed(description="🧪 Who should receive it?", color=var.COLOR_INFO),
            view=TargetSelectView(self._cv, self._uid, item_id, self._all_members, self._is_bonus),
        )
        self.stop()


class _FeaturePickView(discord.ui.View):
    """Ephemeral: pick which class action feature to use (main action slot)."""

    def __init__(self, combat_view: "CombatView", uid: str,
                 features: list[dict], active_members: list[tuple[str, str]]):
        super().__init__(timeout=30)
        self._cv             = combat_view
        self._uid            = uid
        self._active_members = active_members
        options = [
            discord.SelectOption(label=f["label"], value=f["id"], description=f["desc"][:100])
            for f in features
        ]
        sel = discord.ui.Select(placeholder="Choose a class action…", options=options)
        sel.callback = self._on_pick
        self.add_item(sel)

    async def _on_pick(self, interaction: discord.Interaction):
        fid = interaction.data["values"][0]
        self._cv.actions[self._uid] = {"action": "feature", "feature_id": fid}
        self._cv._check_done()
        await interaction.response.edit_message(
            embed=discord.Embed(description="⚡ Class action locked in!", color=var.COLOR_WIN), view=None)
        self.stop()


class LevelUpView(discord.ui.View):
    """One-time subclass / archetype picker shown after leveling up."""

    def __init__(self, uid: str, options: list[dict], timeout: float = 120.0):
        super().__init__(timeout=timeout)
        self._uid   = uid
        self.chosen: str | None = None
        self._done  = asyncio.Event()

        select_options = [
            discord.SelectOption(
                label=o["label"],
                value=o["id"],
                description=o.get("desc", "")[:100],
            )
            for o in options
        ]
        self._select = discord.ui.Select(
            placeholder="Choose your specialization…",
            min_values=1,
            max_values=1,
            options=select_options,
        )
        self._select.callback = self._on_pick
        self.add_item(self._select)

    async def _on_pick(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self._uid:
            await interaction.response.send_message(
                "This choice isn't yours to make.", ephemeral=True)
            return
        self.chosen = self._select.values[0]
        for item in self.children:
            item.disabled = True
        label = next(
            (o.label for o in self._select.options if o.value == self.chosen), self.chosen)
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=f"✅ You chose **{label}**.",
                color=var.COLOR_WIN,
            ),
            view=self,
        )
        self._done.set()
        self.stop()

    async def wait_for_choice(self) -> str | None:
        try:
            await asyncio.wait_for(self._done.wait(), timeout=self.timeout)
        except asyncio.TimeoutError:
            pass
        return self.chosen


class _BonusPickView(discord.ui.View):
    """Ephemeral: pick a bonus action — class feature OR general utility (Taunt)."""

    _UTILITY = [
        discord.SelectOption(label="🗣️ Taunt", value="__taunt__", description="Force the enemy to target you next hit"),
    ]

    def __init__(self, combat_view: "CombatView", uid: str,
                 features: list[dict], all_members: list[tuple[str, str]]):
        super().__init__(timeout=30)
        self._cv          = combat_view
        self._uid         = uid
        self._all_members = all_members
        options = [
            discord.SelectOption(label=f["label"], value=f["id"], description=f["desc"][:100])
            for f in features
        ]
        options.extend(self._UTILITY[: 25 - len(options)])
        sel = discord.ui.Select(placeholder="Choose a bonus action…", options=options)
        sel.callback = self._on_pick
        self.add_item(sel)

    async def _on_pick(self, interaction: discord.Interaction):
        val = interaction.data["values"][0]
        if val == "__flee__":
            self._cv.bonus_actions[self._uid] = {"action": "flee"}
            await interaction.response.edit_message(
                embed=discord.Embed(description="🏃 Flee locked in!", color=var.COLOR_WIN), view=None)
        elif val == "__taunt__":
            self._cv.bonus_actions[self._uid] = {"action": "taunt"}
            await interaction.response.edit_message(
                embed=discord.Embed(description="🗣️ Taunt locked in!", color=var.COLOR_WIN), view=None)
        elif val == "__help__":
            if _is_help_used(self._cv._cog.db, self._uid, self._cv._gid):
                await interaction.response.edit_message(
                    embed=discord.Embed(
                        description="🤝 Help already used this long rest — use `/rest` to recover it.",
                        color=var.COLOR_ERROR), view=None)
                self.stop()
                return
            targets = [(u, n) for u, n in self._cv._participants
                       if u != self._uid and u not in self._cv._run.get("dead", set())]
            if not targets:
                await interaction.response.edit_message(
                    embed=discord.Embed(description="No allies to help!", color=var.COLOR_ERROR), view=None)
                self.stop()
                return
            await interaction.response.edit_message(
                embed=discord.Embed(description="🤝 Who do you help?", color=var.COLOR_INFO),
                view=_HelpTargetView(self._cv, self._uid, targets, self._cv._run, is_bonus=True))
        elif val in ("lay_on_hands", "healing_word"):
            await interaction.response.edit_message(
                embed=discord.Embed(description="✨ Who receives it?", color=var.COLOR_INFO),
                view=_BonusTargetView(self._cv, self._uid, val, self._all_members))
        else:
            self._cv.bonus_actions[self._uid] = {"action": "bonus_feature", "feature_id": val}
            await interaction.response.edit_message(
                embed=discord.Embed(description="✨ Bonus action locked in!", color=var.COLOR_WIN), view=None)
        self.stop()


class _BonusTargetView(discord.ui.View):
    """Ephemeral: pick which ally receives a targeted bonus feature (heal)."""

    def __init__(self, combat_view: "CombatView", uid: str,
                 feature_id: str, all_members: list[tuple[str, str]]):
        super().__init__(timeout=30)
        self._cv         = combat_view
        self._uid        = uid
        self._feature_id = feature_id
        hp = combat_view._run["player_hp"]
        options = [
            discord.SelectOption(
                label=f"{name}{' (you)' if m_uid == uid else ''}{' ⚰️' if hp.get(m_uid, 0) <= 0 else ''}",
                value=m_uid)
            for m_uid, name in all_members
        ]
        sel = discord.ui.Select(placeholder="Choose a target…", options=options)
        sel.callback = self._on_target
        self.add_item(sel)

    async def _on_target(self, interaction: discord.Interaction):
        target_uid = interaction.data["values"][0]
        self._cv.bonus_actions[self._uid] = {
            "action": "bonus_feature", "feature_id": self._feature_id, "target_uid": target_uid}
        await interaction.response.edit_message(
            embed=discord.Embed(description="✨ Bonus action locked in!", color=var.COLOR_WIN), view=None)
        self.stop()


class _HelpTargetView(discord.ui.View):
    """Ephemeral: pick which ally to Help (stabilize if downed, or +4 to hit)."""

    def __init__(self, combat_view: "CombatView", uid: str,
                 targets: list[tuple[str, str]], run: dict, is_bonus: bool = False):
        super().__init__(timeout=30)
        self._cv       = combat_view
        self._uid      = uid
        self._is_bonus = is_bonus
        hp = run["player_hp"]
        options = [
            discord.SelectOption(
                label=f"{name}{' ⚰️ downed' if hp.get(t_uid, 0) <= 0 else ''}",
                value=t_uid)
            for t_uid, name in targets
        ]
        sel = discord.ui.Select(placeholder="Help who?", options=options)
        sel.callback = self._on_target
        self.add_item(sel)

    async def _on_target(self, interaction: discord.Interaction):
        target_uid = interaction.data["values"][0]
        payload = {"action": "help", "target_uid": target_uid}
        _set_help_used(self._cv._cog.db, self._uid, self._cv._gid)
        if self._is_bonus:
            self._cv.bonus_actions[self._uid] = payload
        else:
            self._cv.actions[self._uid] = payload
            self._cv._check_done()
        await interaction.response.edit_message(
            embed=discord.Embed(description="🤝 Help locked in!", color=var.COLOR_WIN), view=None)
        self.stop()


class ChoiceView(discord.ui.View):
    """Decision node — party picks a path, one player decides for everyone."""

    def __init__(self, active_uids: list[str], encounter: dict):
        super().__init__(timeout=None)
        self._active = set(active_uids)
        self.chosen: dict | None = None
        self._done = asyncio.Event()
        for opt in encounter["options"][:4]:
            btn = discord.ui.Button(label=opt["label"], style=discord.ButtonStyle.primary, row=0)
            btn.callback = self._make_cb(opt)
            self.add_item(btn)

    def _make_cb(self, opt: dict):
        async def cb(interaction: discord.Interaction):
            if str(interaction.user.id) not in self._active:
                await interaction.response.send_message("You're not in this run.", ephemeral=True)
                return
            if self._done.is_set():
                await interaction.response.send_message("Already decided.", ephemeral=True)
                return
            await interaction.response.send_message(
                f"✅ You chose: **{opt['label']}**", ephemeral=True)
            self.chosen = opt
            self._done.set()
            self.stop()
        return cb


class InteractionView(discord.ui.View):
    """Skill check / interaction encounter — one player acts for the group."""

    def __init__(self, active_uids: list[str], encounter: dict, cog=None):
        super().__init__(timeout=None)
        self.active_uids = set(active_uids)
        self.encounter   = encounter
        self.result: dict | None = None
        self.helper_uid: str | None = None   # set when a party member uses Help
        self.helper_name: str | None = None
        self._cog        = cog
        self._done = asyncio.Event()

        skill_btn = discord.ui.Button(
            label=encounter["skill_label"],
            style=discord.ButtonStyle.primary,
            row=0,
        )
        skill_btn.callback = self._skill_cb
        self.add_item(skill_btn)

        if len(active_uids) > 1:
            help_btn = discord.ui.Button(
                label="🤝 Help",
                style=discord.ButtonStyle.secondary,
                row=0,
            )
            help_btn.callback = self._help_cb
            self.add_item(help_btn)

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

    async def _help_cb(self, interaction: discord.Interaction):
        uid  = str(interaction.user.id)
        name = interaction.user.display_name
        gid  = str(interaction.guild_id)
        if uid not in self.active_uids:
            await interaction.response.send_message("You're not in this run.", ephemeral=True)
            return
        if self._done.is_set():
            await interaction.response.send_message("Already resolved.", ephemeral=True)
            return
        if self._cog and _is_help_used(self._cog.db, uid, gid):
            await interaction.response.send_message(
                "🤝 Help already used this long rest — use `/rest` to recover it.", ephemeral=True)
            return
        if self._cog:
            _set_help_used(self._cog.db, uid, gid)
        self.helper_uid  = uid
        self.helper_name = name
        await interaction.response.send_message(
            f"🤝 **{name}** steps up to help! +4 bonus to the skill check.", ephemeral=False)

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
        gid = str(interaction.guild_id)
        char_name = self._cog._char_display_name(uid, gid, interaction.user.display_name)
        self.joiners.append((uid, char_name))
        await interaction.response.edit_message(embed=self._build_embed(), view=self)
        if self._joiner_set >= set(self.party_members):
            self._all_joined.set()


class PrepareSpellsView(discord.ui.View):
    """Wizard spell preparation — choose which known spells to have ready."""

    def __init__(self, cog: "DungeonMasterCog", uid: str, gid: str,
                 preparable: list[dict], currently_prepared: list[str], max_prep: int):
        super().__init__(timeout=60)
        self._cog = cog
        self._uid = uid
        self._gid = gid
        options = [
            discord.SelectOption(
                label=f"{s['emoji']} {s['name']} (Lv {s['level']})",
                value=s["id"],
                description=s["desc"][:100],
                default=s["id"] in currently_prepared,
            )
            for s in preparable
        ]
        sel = discord.ui.Select(
            placeholder=f"Choose up to {max_prep} spells to prepare…",
            min_values=0,
            max_values=min(max_prep, len(options)),
            options=options,
        )
        sel.callback = self._on_select
        self.add_item(sel)

    async def _on_select(self, interaction: discord.Interaction):
        chosen = interaction.data["values"]
        self._cog.db.execute(
            "INSERT OR REPLACE INTO dnd_character_choices "
            "(user_id, guild_id, choice_key, choice_val) VALUES (?,?,?,?)",
            (self._uid, self._gid, "wizard_prepared_spells", ",".join(chosen)))
        names = [v.replace("_", " ").title() for v in chosen]
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=(
                    f"✅ **Spells prepared!**\n"
                    f"Ready for your next combat: {', '.join(names) or '*(none)*'}"
                ),
                color=var.COLOR_WIN,
            ),
            view=None,
        )
        self.stop()


class LearnSpellView(discord.ui.View):
    """Consume a spell scroll to permanently learn a new wizard spell."""

    def __init__(self, cog: "DungeonMasterCog", uid: str, gid: str,
                 scrolls: list[tuple]):
        super().__init__(timeout=60)
        self._cog = cog
        self._uid = uid
        self._gid = gid
        self._scroll_map: dict[str, tuple] = {}
        options = []
        for iid, qty, item in scrolls:
            if item:
                spell_id = item.get("teaches", "")
                self._scroll_map[iid] = (qty, item, spell_id)
                spell_label = spell_id.replace("_", " ").title() if spell_id else "?"
                options.append(discord.SelectOption(
                    label=f"{item['emoji']} {item['name']} ×{qty}",
                    value=iid,
                    description=f"Teaches: {spell_label}",
                ))
        sel = discord.ui.Select(placeholder="Choose a scroll to study…", options=options)
        sel.callback = self._on_select
        self.add_item(sel)

    async def _on_select(self, interaction: discord.Interaction):
        scroll_id = interaction.data["values"][0]
        qty, item, spell_id = self._scroll_map.get(scroll_id, (0, None, ""))
        if not spell_id or not item:
            await interaction.response.edit_message(
                embed=discord.Embed(description="❌ Couldn't identify the spell.", color=var.COLOR_ERROR),
                view=None)
            self.stop()
            return
        known = _get_wizard_known_spells(self._cog.db, self._uid, self._gid)
        if spell_id in known:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description=f"You already know **{spell_id.replace('_', ' ').title()}**!",
                    color=var.COLOR_INFO),
                view=None)
            self.stop()
            return
        # Consume the scroll
        self._cog.db.execute(
            "UPDATE dnd_inventory SET qty=qty-1 "
            "WHERE user_id=? AND guild_id=? AND item_id=?",
            (self._uid, self._gid, scroll_id))
        self._cog.db.execute(
            "DELETE FROM dnd_inventory "
            "WHERE user_id=? AND guild_id=? AND item_id=? AND qty<=0",
            (self._uid, self._gid, scroll_id))
        # Add to known spells
        known.append(spell_id)
        self._cog.db.execute(
            "INSERT OR REPLACE INTO dnd_character_choices "
            "(user_id, guild_id, choice_key, choice_val) VALUES (?,?,?,?)",
            (self._uid, self._gid, "wizard_known_spells", ",".join(known)))
        spell_name = spell_id.replace("_", " ").title()
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=(
                    f"📚 You studied the **{item['name']}** and permanently learned "
                    f"**{spell_name}**!\n\n"
                    f"Use `/prepare_spells` to add it to your prepared list."
                ),
                color=var.COLOR_WIN,
            ),
            view=None)
        self.stop()


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
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS dnd_character_choices (
                user_id    TEXT NOT NULL,
                guild_id   TEXT NOT NULL,
                choice_key TEXT NOT NULL,
                choice_val TEXT NOT NULL,
                PRIMARY KEY (user_id, guild_id, choice_key)
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

    def _char_display_name(self, uid: str, gid: str, fallback: str) -> str:
        rows = self.db.execute(
            "SELECT name FROM dnd_characters WHERE user_id=? AND guild_id=?", (uid, gid))
        return rows[0][0] if rows and rows[0][0] else fallback

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
        if klass is None:
            klass = next((c for c in self._extra_classes if c["id"] == char_class), None)

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
        # Elf subrace: High Elf +1 INT, Wood Elf +1 DEX (applied before mods)
        if race_id == "elf":
            _elf_sr = _get_elf_subrace(self.db, uid, gid)
            if _elf_sr == "high_elf":
                finals["intelligence"] += 1
            elif _elf_sr == "wood_elf":
                finals["dexterity"] += 1
        mods = {ab: (v - 10) // 2 for ab, v in finals.items()}
        prof = 2 + (max(1, level or 1) - 1) // 4

        hit_die = klass["hit_die"] if klass else 6
        avg_gain = hit_die // 2 + 1
        max_hp = max(1, (hit_die + mods["constitution"])
                     + (max(1, level or 1) - 1) * (avg_gain + mods["constitution"]))
        ac = 10 + mods["dexterity"] + (klass.get("armor", 0) if klass else 0)
        # Add AC bonus from equipped offhand / armor items (shields, chain mail, etc.)
        inv_rows = self.db.execute(
            "SELECT item_id FROM dnd_inventory WHERE user_id=? AND guild_id=? AND equipped=1",
            (uid, gid))
        for (inv_iid,) in (inv_rows or []):
            inv_item = self._find_item(inv_iid)
            if inv_item and inv_item.get("slot") in ("offhand", "armor"):
                ac += inv_item.get("ac_bonus", 0)

        # Equipped weapon
        weapon = self._get_equipped_weapon(uid, gid)
        if weapon:
            atk_ability = weapon.get("ability", "strength")
            dmg_expr    = weapon.get("dmg", weapon.get("damage", "1d6"))
            atk_bonus   = mods[atk_ability] + prof
        else:
            atk_ability = "strength"
            dmg_expr    = "1d4"
            atk_bonus   = mods["strength"] + prof

        # Fighting style and feat/racial bonuses
        fs         = _get_fighting_style(self.db, uid, gid, char_class)
        feat       = _get_human_feat(self.db, uid, gid)
        dwarf_tr   = _get_dwarf_trait(self.db, uid, gid)
        if fs == "defense" and klass and klass.get("armor", 0) > 0:
            ac += 1
        if feat == "tough":
            max_hp += 2 * max(1, level or 1)
        if dwarf_tr == "dwarven_toughness":
            max_hp += max(1, level or 1)

        is_ranged = weapon.get("ranged", False) if weapon else False
        handed    = weapon.get("handed", 1)     if weapon else 1

        return {
            "mods":       mods,
            "prof":       prof,
            "ac":         ac,
            "max_hp":     max_hp,
            "current_hp": current_hp or max_hp,
            "atk_bonus":  atk_bonus,
            "dmg_expr":   f"{dmg_expr}+{mods[atk_ability]}" if mods[atk_ability] >= 0
                          else f"{dmg_expr}{mods[atk_ability]}",
            "char_class": char_class,
            "level":      level or 1,
            "is_ranged":  is_ranged,
            "handed":     handed,
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

    def _give_rewards(self, uid: str, gid: str, display_name: str,
                      gold: int, xp: int) -> tuple[int, int]:
        """Return (new_level, old_level) after applying rewards."""
        self.db.ensure_user(uid, gid, display_name)
        if gold > 0:
            self.db.update_balance(uid, gid, gold, "campaign_reward")
        rows = self.db.execute(
            "SELECT level, xp FROM dnd_characters WHERE user_id=? AND guild_id=?", (uid, gid))
        if not rows:
            return 1, 1
        current_level, current_xp = rows[0]
        old_level = current_level or 1
        new_xp    = (current_xp or 0) + xp
        new_level = old_level
        while new_level < char_var.MAX_LEVEL and new_xp >= char_var.XP_THRESHOLDS[new_level + 1]:
            new_level += 1

        leveled_up = new_level > old_level
        if leveled_up:
            old_stats = self._get_char_combat_stats(uid, gid)
        self.db.execute(
            "UPDATE dnd_characters SET xp=?, level=? WHERE user_id=? AND guild_id=?",
            (new_xp, new_level, uid, gid))
        if leveled_up and old_stats:
            new_stats = self._get_char_combat_stats(uid, gid)
            if new_stats:
                hp_gain = new_stats["max_hp"] - old_stats["max_hp"]
                if hp_gain > 0:
                    new_hp = min(new_stats["max_hp"], old_stats["current_hp"] + hp_gain)
                    self.db.execute(
                        "UPDATE dnd_characters SET hp=? WHERE user_id=? AND guild_id=?",
                        (new_hp, uid, gid))
        return new_level, old_level

    async def _handle_levelup(
        self,
        channel: discord.TextChannel,
        uid: str,
        name: str,
        char_class: str,
        old_level: int,
        new_level: int,
        gid: str,
    ):
        """Post a level-up embed and handle any subclass/archetype choice prompts."""
        # Collect features gained across all gained levels.
        # CLASS_FEATURES is {class: [{"level": N, "name": "...", "desc": "..."}, ...]}
        all_feats = char_var.CLASS_FEATURES.get(char_class, [])
        gained_features: list[str] = [
            f["name"]
            for f in all_feats
            if old_level < f["level"] <= new_level
        ]

        desc_lines = [f"🎉 **{name}** reached **Level {new_level}**!"]
        if gained_features:
            desc_lines.append("\n**New features:**\n" + "\n".join(f"• **{f}**" for f in gained_features))

        embed = discord.Embed(
            title=f"⬆️ Level Up!",
            description="\n".join(desc_lines),
            color=var.COLOR_WIN,
        )
        embed.set_footer(text=f"Class: {char_class.capitalize()} · Level {new_level}")

        # Check whether any level gained triggers a subclass choice
        choice_info: dict | None = None
        for lvl in range(old_level + 1, new_level + 1):
            info = char_var.LEVEL_UP_CHOICES.get((char_class, lvl))
            if info:
                choice_info = info
                break  # handle one choice at a time (multiple level-ups are rare)

        if choice_info:
            choice_key = f"{char_class}_{choice_info['key']}"
            # Skip if already chosen (e.g. multi-level-up edge case)
            existing = self.db.execute(
                "SELECT choice_val FROM dnd_character_choices "
                "WHERE user_id=? AND guild_id=? AND choice_key=?",
                (uid, gid, choice_key))
            if not existing:
                embed.add_field(
                    name="🔮 Choice Required",
                    value=choice_info["prompt"],
                    inline=False,
                )
                view = LevelUpView(uid, choice_info["options"], timeout=120.0)
                msg  = await channel.send(
                    content=f"<@{uid}>",
                    embed=embed,
                    view=view,
                )
                chosen = await view.wait_for_choice()
                if chosen:
                    self.db.execute(
                        "INSERT OR REPLACE INTO dnd_character_choices "
                        "(user_id, guild_id, choice_key, choice_val) VALUES (?,?,?,?)",
                        (uid, gid, choice_key, chosen))
                    if char_class == "ranger" and choice_key == "ranger_subclass" and chosen == "beast_master":
                        _grant_wolf_if_needed(self.db, uid, gid)
                else:
                    # Timed out — edit message to show warning
                    for item in view.children:
                        item.disabled = True
                    timeout_embed = discord.Embed(
                        description=(
                            f"⏰ **{name}** didn't choose in time.\n"
                            "Use `/sheet` to check your character — your choice can be set later."
                        ),
                        color=var.COLOR_ERROR,
                    )
                    try:
                        await msg.edit(embed=timeout_embed, view=view)
                    except Exception:
                        pass
                return
        # No choice needed — just post the level-up embed
        await channel.send(content=f"<@{uid}>", embed=embed)

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

    @app_commands.command(
        name="subclass",
        description="Choose your subclass / archetype if you haven't picked one yet.")
    async def subclass(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        rows = self.db.execute(
            "SELECT char_class, level FROM dnd_characters WHERE user_id=? AND guild_id=?",
            (uid, gid))
        if not rows:
            await interaction.response.send_message(
                embed=self._err("You don't have a character yet."), ephemeral=True)
            return

        char_class, level = rows[0]
        if not char_class:
            await interaction.response.send_message(
                embed=self._err("Set your class first with `/class`."), ephemeral=True)
            return

        # Find the first unchosen choice at or below the character's current level
        choice_info: dict | None = None
        choice_key:  str  | None = None
        for lvl in range(1, (level or 1) + 1):
            info = char_var.LEVEL_UP_CHOICES.get((char_class, lvl))
            if not info:
                continue
            key = f"{char_class}_{info['key']}"
            already = self.db.execute(
                "SELECT choice_val FROM dnd_character_choices "
                "WHERE user_id=? AND guild_id=? AND choice_key=?",
                (uid, gid, key))
            if not already:
                choice_info = info
                choice_key  = key
                break

        if not choice_info:
            # Show all choices already stored so the player can see what they picked
            all_choice_rows = self.db.execute(
                "SELECT choice_key, choice_val FROM dnd_character_choices "
                "WHERE user_id=? AND guild_id=? AND choice_key LIKE ?",
                (uid, gid, f"{char_class}_%"))
            made_lines = []
            for ck, cv in (all_choice_rows or []):
                label_key = ck.replace(f"{char_class}_", "").replace("_", " ").title()
                # Try to find a human-readable label from LEVEL_UP_CHOICES options
                for lvl2 in range(1, (level or 1) + 1):
                    info2 = char_var.LEVEL_UP_CHOICES.get((char_class, lvl2))
                    if info2 and f"{char_class}_{info2['key']}" == ck:
                        opt = next((o for o in info2["options"] if o["id"] == cv), None)
                        if opt:
                            cv = opt["label"]
                        break
                made_lines.append(f"• **{label_key}:** {cv}")
            desc = f"No pending choices for your **{char_class.capitalize()}** at level {level}."
            if made_lines:
                desc += "\n\n**Your current selections:**\n" + "\n".join(made_lines)
            else:
                desc += "\nLevel up further to unlock choices."
            await interaction.response.send_message(
                embed=discord.Embed(description=desc, color=var.COLOR_INFO),
                ephemeral=True)
            return

        embed = discord.Embed(
            title="🔮 Subclass Choice",
            description=choice_info["prompt"],
            color=var.COLOR_INFO,
        )
        embed.set_footer(text=f"{char_class.capitalize()} · Level {level}")
        view = LevelUpView(uid, choice_info["options"], timeout=120.0)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        chosen = await view.wait_for_choice()
        if chosen:
            self.db.execute(
                "INSERT OR REPLACE INTO dnd_character_choices "
                "(user_id, guild_id, choice_key, choice_val) VALUES (?,?,?,?)",
                (uid, gid, choice_key, chosen))
            if char_class == "ranger" and choice_key == "ranger_subclass" and chosen == "beast_master":
                _grant_wolf_if_needed(self.db, uid, gid)

    # ── /prepare_spells ───────────────────────────────────────────────────────

    @app_commands.command(
        name="prepare_spells",
        description="Wizard only: choose which spells to have ready for your next combat.")
    async def prepare_spells(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        rows = self.db.execute(
            "SELECT char_class, level FROM dnd_characters WHERE user_id=? AND guild_id=?",
            (uid, gid))
        if not rows:
            await interaction.response.send_message(
                embed=self._err("You don't have a character yet."), ephemeral=True)
            return
        char_class, level = rows[0]
        if char_class != "wizard":
            await interaction.response.send_message(
                embed=self._err("Only Wizards can prepare spells."), ephemeral=True)
            return

        # Auto-init known spells for new wizards
        known = _get_wizard_known_spells(self.db, uid, gid)
        if not known:
            known = list(char_var.WIZARD_STARTING_SPELLS)
            self.db.execute(
                "INSERT OR REPLACE INTO dnd_character_choices "
                "(user_id, guild_id, choice_key, choice_val) VALUES (?,?,?,?)",
                (uid, gid, "wizard_known_spells", ",".join(known)))

        stats    = self._get_char_combat_stats(uid, gid)
        int_mod  = stats["mods"]["intelligence"] if stats else 0
        max_prep = max(2, int_mod + max(1, (level or 1) // 2))
        prepared = _get_wizard_prepared_spells(self.db, uid, gid)

        spell_lookup = {s["id"]: s for s in char_var.WIZARD_SPELLS}
        cantrips     = char_var.WIZARD_CANTRIPS
        preparable   = [
            spell_lookup[sid]
            for sid in known
            if sid in spell_lookup and sid not in cantrips
            and spell_lookup[sid]["level_req"] <= (level or 1)
        ]

        if not preparable:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "You have no preparable spells yet.\n"
                        "Buy **Spell Scrolls** from the shop and use `/learn_spell` to unlock new ones."
                    ),
                    color=var.COLOR_INFO),
                ephemeral=True)
            return

        cantrip_names = [
            spell_lookup[sid]["name"] for sid in known
            if sid in cantrips and sid in spell_lookup
        ]
        prepared_names = [p.replace("_", " ").title() for p in prepared] if prepared else ["*(none)*"]
        embed = discord.Embed(
            title="📖 Prepare Spells",
            description=(
                f"**Always ready (cantrips):** {', '.join(cantrip_names) or 'none'}\n\n"
                f"**Currently prepared:** {', '.join(prepared_names)}\n"
                f"**Max prepared:** {max_prep} *(INT {int_mod:+d} + Level {level}÷2)*\n\n"
                "Select which spells to prepare for your next combat:"
            ),
            color=var.COLOR_CAMPAIGN,
        )
        await interaction.response.send_message(
            embed=embed,
            view=PrepareSpellsView(self, uid, gid, preparable, prepared, max_prep),
            ephemeral=True)

    # ── /spells ───────────────────────────────────────────────────────────────

    @app_commands.command(
        name="spells",
        description="Wizard only: view your known and prepared spells.")
    async def spells(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        rows = self.db.execute(
            "SELECT char_class, level FROM dnd_characters WHERE user_id=? AND guild_id=?",
            (uid, gid))
        if not rows:
            await interaction.response.send_message(
                embed=self._err("You don't have a character yet."), ephemeral=True)
            return
        char_class, level = rows[0]
        if char_class != "wizard":
            await interaction.response.send_message(
                embed=self._err("Only Wizards have spells."), ephemeral=True)
            return

        known    = _get_wizard_known_spells(self.db, uid, gid)
        prepared = _get_wizard_prepared_spells(self.db, uid, gid)

        spell_lookup = {s["id"]: s for s in char_var.WIZARD_SPELLS}
        cantrips     = char_var.WIZARD_CANTRIPS

        cantrip_lines  = []
        prepared_lines = []
        known_lines    = []

        for sid in (known or list(char_var.WIZARD_STARTING_SPELLS)):
            s = spell_lookup.get(sid)
            if not s:
                continue
            level_ok = s["level_req"] <= (level or 1)
            locked   = "" if level_ok else f" *(Lv {s['level_req']} req)*"
            if sid in cantrips:
                cantrip_lines.append(f"{s['emoji']} **{s['name']}** — {s['desc']}")
            elif sid in prepared:
                prepared_lines.append(
                    f"{s['emoji']} **{s['name']}**{locked} — {s['desc']}"
                    + ("" if s["once_per"] else ""))
            else:
                known_lines.append(f"{s['emoji']} ~~{s['name']}~~{locked} *(not prepared)*")

        parts = []
        if cantrip_lines:
            parts.append("**✨ Cantrips (always available)**\n" + "\n".join(cantrip_lines))
        if prepared_lines:
            parts.append("**📖 Prepared spells**\n" + "\n".join(prepared_lines))
        if known_lines:
            parts.append("**📚 Known but not prepared**\n" + "\n".join(known_lines))
        if not parts:
            parts.append("No spells yet. Use `/prepare_spells` to set up your spellbook.")

        await interaction.response.send_message(
            embed=discord.Embed(
                title="🪄 Your Spellbook",
                description="\n\n".join(parts),
                color=var.COLOR_CAMPAIGN,
            ).set_footer(text="Use /prepare_spells to change your loadout · /learn_spell to add new spells"),
            ephemeral=True)

    # ── /learn_spell ──────────────────────────────────────────────────────────

    @app_commands.command(
        name="learn_spell",
        description="Wizard only: consume a spell scroll from your inventory to learn that spell.")
    async def learn_spell(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        rows = self.db.execute(
            "SELECT char_class FROM dnd_characters WHERE user_id=? AND guild_id=?",
            (uid, gid))
        if not rows or rows[0][0] != "wizard":
            await interaction.response.send_message(
                embed=self._err("Only Wizards can learn spells from scrolls."), ephemeral=True)
            return

        inv_rows  = self.db.execute(
            "SELECT item_id, qty FROM dnd_inventory "
            "WHERE user_id=? AND guild_id=? AND qty>0",
            (uid, gid))
        all_items = self._all_char_items()
        scrolls   = [
            (iid, qty, next((i for i in all_items if i["id"] == iid), None))
            for iid, qty in (inv_rows or [])
        ]
        scrolls = [(iid, qty, item) for iid, qty, item in scrolls
                   if item and item.get("slot") == "spell_scroll"]

        if not scrolls:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "You have no spell scrolls.\n"
                        "Buy them from the **shop** — look for `📜 Scroll of …` items!"
                    ),
                    color=var.COLOR_INFO),
                ephemeral=True)
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="📜 Learn a Spell",
                description="Choose a scroll to study and permanently learn:",
                color=var.COLOR_CAMPAIGN),
            view=LearnSpellView(self, uid, gid, scrolls),
            ephemeral=True)

    # ── /companion ────────────────────────────────────────────────────────────

    @app_commands.command(
        name="companion",
        description="View your Beast Master companion's stats, or give them a name.")
    @app_commands.describe(new_name="Give your companion a custom name (leave empty to just view)")
    async def companion(self, interaction: discord.Interaction, new_name: str | None = None):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        rows = self.db.execute(
            "SELECT char_class, level FROM dnd_characters WHERE user_id=? AND guild_id=?",
            (uid, gid))
        if not rows:
            await interaction.response.send_message(
                embed=self._err("You don't have a character yet."), ephemeral=True)
            return
        char_class, level = rows[0]
        if char_class != "ranger":
            await interaction.response.send_message(
                embed=self._err("Only Rangers have animal companions."), ephemeral=True)
            return
        sc = _get_subclass(self.db, uid, gid, "ranger")
        if sc != "beast_master":
            await interaction.response.send_message(
                embed=self._err(
                    "Only **Beast Master** Rangers have a companion.\n"
                    "Choose your archetype at level 3 with `/subclass`."),
                ephemeral=True)
            return

        # Find best companion item owned (wolf is guaranteed fallback)
        comp_ids  = ["baby_dragon_companion", "bear_companion", "eagle_companion", "wolf_companion"]
        comp_item = None
        for cid in comp_ids:
            inv = self.db.execute(
                "SELECT qty FROM dnd_inventory "
                "WHERE user_id=? AND guild_id=? AND item_id=? AND qty>0",
                (uid, gid, cid))
            if inv:
                comp_item = self._find_item(cid)
                break
        if not comp_item:
            comp_item = self._find_item("wolf_companion")  # free fallback

        # Save name if provided
        if new_name:
            new_name = new_name.strip()[:32]
            self.db.execute(
                "INSERT OR REPLACE INTO dnd_character_choices "
                "(user_id, guild_id, choice_key, choice_val) VALUES (?,?,?,?)",
                (uid, gid, "companion_name", new_name))

        name_row     = self.db.execute(
            "SELECT choice_val FROM dnd_character_choices "
            "WHERE user_id=? AND guild_id=? AND choice_key=?",
            (uid, gid, "companion_name"))
        custom_name  = name_row[0][0] if name_row else None

        beast_name   = comp_item.get("beast_name",    "Wolf")
        beast_dmg    = comp_item.get("beast_dmg",     "1d6+2")
        beast_amod   = comp_item.get("beast_atk_mod", -2)
        emoji        = comp_item.get("emoji",          "🐾")

        stats        = self._get_char_combat_stats(uid, gid)
        atk_bonus    = ((stats["atk_bonus"] if stats else 0) + beast_amod)
        display_name = custom_name or beast_name

        _flavor = {
            "Wolf":        "A loyal pack hunter that fights at your side every round.",
            "Eagle":       "A keen-eyed raptor that strikes fast with deadly talons.",
            "Bear":        "A powerful grizzly that hits hard and takes hits harder.",
            "Baby Dragon": "A fierce dragonling whose breath sends enemies running.",
        }
        _tier_label = {
            "Wolf": "Common", "Eagle": "Uncommon", "Bear": "Rare", "Baby Dragon": "Legendary"
        }

        embed = discord.Embed(
            title=f"{emoji} {display_name}",
            description=(
                f"*{beast_name}* · {_tier_label.get(beast_name, '')} companion\n"
                f"{_flavor.get(beast_name, '')}"
            ),
            color=var.COLOR_WIN,
        )
        embed.add_field(name="⚔️ Damage",    value=beast_dmg,          inline=True)
        embed.add_field(name="🎯 ATK Bonus", value=f"{atk_bonus:+d}",  inline=True)
        embed.add_field(name="🧑 Owner",     value=interaction.user.display_name, inline=True)
        if new_name:
            embed.set_footer(text=f"✅ Name set to '{display_name}'!")
        elif not custom_name:
            embed.set_footer(text=f"Tip: /companion new_name:Rex to give {beast_name} a personal name.")
        else:
            embed.set_footer(text=f"Use /companion new_name:… to rename {display_name}.")
        await interaction.response.send_message(embed=embed)

    # ── /set_level ────────────────────────────────────────────────────────────

    @app_commands.command(name="set_level", description="[Admin] Set a player's character level.")
    @app_commands.describe(member="The player", level="New level (1–20)")
    @app_commands.default_permissions(administrator=True)
    async def set_level(self, interaction: discord.Interaction, member: discord.Member, level: int):
        if not 1 <= level <= 20:
            await interaction.response.send_message(
                embed=self._err("Level must be between 1 and 20."), ephemeral=True)
            return
        uid = str(member.id)
        gid = str(interaction.guild_id)
        rows = self.db.execute(
            "SELECT name FROM dnd_characters WHERE user_id=? AND guild_id=?", (uid, gid))
        if not rows:
            await interaction.response.send_message(
                embed=self._err(f"{member.display_name} doesn't have a character."), ephemeral=True)
            return
        char_name = rows[0][0] or member.display_name
        # Compute XP to reach this level (use the threshold table from char_var)
        target_xp = char_var.XP_THRESHOLDS.get(level, char_var.XP_THRESHOLDS[level])
        self.db.execute(
            "UPDATE dnd_characters SET level=?, xp=? WHERE user_id=? AND guild_id=?",
            (level, target_xp, uid, gid))
        # Recompute and save max HP for new level
        stats = self._get_char_combat_stats(uid, gid)
        if stats:
            self.db.execute(
                "UPDATE dnd_characters SET hp=? WHERE user_id=? AND guild_id=?",
                (stats["max_hp"], uid, gid))
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ **{char_name}** is now level **{level}** ({target_xp:,} XP).",
                color=var.COLOR_WIN),
            ephemeral=True)

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
                    solo=[(uid, self._char_display_name(uid, gid, interaction.user.display_name))]))

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
                "gid":                gid,
                "participants":       participants,
                "player_hp":          {},
                "player_max_hp":      {},
                "fled":               set(),
                "log":                [],
                "features_used":      {},
                "raging_uids":        set(),
                "downed":             {},
                "dead":               set(),
                "hunters_mark_uids":  set(),
                "helped_next_attack": {},
                "subclass_used":        {},
                "ward_hp":              {},
                "beast_companion":      set(),
                "beast_companion_item": {},   # {uid: item_dict or None}
                "sacred_weapon_uids":   set(),
                "portent_used":         set(),
                "vow_of_enmity":        set(),
                "guided_strike":        set(),
                "superiority_die":      set(),
                "warding_flare":        set(),
                "arcane_distraction":   set(),
                "natures_wrath_active": False,
                # Fighter-specific
                "sup_dice":             {},   # {uid: int} Battle Master dice remaining
                "sup_die_type":         {},   # {uid: str} "1d8"|"1d10"|"1d12"
                "bm_pending":           {},   # {uid: {type, die}} queued maneuver effect
                "action_surge_uses":    {},   # {uid: int} charges remaining
                "indomitable_uses":     {},   # {uid: int} charges remaining
                "fighting_style":       {},   # {uid: str|None}
                "shield_spell_ac":      set(),# EK Shield spell active this round
                "fire_bolt_rnd":        {},   # {uid: int} last round Fire Bolt was cast (War Magic)
                "eldritch_strike_rnd":  {},   # {uid: int} Eldritch Strike triggers this round
                "survivor_uids":        set(),# Champion Lv18 Survivor
                "sharpshooter_stance":  set(),# Sharpshooter -5/+10 stance active this round
                "alert_uids":           set(),# Alert feat — always-first on initiative
                "protection_uids":      set(),# Protection fighting style — reduce ally dmg
                "bm_riposte_set":       set(),# BM Riposte pending this round
                "enemy_ac_penalty":     0,    # BM Trip: enemy AC reduced
                "enemy_atk_penalty":    0,    # BM Disarm: enemy ATK reduced
                # Ranger-specific
                "favored_enemy":        {},   # {uid: str|None} favored enemy type
                "ensnaring_uids":       set(),# Ensnaring Strike armed (next ranged hit restrain)
                "hail_uids":            set(),# Hail of Thorns armed (next ranged hit +1d10)
                "vanish_uids":          set(),# Vanish active this round (half dmg from next hit)
                "beast_protect_uids":   set(),# Beast Guard active this round (half dmg from next hit)
                # Wizard-specific
                "wizard_prepared":      {},   # {uid: list[str]} spells prepared for this combat
                "counterspell_uids":    set(),# Counterspell cast — enemy skips attack this round
                "misty_step_uids":      set(),# Misty Step — half dmg from next hit this round
            }
            for uid, name in participants:
                run_state["features_used"][uid]  = set()
                run_state["subclass_used"][uid]  = set()
                stats = self._get_char_combat_stats(uid, gid)
                hp_max = stats["max_hp"]     if stats else 10
                hp_cur = stats["current_hp"] if stats else hp_max
                run_state["player_hp"][uid]     = hp_cur
                run_state["player_max_hp"][uid] = hp_max
                if stats:
                    char_class = stats["char_class"]
                    level      = stats["level"]
                    sc  = _get_subclass(self.db, uid, gid, char_class)
                    fs  = _get_fighting_style(self.db, uid, gid, char_class)
                    run_state["fighting_style"][uid]  = fs
                    run_state["favored_enemy"][uid]   = _get_favored_enemy(self.db, uid, gid)

                    if sc == "abjuration":
                        int_mod = stats["mods"]["intelligence"]
                        run_state["ward_hp"][uid] = max(1, int_mod + level)
                    elif sc == "beast_master":
                        run_state["beast_companion"].add(uid)
                        # Best-to-worst: baby_dragon > bear > eagle > wolf (wolf is free fallback)
                        _comp_ids = ["baby_dragon_companion", "bear_companion",
                                     "eagle_companion",       "wolf_companion"]
                        _comp_item = None
                        for _cid in _comp_ids:
                            _crows = self.db.execute(
                                "SELECT 1 FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id=?",
                                (uid, gid, _cid))
                            if _crows:
                                _comp_item = self._find_item(_cid)
                                break
                        run_state["beast_companion_item"][uid] = _comp_item
                    elif sc == "light":
                        run_state["warding_flare"].add(uid)
                    elif sc == "champion" and level >= 18:
                        run_state["survivor_uids"].add(uid)

                    if sc == "battle_master" and level >= 3:
                        n_dice  = 4 + (1 if level >= 7 else 0) + (1 if level >= 10 else 0) + (1 if level >= 15 else 0)
                        die_type = "1d12" if level >= 15 else ("1d10" if level >= 10 else "1d8")
                        run_state["sup_dice"][uid]    = n_dice
                        run_state["sup_die_type"][uid] = die_type

                    if char_class == "fighter":
                        surge_uses = 2 if level >= 17 else 1
                        run_state["action_surge_uses"][uid] = surge_uses
                        indom_uses = (3 if level >= 17 else 2 if level >= 13 else 1) if level >= 9 else 0
                        run_state["indomitable_uses"][uid]  = indom_uses

                    if fs == "protection":
                        run_state["protection_uids"].add(uid)

                    if char_class == "wizard":
                        _prep = _get_wizard_prepared_spells(self.db, uid, gid)
                        # Always include cantrips; fallback to starting spells if nothing prepared
                        _cantrips = list(char_var.WIZARD_CANTRIPS)
                        if not _prep:
                            _prep = list(char_var.WIZARD_STARTING_SPELLS)
                        for _c in _cantrips:
                            if _c not in _prep:
                                _prep = [_c] + _prep
                        run_state["wizard_prepared"][uid] = _prep

                    feat = _get_human_feat(self.db, uid, gid)
                    if feat == "alert":
                        run_state["alert_uids"].add(uid)
            self._runs[run_id] = run_state

            # Intro
            names = ", ".join(f"**{n}**" for _, n in participants)
            intro = discord.Embed(
                title=f"{campaign['emoji']} {campaign['name']}",
                description=f"*{campaign['intro']}*\n\n**Adventurers:** {names}",
                color=var.COLOR_CAMPAIGN,
            )
            if campaign.get("image"):
                intro.set_image(url=campaign["image"])
            intro.set_footer(text=var.SERVER_NAME)
            await interaction.channel.send(embed=intro)
            await asyncio.sleep(2)

            # Run encounters (queue supports choice nodes injecting sub-encounters)
            success        = True
            enc_queue      = list(campaign["encounters"])
            enc_idx        = 0
            while enc_idx < len(enc_queue):
                encounter = enc_queue[enc_idx]
                if encounter["type"] == "combat":
                    result = await self._run_combat(interaction.channel, encounter, run_id)
                elif encounter["type"] == "choice":
                    result, extra = await self._run_choice(interaction.channel, encounter, run_id)
                    if extra and result == "victory":
                        enc_queue[enc_idx + 1:enc_idx + 1] = extra
                else:
                    result = await self._run_interaction(interaction.channel, encounter, run_id)

                if result in ("defeat", "all_fled"):
                    success = False
                    break
                enc_idx += 1

            # Final rewards
            run   = self._runs[run_id]
            alive = [(uid, name) for uid, name in participants
                     if uid not in run["fled"]
                     and uid not in run.get("dead", set())
                     and run["player_hp"].get(uid, 0) > 0]

            levelups: list = []  # (uid, name, char_class, old_level, new_level)
            if success and alive:
                total_gold = random.randint(campaign["reward_gold_min"], campaign["reward_gold_max"])
                gold_each  = max(1, total_gold // max(1, len(alive)))
                xp_each    = campaign["reward_xp"]
                lines      = []
                for uid, name in alive:
                    new_level, old_level = self._give_rewards(uid, gid, name, gold_each, xp_each)
                    lvl_up = f"  🎉 **Level {new_level}!**" if new_level > old_level else ""
                    lines.append(
                        f"• **{name}** — +{gold_each:,} {var.CURRENCY_SYMBOL}  ·  +{xp_each:,} XP{lvl_up}")
                    if new_level > old_level:
                        stats = self._get_char_combat_stats(uid, gid)
                        char_class = stats["char_class"] if stats else "unknown"
                        levelups.append((uid, name, char_class, old_level, new_level))
                result_embed = discord.Embed(
                    title=f"✅ {campaign['name']} — Victory!",
                    description="\n".join(lines),
                    color=var.COLOR_WIN,
                )
            else:
                # Death penalty: non-fleeing players lose 50% of their coins
                penalty_lines = []
                for p_uid, p_name in participants:
                    if p_uid not in run.get("fled", set()):
                        bal     = self.db.get_balance(p_uid, gid)
                        penalty = bal // 2
                        if penalty > 0:
                            self.db.update_balance(p_uid, gid, -penalty, "death_penalty")
                            penalty_lines.append(f"• **{p_name}** lost {penalty:,} {var.CURRENCY_SYMBOL}")
                desc = "The party was overwhelmed and forced to retreat.\n*(Use `/rest` to recover HP.)*"
                if penalty_lines:
                    desc += "\n\n💸 **Death penalty (−50% coins):**\n" + "\n".join(penalty_lines)
                result_embed = discord.Embed(
                    title=f"❌ {campaign['name']} — Defeated!",
                    description=desc,
                    color=var.COLOR_ERROR,
                )

            # Save current HP to DB for all participants
            for p_uid, _ in participants:
                final_hp = run["player_hp"].get(p_uid, 0)
                self.db.execute(
                    "UPDATE dnd_characters SET hp=? WHERE user_id=? AND guild_id=?",
                    (max(0, final_hp), p_uid, gid))

            result_embed.set_footer(text=var.SERVER_NAME)
            await interaction.channel.send(embed=result_embed)
            self._save_run_log(run_id, gid, campaign, participants, success, run["log"])

            # Fire level-up notifications / subclass prompts after the result embed
            if success:
                for lu_uid, lu_name, lu_class, lu_old, lu_new in levelups:
                    await self._handle_levelup(
                        interaction.channel,
                        lu_uid, lu_name, lu_class, lu_old, lu_new, gid)

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

        # Reset per-combat state so once-per-combat features recharge each encounter
        for _uid, _ in run["participants"]:
            run["features_used"][_uid]  = set()
            run["subclass_used"][_uid]  = set()
        for _key in ("raging_uids", "hunters_mark_uids", "shield_spell_ac",
                     "counterspell_uids", "misty_step_uids", "sacred_weapon_uids",
                     "portent_used", "vow_of_enmity", "guided_strike", "superiority_die",
                     "warding_flare", "arcane_distraction", "ensnaring_uids", "hail_uids",
                     "vanish_uids", "beast_protect_uids", "sharpshooter_stance",
                     "bm_riposte_set"):
            if _key in run:
                run[_key].clear()
        for _key in ("bm_pending", "fire_bolt_rnd", "eldritch_strike_rnd"):
            if _key in run:
                run[_key].clear()
        run["natures_wrath_active"] = False
        run["enemy_ac_penalty"]     = 0
        run["enemy_atk_penalty"]    = 0
        # Recharge action-surge and superiority dice (recharge on short rest = between encounters)
        for _uid, _ in run["participants"]:
            _uid_stats = self._get_char_combat_stats(_uid, gid)
            if not _uid_stats:
                continue
            _uid_class = _uid_stats["char_class"]
            _uid_level = _uid_stats["level"]
            if _uid_class == "fighter":
                run["action_surge_uses"][_uid] = 2 if _uid_level >= 17 else 1
            _uid_sc = _get_subclass(self.db, _uid, gid, _uid_class)
            if _uid_sc == "battle_master" and _uid_level >= 3:
                _n = 4 + (1 if _uid_level >= 7 else 0) + (1 if _uid_level >= 10 else 0) + (1 if _uid_level >= 15 else 0)
                _die = "1d12" if _uid_level >= 15 else ("1d10" if _uid_level >= 10 else "1d8")
                run["sup_dice"][_uid]     = _n
                run["sup_die_type"][_uid] = _die
            if _uid_sc == "abjuration":
                _int_mod = _uid_stats["mods"]["intelligence"]
                run["ward_hp"][_uid] = max(1, _int_mod + _uid_level)

        # Carry setback disadvantage earned from a failed skill check into this combat
        run["disadvantage_uids"] = set()
        if run.pop("setback_disadvantage", False):
            run["disadvantage_uids"] = {u for u, _ in run["participants"]
                                         if u not in run["fled"]
                                         and run["player_hp"].get(u, 0) > 0}

        enemy      = dict(encounter["enemy"])
        party_size = len(run["participants"])
        _base_hp   = enemy["hp"]
        # Decide whether to multiply enemies or scale HP based on enemy strength:
        #   Mooks  (≤30 HP)  → spawn one per player, cap 3, base HP each
        #   Elites (31-60 HP)→ 1 for solo/duo, 2 for 3-4 players; HP distributed
        #   Bosses (>60 HP)  → always 1 enemy, scale HP with party size (old behavior)
        if _base_hp <= 30:
            n_enemies = min(party_size, 3)
            _per_hp   = _base_hp
        elif _base_hp <= 60:
            n_enemies = 1 if party_size <= 2 else 2
            _total_hp = _base_hp + (party_size - 1) * max(1, _base_hp // 3)
            _per_hp   = max(1, _total_hp // n_enemies)
        else:
            n_enemies = 1
            _per_hp   = _base_hp + (party_size - 1) * max(1, _base_hp // 3)
        enemies    = [
            {"idx": i, "hp": _per_hp, "max_hp": _per_hp,
             "name": (enemy["name"] if n_enemies == 1 else f"{enemy['name']} {chr(65 + i)}")}
            for i in range(n_enemies)
        ]
        run["combat_enemies"]     = enemies
        run["combat_enemy_base"]  = enemy  # base dict with emoji, ac, atk_bonus etc.
        e_max  = _per_hp           # kept for any leftover refs; use enemies[x]["hp"] instead
        e_hp   = _per_hp           # placeholder; overwritten per-player each round
        rnd    = 0
        last_hitter: tuple | None              = None
        kill_entries_log: list[dict]           = []   # per-enemy kill log entries
        already_killed:   set[int]             = set()  # enemy indices already processed

        # ── Local helpers ─────────────────────────────────────────────────────
        def _first_alive_idx() -> int:
            for _i, _e in enumerate(enemies):
                if _e["hp"] > 0:
                    return _i
            return 0

        def _clamp_to_alive(tidx: int) -> int:
            if 0 <= tidx < len(enemies) and enemies[tidx]["hp"] > 0:
                return tidx
            return _first_alive_idx()

        surprise    = encounter.get("surprise", False)
        surp_note   = "  ·  ⚡ **Surprise!**" if surprise else ""
        if n_enemies == 1:
            enemy_intro_txt = (
                f"{enemy['emoji']} **{enemy['name']}**  —  "
                f"HP **{_per_hp}**  ·  AC **{enemy['ac']}**{surp_note}"
            )
        else:
            enemy_intro_txt = (
                f"{enemy['emoji']} **{n_enemies}× {enemy['name']}**  —  "
                f"HP **{_per_hp}** each  ·  AC **{enemy['ac']}**{surp_note}\n"
                f"*(one enemy per player)*"
            )
        intro_embed = discord.Embed(
            title=f"⚔️ {encounter['name']}",
            description=f"*{encounter['intro']}*\n\n{enemy_intro_txt}",
            color=var.COLOR_COMBAT,
        )
        if encounter.get("image"):
            intro_embed.set_image(url=encounter["image"])
        await channel.send(embed=intro_embed)
        await asyncio.sleep(1)

        if run["disadvantage_uids"]:
            await channel.send(embed=discord.Embed(
                description=(
                    "⬇️ **Disadvantage** — the party enters this fight rattled from the failed check. "
                    "All attack rolls are made at disadvantage *(roll twice, take lower)*."
                ),
                color=var.COLOR_ERROR))
            await asyncio.sleep(1)

        # Ranger Primeval Awareness (Lv 3+): sense if enemy matches favored type
        for _pa_uid, _pa_name in run["participants"]:
            _pa_stats = self._get_char_combat_stats(_pa_uid, gid)
            if (_pa_stats and _pa_stats["char_class"] == "ranger"
                    and _pa_stats["level"] >= 3):
                _pa_fe = run.get("favored_enemy", {}).get(_pa_uid)
                if _pa_fe and _enemy_matches_type(enemy["name"], _pa_fe):
                    await channel.send(embed=discord.Embed(
                        description=(
                            f"🦅 **{_pa_name}** — *Primeval Awareness:* "
                            f"You sense these are **{_pa_fe}** — your favored prey. "
                            f"Your +2 favored enemy bonus applies!"
                        ),
                        color=var.COLOR_WIN))
                    await asyncio.sleep(1)

        # ── Initiative (skipped on surprise) ──────────────────────────────────
        active_init  = [uid for uid, _ in run["participants"]
                        if uid not in run["fled"] and run["player_hp"].get(uid, 0) > 0]
        name_map     = {uid: name for uid, name in run["participants"]}

        enemy_surprise = encounter.get("enemy_surprise", False)
        if surprise:
            enemy_first = False
            await channel.send(embed=discord.Embed(
                title="⚡ Surprise Round!",
                description="You catch them off-guard — free round of attacks before they can react!",
                color=var.COLOR_WIN,
            ))
            await asyncio.sleep(1)
        elif enemy_surprise:
            enemy_first = False  # after the ambush, players rally and fight normally
            await channel.send(embed=discord.Embed(
                title="⚡ Ambush! You've been caught off-guard!",
                description=f"**{enemy['name']}** strikes before you can react — free hit!",
                color=var.COLOR_ERROR,
            ))
            await asyncio.sleep(1)
            if active_init:
                t_uid  = random.choice(active_init)
                t_name = next((n for u, n in run["participants"] if u == t_uid), t_uid)
                t_stat = self._get_char_combat_stats(t_uid, gid)
                if t_stat:
                    e_roll = random.randint(1, 20)
                    e_tot  = e_roll + enemy["atk_bonus"]
                    if e_roll == 20 or e_tot >= t_stat["ac"]:
                        dmg1 = _roll(enemy["dmg"])
                        if e_roll == 20:
                            dmg2 = _roll(enemy["dmg"])
                            dmg  = dmg1 + dmg2
                            atk_txt = f"✨ CRIT! {dmg1}+{dmg2} = **{dmg} dmg**"
                        else:
                            dmg = dmg1
                            atk_txt = f"**{dmg} dmg**"
                        run["player_hp"][t_uid] = max(0, run["player_hp"].get(t_uid, 0) - dmg)
                        if run["player_hp"][t_uid] <= 0:
                            run.setdefault("downed", {})[t_uid] = {"successes": 0, "failures": 0}
                            atk_txt += f"\n💀 **{t_name}** goes down!"
                        run["log"].append({"type": "enemy_hit", "enemy": enemy["name"],
                            "target": t_uid, "target_name": t_name, "dmg": dmg, "round": 0})
                    else:
                        atk_txt = "MISS!"
                    await channel.send(embed=discord.Embed(
                        description=f"💥 **{enemy['name']}** ambushes **{t_name}** → {atk_txt}",
                        color=var.COLOR_ERROR,
                    ))
                    await asyncio.sleep(1)
                active_init = [u for u in active_init if run["player_hp"].get(u, 0) > 0]
                if not active_init:
                    return "defeat"
        else:
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
        while any(e["hp"] > 0 for e in enemies):
            rnd += 1

            # ── Per-round state reset ─────────────────────────────────────────
            run["sharpshooter_stance"] = set()
            run["bm_riposte_set"]      = set()
            run["shield_spell_ac"]     = set()
            run["bm_pending"]          = {}
            run["enemy_ac_penalty"]    = 0
            run["enemy_atk_penalty"]   = 0
            run["vanish_uids"]         = set()
            run["beast_protect_uids"]  = set()
            run["counterspell_uids"]   = set()
            run["misty_step_uids"]     = set()

            # ── Champion Survivor (Lv18) — regain HP at round start ───────────
            if rnd > 1:
                surv_lines: list[str] = []
                for s_uid, s_name in run["participants"]:
                    if s_uid not in run.get("survivor_uids", set()):
                        continue
                    if run["player_hp"].get(s_uid, 0) <= 0:
                        continue
                    s_max = run["player_max_hp"].get(s_uid, 1)
                    s_hp  = run["player_hp"].get(s_uid, 0)
                    if s_hp <= s_max // 2:
                        s_stats = self._get_char_combat_stats(s_uid, gid)
                        con_mod = s_stats["mods"]["constitution"] if s_stats else 0
                        regain  = max(1, 5 + con_mod)
                        run["player_hp"][s_uid] = min(s_max, s_hp + regain)
                        surv_lines.append(f"💚 **{s_name}** Survivor — regains **{regain} HP**")
                if surv_lines:
                    await channel.send(embed=discord.Embed(
                        title="💚 Champion Survivor",
                        description="\n".join(surv_lines),
                        color=var.COLOR_WIN,
                    ))
                    await asyncio.sleep(1)

            # ── Death saving throws ───────────────────────────────────────────
            downed = run.setdefault("downed", {})
            dead   = run.setdefault("dead",   set())
            ds_lines: list[str] = []
            for uid, name in run["participants"]:
                if uid in dead or uid in run["fled"]:
                    continue
                if run["player_hp"].get(uid, 0) > 0:
                    continue
                if uid not in downed:
                    downed[uid] = {"successes": 0, "failures": 0}
                entry = downed[uid]
                ds    = random.randint(1, 20)
                if ds == 20:
                    run["player_hp"][uid] = 1
                    del downed[uid]
                    ds_lines.append(f"✨ **{name}** rolled **20** on their death save — stabilizes at **1 HP!**")
                elif ds == 1:
                    entry["failures"] += 2
                    if entry["failures"] >= 3:
                        dead.add(uid)
                        del downed[uid]
                        ds_lines.append(f"💀 **{name}** rolled **1** — 2 failures — **dead**.")
                        run["log"].append({"type": "death", "uid": uid, "name": name, "round": rnd})
                    else:
                        ds_lines.append(f"💀 **{name}** rolled **1** — 2 failures! ({entry['failures']}/3)")
                elif ds >= 10:
                    entry["successes"] += 1
                    if entry["successes"] >= 3:
                        run["player_hp"][uid] = 1
                        del downed[uid]
                        ds_lines.append(f"✨ **{name}** rolled **{ds}** — 3rd success, stabilizes at **1 HP!**")
                    else:
                        ds_lines.append(f"⚰️ **{name}** rolled **{ds}** — success ({entry['successes']}/3)")
                else:
                    entry["failures"] += 1
                    if entry["failures"] >= 3:
                        dead.add(uid)
                        del downed[uid]
                        ds_lines.append(f"⚰️ **{name}** rolled **{ds}** — 3rd failure — **dead**.")
                        run["log"].append({"type": "death", "uid": uid, "name": name, "round": rnd})
                    else:
                        ds_lines.append(f"⚰️ **{name}** rolled **{ds}** — failure ({entry['failures']}/3 failures)")
            if ds_lines:
                await channel.send(embed=discord.Embed(
                    title="⚰️ Death Saving Throws",
                    description="\n".join(ds_lines),
                    color=var.COLOR_ERROR,
                ))
                await asyncio.sleep(1)

            # ── Active check ──────────────────────────────────────────────────
            active = [uid for uid, _ in run["participants"]
                      if uid not in run["fled"]
                      and uid not in run.get("dead", set())
                      and run["player_hp"].get(uid, 0) > 0]
            if not active:
                if all(uid in run["fled"]
                       for uid, _ in run["participants"]
                       if uid not in run.get("dead", set())):
                    return "all_fled"
                return "defeat"

            # ── Enemy surprise: players stunned, cannot act round 1 ────────
            if enemy_surprise and rnd == 1:
                await channel.send(embed=discord.Embed(
                    title="😵 Surprise Round — Party is Stunned!",
                    description=(
                        "The ambush leaves the party scrambling — "
                        "**you cannot act this round!**"
                    ),
                    color=var.COLOR_ERROR))
                await asyncio.sleep(2)
                continue

            # ── Enemy strikes first if it won initiative ───────────────────
            if enemy_first and any(e["hp"] > 0 for e in enemies):
                # Each alive enemy gets one pre-round strike
                for _ei, _eobj in enumerate(enemies):
                    if _eobj["hp"] <= 0:
                        continue
                    if not active:
                        break
                    taunt_first = [u for u in run.get("taunt_targets", set()) if u in active]
                    t_uid  = random.choice(taunt_first) if taunt_first else random.choice(active)
                    run["taunt_targets"] = set()
                    t_name = next((n for u, n in run["participants"] if u == t_uid), t_uid)
                    t_stat = self._get_char_combat_stats(t_uid, gid)
                    if t_stat:
                        e_roll = random.randint(1, 20)
                        e_tot  = e_roll + enemy["atk_bonus"]
                        if e_roll == 20 or e_tot >= t_stat["ac"]:
                            dmg1 = _roll(enemy["dmg"])
                            if e_roll == 20:
                                dmg2 = _roll(enemy["dmg"])
                                dmg  = dmg1 + dmg2
                                hit_txt = f"✨ **CRIT!** {dmg1}+{dmg2} = **{dmg} dmg**"
                            else:
                                dmg     = dmg1
                                hit_txt = f"**{dmg} dmg**"
                            ef_sc = _get_subclass(self.db, t_uid, gid, t_stat["char_class"])
                            if t_uid in run.get("raging_uids", set()) and ef_sc == "totem_warrior":
                                dmg = max(1, dmg // 2)
                                hit_txt += " *(Bear — half dmg)*"
                            ef_ward = run.get("ward_hp", {}).get(t_uid, 0)
                            if ef_ward > 0:
                                ef_abs = min(ef_ward, dmg)
                                dmg   -= ef_abs
                                run["ward_hp"][t_uid] = ef_ward - ef_abs
                                hit_txt += f" *(Ward absorbed {ef_abs})*"
                            run["player_hp"][t_uid] = max(0, run["player_hp"][t_uid] - dmg)
                            ko_txt = ""
                            if run["player_hp"][t_uid] <= 0:
                                run.setdefault("downed", {})[t_uid] = {"successes": 0, "failures": 0}
                                ko_txt = f"\n💀 **{t_name}** goes down!"
                            pre_desc = (f"💥 **{_eobj['name']}** strikes first!\n"
                                        f"Hits **{t_name}** → {hit_txt}{ko_txt}")
                            run["log"].append({
                                "type": "enemy_hit", "enemy": _eobj["name"],
                                "target": t_uid, "target_name": t_name,
                                "dmg": dmg, "round": rnd, "initiative": True,
                            })
                        else:
                            pre_desc = f"💨 **{_eobj['name']}** lunges first at **{t_name}** — MISS!"
                        await channel.send(embed=discord.Embed(
                            title=f"⚡ Round {rnd} — {_eobj['name']} goes first!",
                            description=pre_desc, color=var.COLOR_COMBAT))
                        await asyncio.sleep(1)
                        # Refresh active after possible KO
                        active = [uid for uid, _ in run["participants"]
                                  if uid not in run["fled"]
                                  and uid not in run.get("dead", set())
                                  and run["player_hp"].get(uid, 0) > 0]

                if not active:
                    return "defeat"

            # ── HP bars + action buttons ───────────────────────────────────
            hp_lines = []
            for uid, name in run["participants"]:
                if uid in run["fled"]:
                    continue
                hp  = run["player_hp"].get(uid, 0)
                mhp = run["player_max_hp"].get(uid, 1)
                if uid in run.get("dead", set()):
                    hp_lines.append(f"💀 **{name}** — dead")
                elif hp <= 0:
                    hp_lines.append(f"⚰️ **{name}** — downed")
                else:
                    hp_lines.append(f"❤️ **{name}** — {hp}/{mhp} HP")

            enemy_hp_lines = []
            for _eobj in enemies:
                if _eobj["hp"] > 0:
                    _filled = int((_eobj["hp"] / _eobj["max_hp"]) * 10)
                    _bar    = "█" * _filled + "░" * (10 - _filled)
                    enemy_hp_lines.append(
                        f"{enemy['emoji']} **{_eobj['name']}** HP: `{_bar}` {_eobj['hp']}/{_eobj['max_hp']}")
                else:
                    enemy_hp_lines.append(f"💀 ~~{_eobj['name']}~~")

            bonuses_txt: list[str] = []
            if run.get("raging_uids"):
                rage_names = [n for u, n in run["participants"] if u in run["raging_uids"]]
                bonuses_txt.append(f"💢 Raging: {', '.join(rage_names)}")
            if run.get("hunters_mark_uids"):
                mark_names = [n for u, n in run["participants"] if u in run["hunters_mark_uids"]]
                bonuses_txt.append(f"🎯 Marked: {', '.join(mark_names)}")
            buff_line = ("\n" + " · ".join(bonuses_txt)) if bonuses_txt else ""

            if surprise and rnd == 1:
                round_title  = f"⚡ Surprise Round  —  {encounter['name']}"
                round_footer = "⚡ Free round — the enemy cannot react! Choose your actions."
            else:
                round_title  = f"⚔️ Round {rnd}  —  {encounter['name']}"
                round_footer = "⚔️ Attack · 🛡️ Dodge · 🏃 Flee · 🤝 Help · ⚡ Class Action · ✨ Bonus (Taunt + class) · 🧪 Item"

            status = discord.Embed(
                title=round_title,
                description=(
                    "\n".join(enemy_hp_lines) + "\n\n"
                    + "\n".join(hp_lines)
                    + buff_line
                ),
                color=var.COLOR_COMBAT,
            )
            status.set_footer(text=round_footer)

            view = CombatView(active, self, gid, run["participants"], run, enemies=enemies)
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

            round_lines:     list[str] = []
            dodgers:         set[str]  = set()
            cunning_dodgers: set[str]  = set()

            # ── Process bonus actions ──────────────────────────────────────
            for uid, name in run["participants"]:
                if uid not in active:
                    continue
                bonus = view.bonus_actions.get(uid)
                if not bonus:
                    continue
                bonus_act = bonus.get("action")
                fid       = bonus.get("feature_id")
                stats     = self._get_char_combat_stats(uid, gid)
                level     = stats["level"] if stats else 1
                wis       = stats["mods"]["wisdom"]   if stats else 0
                cha       = stats["mods"]["charisma"] if stats else 0

                # ── Utility bonus actions ─────────────────────────────────────
                if bonus_act == "flee":
                    run["fled"].add(uid)
                    round_lines.append(f"🏃 **{name}** breaks away! *(bonus — flees the battle)*")
                    run["log"].append({"type": "flee", "uid": uid, "name": name, "round": rnd})
                    continue

                elif bonus_act == "help":
                    t_uid  = bonus.get("target_uid", uid)
                    t_name = next((n for u, n in run["participants"] if u == t_uid), t_uid)
                    if t_uid in run.get("downed", {}):
                        wis_mod = stats["mods"]["wisdom"] if stats else 0
                        roll    = random.randint(1, 20) + wis_mod
                        if roll >= 10:
                            run["player_hp"][t_uid] = 1
                            del run["downed"][t_uid]
                            round_lines.append(
                                f"🤝 **{name}** stabilizes **{t_name}** (Medicine {roll}) → 1 HP! *(bonus)*")
                        else:
                            round_lines.append(
                                f"🤝 **{name}** tries to stabilize **{t_name}** (Medicine {roll}) — failed *(bonus)*")
                    else:
                        run.setdefault("helped_next_attack", {})[t_uid] = 4
                        round_lines.append(f"🤝 **{name}** helps **{t_name}** — +4 to hit! *(bonus)*")
                    run["log"].append({"type": "help", "uid": uid, "target": t_uid, "round": rnd})
                    continue

                elif bonus_act == "use_item":
                    item_id    = bonus.get("item_id")
                    target_uid = bonus.get("target_uid", uid)
                    item       = self._find_item(item_id) if item_id else None
                    if item and item.get("heal_expr") and target_uid in run["player_hp"]:
                        heal   = _roll(item["heal_expr"])
                        max_hp = run["player_max_hp"].get(target_uid, 999)
                        old_hp = run["player_hp"].get(target_uid, 0)
                        actual = min(max_hp, old_hp + heal) - old_hp
                        run["player_hp"][target_uid] = old_hp + actual
                        if target_uid in run.get("downed", {}) and run["player_hp"][target_uid] > 0:
                            del run["downed"][target_uid]
                            rev = next((n for u, n in run["participants"] if u == target_uid), target_uid)
                            round_lines.append(f"💉 **{rev}** is back on their feet!")
                        t_name = next((n for u, n in run["participants"] if u == target_uid), target_uid)
                        self.db.execute(
                            "UPDATE dnd_inventory SET qty=qty-1 WHERE user_id=? AND guild_id=? AND item_id=?",
                            (uid, gid, item_id))
                        self.db.execute(
                            "DELETE FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id=? AND qty<=0",
                            (uid, gid, item_id))
                        target_txt = "themselves" if target_uid == uid else f"**{t_name}**"
                        round_lines.append(
                            f"🧪 **{name}** uses a {item['name']} on {target_txt} → +{actual} HP *(bonus)*")
                        run["log"].append({"type": "item_use", "uid": uid, "name": name,
                            "item": item_id, "target": target_uid, "heal": actual, "round": rnd})
                    continue

                elif bonus_act == "taunt":
                    run.setdefault("taunt_targets", set()).add(uid)
                    round_lines.append(f"🗣️ **{name}** taunts **{enemy['name']}** — they'll focus on you!")
                    run["log"].append({"type": "bonus", "uid": uid, "name": name,
                                       "action": "taunt", "round": rnd})
                    continue

                # ── Class feature bonus actions ───────────────────────────────
                run["features_used"].setdefault(uid, set()).add(fid)

                if fid == "second_wind":
                    heal   = _roll(f"1d10+{level}")
                    max_hp = run["player_max_hp"].get(uid, 999)
                    old_hp = run["player_hp"].get(uid, 0)
                    actual = min(max_hp, old_hp + heal) - old_hp
                    run["player_hp"][uid] = old_hp + actual
                    round_lines.append(f"🌬️ **{name}** Second Wind → **+{actual} HP** *(bonus)*")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "heal": actual, "round": rnd})

                elif fid == "rage":
                    run["raging_uids"].add(uid)
                    round_lines.append(f"💢 **{name}** enters a **RAGE!** *(bonus — ×2 damage all combat)*")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                elif fid == "cunning_action":
                    cunning_dodgers.add(uid)
                    round_lines.append(f"🕵️ **{name}** Cunning Action — Dodge *(bonus — half enemy damage this round)*")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                elif fid == "hunters_mark":
                    run.setdefault("hunters_mark_uids", set()).add(uid)
                    round_lines.append(f"🎯 **{name}** marks the target *(bonus — +1d6 to all attacks)*")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                elif fid == "ensnaring_strike":
                    run.setdefault("ensnaring_uids", set()).add(uid)
                    round_lines.append(f"🌿 **{name}** arms **Ensnaring Strike** *(next ranged hit restrains — enemy ATK −2)*")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                elif fid == "hail_of_thorns":
                    run.setdefault("hail_uids", set()).add(uid)
                    round_lines.append(f"🌪️ **{name}** primes **Hail of Thorns** *(next ranged hit +1d10 piercing)*")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                elif fid == "vanish":
                    run.setdefault("vanish_uids", set()).add(uid)
                    round_lines.append(f"👁️ **{name}** Vanishes into shadow *(half damage from next hit this round)*")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                elif fid == "beast_protect":
                    t_stats_bp = self._get_char_combat_stats(uid, gid)
                    if t_stats_bp and t_stats_bp["level"] >= 7:
                        run.setdefault("beast_protect_uids", set()).add(uid)
                        round_lines.append(f"🛡️ **{name}**'s beast intercepts *(half damage from next hit this round)*")
                        run["log"].append({"type": "feature", "uid": uid, "name": name,
                                           "feature": fid, "round": rnd})
                    else:
                        round_lines.append(f"🛡️ **{name}** tried Beast Guard but isn't Lv 7+ yet!")

                elif fid == "shield_spell":
                    run["shield_spell_ac"].add(uid)
                    round_lines.append(f"🛡️ **{name}** Shield! +5 AC until next turn *(bonus)*")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                elif fid == "misty_step":
                    run.setdefault("misty_step_uids", set()).add(uid)
                    round_lines.append(f"💨 **{name}** Misty Step — teleports away *(half damage from next hit)*")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                elif fid == "counterspell":
                    run.setdefault("counterspell_uids", set()).add(uid)
                    round_lines.append(f"🚫 **{name}** Counterspell! **{enemy['name']}** is disrupted — skips their attack this round!")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                elif fid in ("lay_on_hands", "healing_word"):
                    t_uid    = bonus.get("target_uid", uid)
                    # Paladin Lay on Hands uses CHA; Cleric uses WIS
                    heal_mod = cha if (fid == "lay_on_hands" and stats and stats["char_class"] == "paladin") else wis
                    heal     = max(1, random.randint(1, 8) + heal_mod) if fid == "lay_on_hands" \
                               else max(1, random.randint(1, 4) + wis)
                    if fid == "healing_word" and stats:
                        sc_heal = _get_subclass(self.db, uid, gid, stats["char_class"])
                        if sc_heal == "life":
                            heal += 3
                            life_tag = " *(+3 Life)*"
                        else:
                            life_tag = ""
                    else:
                        life_tag = ""
                    max_hp = run["player_max_hp"].get(t_uid, 999)
                    old_hp = run["player_hp"].get(t_uid, 0)
                    actual = min(max_hp, old_hp + heal) - old_hp
                    run["player_hp"][t_uid] = old_hp + actual
                    if t_uid in run.get("downed", {}) and run["player_hp"][t_uid] > 0:
                        del run["downed"][t_uid]
                        rev_name = next((n for u, n in run["participants"] if u == t_uid), t_uid)
                        round_lines.append(f"💉 **{rev_name}** is back on their feet!")
                    t_name   = next((n for u, n in run["participants"] if u == t_uid), t_uid)
                    feat_lbl = "Lay on Hands" if fid == "lay_on_hands" else "Healing Word"
                    emoji    = "✨" if fid == "lay_on_hands" else "🙏"
                    who      = "themselves" if t_uid == uid else f"**{t_name}**"
                    round_lines.append(f"{emoji} **{name}** {feat_lbl} on {who} → **+{actual} HP**{life_tag} *(bonus)*")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "target": t_uid, "heal": actual, "round": rnd})

                elif fid == "frenzy_attack":
                    if uid not in run.get("raging_uids", set()):
                        round_lines.append(f"🔥 **{name}** tried Frenzy but isn't raging!")
                    elif stats:
                        _fa_tidx = _clamp_to_alive(view.enemy_targets.get(uid, 0))
                        fr = random.randint(1, 20)
                        ft = fr + stats["atk_bonus"]
                        if fr == 20 or ft >= enemy["ac"]:
                            fd1 = _roll(stats["dmg_expr"])
                            if fr == 20:
                                fd2 = _roll(stats["dmg_expr"])
                                fdmg = (fd1 + fd2) * 2
                                round_lines.append(f"🔥 **{name}** Frenzy ✨CRIT! → **{fdmg} dmg** *(rage ×2)*")
                            else:
                                fdmg = fd1 * 2
                                round_lines.append(f"🔥 **{name}** Frenzy attack → **{fdmg} dmg** *(rage ×2)*")
                            enemies[_fa_tidx]["hp"] = max(0, enemies[_fa_tidx]["hp"] - fdmg)
                            last_hitter = (uid, name)
                        else:
                            round_lines.append(f"🔥 **{name}** Frenzy attack missed! (rolled {fr})")
                        run["log"].append({"type": "feature", "uid": uid, "name": name,
                                           "feature": fid, "round": rnd})

                elif fid == "eldritch_spell":
                    _es_tidx = _clamp_to_alive(view.enemy_targets.get(uid, 0))
                    es_dmg = random.randint(1, 8)
                    enemies[_es_tidx]["hp"] = max(0, enemies[_es_tidx]["hp"] - es_dmg)
                    last_hitter = (uid, name)
                    round_lines.append(f"🔮 **{name}** War Magic — Booming Blade → **{es_dmg} force dmg** *(auto-hit)*")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "dmg": es_dmg, "round": rnd})

                elif fid == "mage_hand":
                    run.setdefault("arcane_distraction", set()).add(uid)
                    round_lines.append(f"🎩 **{name}** Mage Hand distracts **{enemy['name']}** — disadvantage on their next attack!")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                elif fid == "guided_strike":
                    run.setdefault("guided_strike", set()).add(uid)
                    round_lines.append(f"✝️ **{name}** channels Guided Strike — +10 to next attack roll!")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                elif fid == "sacred_weapon":
                    run.setdefault("sacred_weapon_uids", set()).add(uid)
                    cha_mod = stats["mods"]["charisma"] if stats else 0
                    round_lines.append(f"✨ **{name}** Sacred Weapon — +{cha_mod} to all attack rolls this combat!")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                elif fid == "natures_wrath":
                    run["natures_wrath_active"] = True
                    round_lines.append(f"🌿 **{name}** Nature's Wrath — **{enemy['name']}** is restrained! *(−2 ATK next round)*")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                elif fid == "vow_of_enmity":
                    run.setdefault("vow_of_enmity", set()).add(uid)
                    round_lines.append(f"⚡ **{name}** Vow of Enmity — advantage on all attacks this combat!")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                elif fid == "superiority_die":
                    run.setdefault("superiority_die", set()).add(uid)
                    round_lines.append(f"⚔️ **{name}** Superiority Die readied — +1d8 to next attack!")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                # ── EK: Shield spell ──────────────────────────────────────────
                elif fid == "ek_shield":
                    run["shield_spell_ac"].add(uid)
                    round_lines.append(f"🛡️ **{name}** Shield! +5 AC until next turn *(bonus)*")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                # ── EK: War Magic bonus weapon attack ─────────────────────────
                elif fid == "war_magic_atk" and stats:
                    main_act = view.actions.get(uid)
                    fire_bolted = (isinstance(main_act, dict)
                                   and main_act.get("feature_id") == "fire_bolt")
                    if not fire_bolted:
                        round_lines.append(
                            f"⚔️ **{name}** War Magic Strike — no spell cast this round *(fizzles)*")
                    else:
                        _wm_tidx = _clamp_to_alive(view.enemy_targets.get(uid, 0))
                        wm_r = random.randint(1, 20)
                        wm_t = wm_r + stats["atk_bonus"]
                        if wm_r == 20 or wm_t >= enemy["ac"]:
                            wd1 = _roll(stats["dmg_expr"])
                            if wm_r == 20:
                                wd2   = _roll(stats["dmg_expr"])
                                wdmg  = wd1 + wd2
                                wm_txt = f"✨CRIT {wd1}+{wd2}=**{wdmg}**"
                            else:
                                wdmg   = wd1
                                wm_txt = f"**{wdmg}**"
                            enemies[_wm_tidx]["hp"] = max(0, enemies[_wm_tidx]["hp"] - wdmg)
                            last_hitter = (uid, name)
                            round_lines.append(
                                f"⚔️ **{name}** War Magic Strike → {wm_txt} dmg *(bonus)*")
                        else:
                            round_lines.append(
                                f"⚔️ **{name}** War Magic Strike missed! (rolled {wm_r}) *(bonus)*")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                # ── Sharpshooter stance ───────────────────────────────────────
                elif fid == "sharpshooter_stance":
                    run["sharpshooter_stance"].add(uid)
                    round_lines.append(
                        f"🎯 **{name}** Sharpshooter Stance — next ranged attack: −5 to hit, +10 dmg *(bonus)*")
                    run["log"].append({"type": "feature", "uid": uid, "name": name,
                                       "feature": fid, "round": rnd})

                # ── Battle Master maneuvers ───────────────────────────────────
                elif fid in ("bm_precision", "bm_trip", "bm_disarm", "bm_riposte", "bm_menacing"):
                    if run.get("sup_dice", {}).get(uid, 0) <= 0:
                        round_lines.append(f"🎲 **{name}** — no Superiority Dice left!")
                    else:
                        die_type = run.get("sup_die_type", {}).get(uid, "1d8")
                        die_val  = _sup_die_roll(die_type)
                        run["sup_dice"][uid] -= 1
                        if fid == "bm_precision":
                            run.setdefault("bm_pending", {})[uid] = {"type": "precision", "die": die_val}
                            round_lines.append(
                                f"🎯 **{name}** Precision Attack — +{die_val} to ATK roll *(sup die {die_type})*")
                        elif fid == "bm_trip":
                            run.setdefault("bm_pending", {})[uid] = {"type": "trip", "die": die_val}
                            round_lines.append(
                                f"🦵 **{name}** Trip Attack readied — +{die_val} dmg + trip on hit *(sup die {die_type})*")
                        elif fid == "bm_disarm":
                            run.setdefault("bm_pending", {})[uid] = {"type": "disarm", "die": die_val}
                            round_lines.append(
                                f"🔓 **{name}** Disarming Strike readied — +{die_val} dmg + disarm on hit *(sup die {die_type})*")
                        elif fid == "bm_menacing":
                            run.setdefault("bm_pending", {})[uid] = {"type": "menacing", "die": die_val}
                            round_lines.append(
                                f"😤 **{name}** Menacing Attack readied — +{die_val} dmg + taunt on hit *(sup die {die_type})*")
                        elif fid == "bm_riposte":
                            run["bm_riposte_set"].add(uid)
                            run.setdefault("bm_pending", {})[uid] = {"type": "riposte", "die": die_val}
                            round_lines.append(
                                f"🔄 **{name}** Riposte readied — counter +{die_val} dmg if enemy misses! *(sup die {die_type})*")
                        run["log"].append({"type": "feature", "uid": uid, "name": name,
                                           "feature": fid, "die": die_val, "round": rnd})

            # ── Process main actions ───────────────────────────────────────
            for uid, name in run["participants"]:
                if uid not in active:
                    continue
                if all(e["hp"] <= 0 for e in enemies):
                    break
                action = view.actions.get(uid, "dodge")
                if uid in run["fled"]:
                    continue  # already fled via bonus action

                if action == "flee":
                    run["fled"].add(uid)
                    round_lines.append(f"🏃 **{name}** flees the battle!")
                    run["log"].append({"type": "flee", "uid": uid, "name": name, "round": rnd})

                elif action == "dodge":
                    dodgers.add(uid)
                    round_lines.append(f"🛡️ **{name}** takes a defensive stance.")

                elif isinstance(action, dict) and action.get("action") == "help":
                    t_uid  = action["target_uid"]
                    t_name = next((n for u, n in run["participants"] if u == t_uid), t_uid)
                    if t_uid in run.get("downed", {}):
                        stats   = self._get_char_combat_stats(uid, gid)
                        wis_mod = stats["mods"]["wisdom"] if stats else 0
                        roll    = random.randint(1, 20) + wis_mod
                        if roll >= 10:
                            run["player_hp"][t_uid] = 1
                            del run["downed"][t_uid]
                            round_lines.append(
                                f"🤝 **{name}** stabilizes **{t_name}** (Medicine {roll}) → back at 1 HP!")
                            run["log"].append({"type": "help_stabilize", "uid": uid,
                                               "target": t_uid, "roll": roll, "round": rnd})
                        else:
                            round_lines.append(
                                f"🤝 **{name}** tries to help **{t_name}** but fails (Medicine {roll})")
                    else:
                        run.setdefault("helped_next_attack", {})[t_uid] = 4
                        round_lines.append(
                            f"🤝 **{name}** helps **{t_name}** — advantage on next attack! *(+4 to hit)*")
                        run["log"].append({"type": "help_attack", "uid": uid, "target": t_uid, "round": rnd})

                elif isinstance(action, dict) and action.get("action") == "use_item":
                    item_id    = action["item_id"]
                    target_uid = action["target_uid"]
                    item       = self._find_item(item_id)
                    if item and item.get("heal_expr") and target_uid in run["player_hp"]:
                        heal   = _roll(item["heal_expr"])
                        max_hp = run["player_max_hp"].get(target_uid, 999)
                        old_hp = run["player_hp"].get(target_uid, 0)
                        actual = min(max_hp, old_hp + heal) - old_hp
                        run["player_hp"][target_uid] = old_hp + actual
                        if target_uid in run.get("downed", {}) and run["player_hp"][target_uid] > 0:
                            del run["downed"][target_uid]
                            rev_name = next((n for u, n in run["participants"] if u == target_uid), target_uid)
                            round_lines.append(f"💉 **{rev_name}** is back on their feet!")
                        t_name = next((n for u, n in run["participants"] if u == target_uid), target_uid)
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

                elif action == "attack" or (isinstance(action, dict) and action.get("action") == "attack"):
                    _atk_tidx = _clamp_to_alive(
                        action.get("target_idx", 0) if isinstance(action, dict) else
                        view.enemy_targets.get(uid, 0))
                    e_hp = enemies[_atk_tidx]["hp"]
                    stats = self._get_char_combat_stats(uid, gid)
                    if stats:
                        char_class = stats["char_class"]
                        level      = stats["level"]
                        n_atk      = _n_attacks(char_class, level)
                        is_raging  = uid in run.get("raging_uids", set())
                        is_marked  = uid in run.get("hunters_mark_uids", set())
                        imp_smite  = char_class == "paladin" and level >= 9
                        help_bonus = run.setdefault("helped_next_attack", {}).pop(uid, 0)
                        b_txt      = f"{stats['atk_bonus']:+d}"
                        rage_txt   = " 💢*(rage ×2)*" if is_raging else ""
                        help_txt   = f" 🤝*(+{help_bonus})*" if help_bonus else ""

                        subclass           = _get_subclass(self.db, uid, gid, char_class)
                        crit_thresh        = (18 if level >= 15 else 19) if subclass == "champion" else 20
                        hunter_slayer_used = False
                        cha_mod            = stats["mods"]["charisma"]
                        is_ranged          = stats.get("is_ranged", False)
                        handed             = stats.get("handed", 1)
                        fs                 = run.get("fighting_style", {}).get(uid)
                        p_feat             = _get_human_feat(self.db, uid, gid)
                        dwarf_tr           = _get_dwarf_trait(self.db, uid, gid)
                        fe_type            = run.get("favored_enemy", {}).get(uid)
                        fe_add             = 2 if fe_type and _enemy_matches_type(enemy["name"], fe_type) else 0
                        any_crit           = False

                        total_dmg  = 0
                        first_roll = first_total = first_crit = 0
                        first_ann  = ""
                        hit_parts: list[str] = []
                        for i in range(n_atk):
                            roll  = random.randint(1, 20)
                            bonus = help_bonus if i == 0 else 0
                            atk_ann: list[str] = []

                            if uid in run.get("disadvantage_uids", set()):
                                roll = min(roll, random.randint(1, 20))
                                atk_ann.append("*(disadv)*")

                            if uid in run.get("vow_of_enmity", set()):
                                roll2b = random.randint(1, 20)
                                if roll2b > roll:
                                    roll = roll2b
                                    atk_ann.append("*(Vow of Enmity)*")

                            if subclass == "divination" and uid not in run.get("portent_used", set()) and i == 0:
                                roll2  = random.randint(1, 20)
                                roll   = max(roll, roll2)
                                run.setdefault("portent_used", set()).add(uid)
                                atk_ann.append("*(Portent)*")

                            if subclass == "assassin" and surprise and rnd == 1:
                                crit = True
                            else:
                                crit = roll >= crit_thresh

                            total = roll + stats["atk_bonus"] + bonus

                            if subclass == "illusion" and rnd == 1 and i == 0:
                                total += 4
                                atk_ann.append("*(+4 Illusion)*")

                            if subclass == "knowledge":
                                total += 2
                                atk_ann.append("*(+2 Knowledge)*")

                            if uid in run.get("guided_strike", set()) and i == 0:
                                total += 10
                                atk_ann.append("*(+10 Guided Strike!)*")
                                run["guided_strike"].discard(uid)

                            if uid in run.get("sacred_weapon_uids", set()):
                                total += cha_mod
                                atk_ann.append("*(Sacred Weapon)*")

                            # Fighting style: Archery +2 ranged ATK
                            if fs == "archery" and is_ranged:
                                total += 2
                                atk_ann.append("*(+2 Archery)*")

                            # Dwarf Battle-Born: +1 melee ATK
                            if dwarf_tr == "battle_born" and not is_ranged:
                                total += 1
                                atk_ann.append("*(+1 Battle-Born)*")

                            # BM Precision: +die to first attack roll
                            bm_pend = run.get("bm_pending", {}).get(uid)
                            if bm_pend and bm_pend["type"] == "precision" and i == 0:
                                total += bm_pend["die"]
                                atk_ann.append(f"*(+{bm_pend['die']} Precision)*")
                                del run["bm_pending"][uid]
                                bm_pend = None

                            # Sharpshooter: -5 to hit, +10 dmg on hit (ranged only)
                            ss_active = (uid in run.get("sharpshooter_stance", set())
                                         and is_ranged and i == 0)
                            if ss_active:
                                total -= 5
                                atk_ann.append("*(-5 Sharpshooter)*")
                                run["sharpshooter_stance"].discard(uid)

                            if i == 0:
                                first_roll  = roll
                                first_total = total
                                first_crit  = crit
                                first_ann   = " ".join(atk_ann)

                            eff_ac = enemy["ac"] - run.get("enemy_ac_penalty", 0)
                            if crit or total >= eff_ac:
                                # Damage roll — GWF rerolls 1s and 2s
                                if fs == "great_weapon_fighting" and not is_ranged:
                                    dmg1 = _roll_gwf(stats["dmg_expr"])
                                else:
                                    dmg1 = _roll(stats["dmg_expr"])
                                mark_add = random.randint(1, 6) if is_marked else 0
                                ism_add  = random.randint(1, 8) if imp_smite else 0
                                sup_add  = 0
                                if uid in run.get("superiority_die", set()) and i == 0:
                                    sup_add = random.randint(1, 8)
                                    run["superiority_die"].discard(uid)
                                cs_add = 0
                                if subclass == "hunter" and e_hp < e_max and not hunter_slayer_used:
                                    cs_add = random.randint(1, 8)
                                    hunter_slayer_used = True
                                # Dueling: +2 dmg for one-handed melee
                                duel_add = (2 if fs == "dueling" and not is_ranged
                                               and handed == 1 else 0)
                                # Sharpshooter +10 on hit
                                ss_dmg = 10 if ss_active else 0
                                # BM on-hit effects
                                bm_pend = run.get("bm_pending", {}).get(uid)
                                bm_die  = 0
                                bm_note = ""
                                if bm_pend and bm_pend["type"] in ("trip", "disarm", "menacing") and i == 0:
                                    bm_die  = bm_pend["die"]
                                    if bm_pend["type"] == "trip":
                                        run["enemy_ac_penalty"] = max(run.get("enemy_ac_penalty",0), 2)
                                        bm_note = f"+{bm_die}🦵*(trip)*"
                                    elif bm_pend["type"] == "disarm":
                                        run["enemy_atk_penalty"] = max(run.get("enemy_atk_penalty",0), 2)
                                        bm_note = f"+{bm_die}🔓*(disarm)*"
                                    elif bm_pend["type"] == "menacing":
                                        run.setdefault("taunt_targets", set()).add(uid)
                                        bm_note = f"+{bm_die}😤*(taunt)*"
                                    del run["bm_pending"][uid]
                                # Hail of Thorns: +1d10 on first ranged hit
                                hail_add = 0
                                if uid in run.get("hail_uids", set()) and is_ranged and i == 0:
                                    hail_add = random.randint(1, 10)
                                    run["hail_uids"].discard(uid)
                                # Ensnaring Strike: restrain on first ranged hit
                                ensnare_txt = ""
                                if uid in run.get("ensnaring_uids", set()) and is_ranged and i == 0:
                                    run["enemy_atk_penalty"] = max(run.get("enemy_atk_penalty", 0), 2)
                                    run["ensnaring_uids"].discard(uid)
                                    ensnare_txt = "🌿*(restrained!)*"
                                if crit:
                                    if fs == "great_weapon_fighting" and not is_ranged:
                                        dmg2 = _roll_gwf(stats["dmg_expr"])
                                    else:
                                        dmg2      = _roll(stats["dmg_expr"])
                                    mark_add2 = random.randint(1, 6) if is_marked else 0
                                    ism_add2  = random.randint(1, 8) if imp_smite else 0
                                    dmg       = (dmg1 + dmg2 + mark_add + mark_add2
                                                 + ism_add + ism_add2 + sup_add + cs_add
                                                 + duel_add + ss_dmg + bm_die + fe_add + hail_add)
                                    any_crit  = True
                                else:
                                    dmg = (dmg1 + mark_add + ism_add + sup_add + cs_add
                                           + duel_add + ss_dmg + bm_die + fe_add + hail_add)
                                if is_raging:
                                    dmg *= 2
                                e_hp = max(0, e_hp - dmg)
                                total_dmg += dmg
                                last_hitter = (uid, name)
                                extras = (
                                    (f"+{mark_add}🎯" if mark_add else "")
                                    + (f"+{ism_add}✝️" if ism_add else "")
                                    + (f"+{sup_add}⚔️" if sup_add else "")
                                    + (f"+{cs_add}💥*(Colossus)*" if cs_add else "")
                                    + (f"+{duel_add}⚔️*(duel)*" if duel_add else "")
                                    + (f"+{ss_dmg}🎯*(SS)*" if ss_dmg else "")
                                    + (f"+{fe_add}🏹*(favored)*" if fe_add else "")
                                    + (f"+{hail_add}🌪️*(thorns)*" if hail_add else "")
                                    + (ensnare_txt if ensnare_txt else "")
                                    + (bm_note if bm_note else "")
                                )
                                hit_parts.append(f"✨CRIT **{dmg}**{extras}" if crit else f"**{dmg}**{extras}")

                                # GWM: auto bonus attack after crit or kill
                                if (any_crit or e_hp <= 0) and p_feat == "great_weapon_master" and not is_ranged:
                                    gwm_r = random.randint(1, 20)
                                    gwm_t = gwm_r + stats["atk_bonus"]
                                    if gwm_r == 20 or gwm_t >= enemy["ac"]:
                                        gd1  = _roll(stats["dmg_expr"])
                                        if gwm_r == 20:
                                            gd2  = _roll(stats["dmg_expr"])
                                            gdmg = gd1 + gd2
                                            hit_parts.append(f"💥GWM ✨CRIT **{gdmg}**")
                                        else:
                                            gdmg = gd1
                                            hit_parts.append(f"💥GWM **{gdmg}**")
                                        e_hp = max(0, e_hp - gdmg)
                                        total_dmg += gdmg
                                        last_hitter = (uid, name)
                                    else:
                                        hit_parts.append(f"💥GWM miss")
                                    any_crit = False  # only trigger once
                            else:
                                hit_parts.append("miss")

                            # Beast companion always attacks on first attack, win or lose
                            if uid in run.get("beast_companion", set()) and i == 0:
                                _comp    = run.get("beast_companion_item", {}).get(uid)
                                if _comp:
                                    _b_dmg  = _comp.get("beast_dmg",     "1d6+2")
                                    _b_amod = _comp.get("beast_atk_mod", -2)
                                    _b_emj  = _comp.get("emoji",         "🐾")
                                    _b_nm   = _comp.get("beast_name",    "Beast")
                                else:
                                    _b_dmg  = "1d6+2"
                                    _b_amod = -2
                                    _b_emj  = "🐺"
                                    _b_nm   = "Wolf"
                                _cn_row = self.db.execute(
                                    "SELECT choice_val FROM dnd_character_choices "
                                    "WHERE user_id=? AND guild_id=? AND choice_key=?",
                                    (uid, gid, "companion_name"))
                                if _cn_row:
                                    _b_nm = _cn_row[0][0]
                                b_atk = stats["atk_bonus"] + _b_amod
                                br    = random.randint(1, 20)
                                bt    = br + b_atk
                                if br == 20 or bt >= enemy["ac"]:
                                    bd   = _roll(_b_dmg)
                                    if br == 20:
                                        bd += _roll(_b_dmg)
                                    e_hp = max(0, e_hp - bd)
                                    total_dmg += bd
                                    crit_tag = " ✨CRIT!" if br == 20 else ""
                                    hit_parts.append(f"{_b_emj} {_b_nm}{crit_tag} **{bd}**")
                                else:
                                    hit_parts.append(f"{_b_emj} {_b_nm} miss")

                            if e_hp <= 0:
                                break

                        # TWF: auto offhand attack for two_weapon_fighting + melee
                        if fs == "two_weapon_fighting" and not is_ranged and e_hp > 0:
                            twf_r = random.randint(1, 20)
                            twf_t = twf_r + stats["atk_bonus"]
                            if twf_r == 20 or twf_t >= enemy["ac"]:
                                td1  = _roll(stats["dmg_expr"])
                                if twf_r == 20:
                                    td2  = _roll(stats["dmg_expr"])
                                    tdmg = td1 + td2
                                    hit_parts.append(f"⚔️Offhand ✨CRIT **{tdmg}**")
                                else:
                                    tdmg = td1
                                    hit_parts.append(f"⚔️Offhand **{tdmg}**")
                                e_hp = max(0, e_hp - tdmg)
                                total_dmg += tdmg
                                last_hitter = (uid, name)
                            else:
                                hit_parts.append("⚔️Offhand miss")

                        ann_sfx = (f" {first_ann}" if first_ann else "")
                        if n_atk == 1 and fs != "two_weapon_fighting":
                            result = hit_parts[0] if hit_parts else "miss"
                            if result == "miss":
                                round_lines.append(
                                    f"⚔️ **{name}** rolled {first_roll}{help_txt} {b_txt} = **{first_total}**{ann_sfx} vs AC {enemy['ac']} → MISS")
                                run["log"].append({"type": "attack", "uid": uid, "name": name,
                                    "roll": first_roll, "total": first_total, "dmg": 0,
                                    "hit": False, "crit": False, "round": rnd, "enemy": enemy["name"]})
                            else:
                                round_lines.append(
                                    f"⚔️ **{name}** rolled {first_roll}{help_txt} {b_txt} = **{first_total}**{ann_sfx} vs AC {enemy['ac']} → {result}{rage_txt}")
                                run["log"].append({"type": "attack", "uid": uid, "name": name,
                                    "roll": first_roll, "total": first_total, "dmg": total_dmg,
                                    "hit": True, "crit": first_crit, "round": rnd, "enemy": enemy["name"]})
                        else:
                            round_lines.append(
                                f"⚔️ **{name}** {n_atk}× attacks{help_txt} → {' | '.join(hit_parts)}{rage_txt}")
                            run["log"].append({"type": "attack", "uid": uid, "name": name,
                                "n_attacks": n_atk, "dmg": total_dmg, "round": rnd, "enemy": enemy["name"]})
                    else:
                        round_lines.append(f"⚔️ **{name}** swings wildly and misses!")
                    enemies[_atk_tidx]["hp"] = e_hp  # write back to the targeted enemy

                elif isinstance(action, dict) and action.get("action") == "feature":
                    fid   = action["feature_id"]
                    stats = self._get_char_combat_stats(uid, gid)
                    level = stats["level"] if stats else 1
                    wis   = stats["mods"]["wisdom"] if stats else 0
                    # Feature actions auto-target the first alive enemy
                    _feat_tidx = _first_alive_idx()
                    e_hp = enemies[_feat_tidx]["hp"]
                    # Action Surge uses its own counter; everything else uses features_used
                    if fid == "action_surge":
                        run.setdefault("action_surge_uses", {})[uid] = max(
                            0, run["action_surge_uses"].get(uid, 0) - 1)
                    else:
                        run["features_used"].setdefault(uid, set()).add(fid)

                    if fid == "action_surge" and stats:
                        surge_n    = max(2, _n_attacks(stats["char_class"], stats["level"]))
                        surge_hits: list[str] = []
                        fs_surge   = run.get("fighting_style", {}).get(uid)
                        is_ranged_s = stats.get("is_ranged", False)
                        subclass_s  = _get_subclass(self.db, uid, gid, stats["char_class"])
                        for _ in range(surge_n):
                            r = random.randint(1, 20)
                            t = r + stats["atk_bonus"]
                            if fs_surge == "archery" and is_ranged_s:
                                t += 2
                            c = r == 20
                            if c or t >= enemy["ac"]:
                                d1 = _roll(stats["dmg_expr"])
                                if c:
                                    d2 = _roll(stats["dmg_expr"])
                                    d  = d1 + d2
                                    # EK Arcane Charge: +1d6 force per attack at Lv15+
                                    if subclass_s == "eldritch_knight" and level >= 15:
                                        ac_bonus = random.randint(1, 6)
                                        d += ac_bonus
                                        surge_hits.append(f"✨CRIT {d1}+{d2}+{ac_bonus}⚡=**{d}**")
                                    else:
                                        surge_hits.append(f"✨CRIT {d1}+{d2}=**{d}**")
                                else:
                                    d = d1
                                    if subclass_s == "eldritch_knight" and level >= 15:
                                        ac_bonus = random.randint(1, 6)
                                        d += ac_bonus
                                        surge_hits.append(f"**{d}**(+{ac_bonus}⚡)")
                                    else:
                                        surge_hits.append(f"**{d}**")
                                if uid in run.get("raging_uids", set()):
                                    d *= 2
                                e_hp = max(0, e_hp - d)
                                last_hitter = (uid, name)
                            else:
                                surge_hits.append("miss")
                        round_lines.append(
                            f"⚡ **{name}** Action Surge ×{surge_n}! → {' | '.join(surge_hits)}")
                        run["log"].append({"type": "feature", "uid": uid, "name": name,
                                           "feature": fid, "round": rnd})
                        enemies[_feat_tidx]["hp"] = e_hp

                    elif fid == "fire_bolt" and stats:
                        fb_dice = 1 if level < 5 else (2 if level < 11 else (3 if level < 17 else 4))
                        fb_dmg  = sum(random.randint(1, 10) for _ in range(fb_dice))
                        e_hp    = max(0, e_hp - fb_dmg)
                        last_hitter = (uid, name)
                        run.setdefault("fire_bolt_rnd", {})[uid] = rnd
                        es_note = ""
                        if level >= 10:
                            run.setdefault("eldritch_strike_rnd", {})[uid] = rnd
                            es_note = " *(Eldritch Strike active!)*"
                        round_lines.append(
                            f"🔥 **{name}** Fire Bolt ({fb_dice}d10) → **{fb_dmg} fire dmg** *(auto-hit)*{es_note}")
                        run["log"].append({"type": "feature", "uid": uid, "name": name,
                                           "feature": fid, "dmg": fb_dmg, "round": rnd})
                        enemies[_feat_tidx]["hp"] = e_hp

                    elif fid == "sneak_attack" and stats:
                        sneak_dice = max(1, (level + 1) // 2)
                        r = random.randint(1, 20)
                        t = r + stats["atk_bonus"]
                        c = r == 20
                        if c or t >= enemy["ac"]:
                            d1  = _roll(stats["dmg_expr"])
                            snk = sum(random.randint(1, 6) for _ in range(sneak_dice))
                            if c:
                                d2   = _roll(stats["dmg_expr"])
                                snk2 = sum(random.randint(1, 6) for _ in range(sneak_dice))
                                dmg  = d1 + d2 + snk + snk2
                                round_lines.append(f"🗡️ **{name}** Sneak Attack ✨CRIT! → **{dmg} dmg** (+{sneak_dice}d6)")
                            else:
                                dmg = d1 + snk
                                round_lines.append(f"🗡️ **{name}** Sneak Attack → **{dmg} dmg** (+{sneak_dice}d6)")
                            e_hp = max(0, e_hp - dmg)
                            last_hitter = (uid, name)
                        else:
                            round_lines.append(f"🗡️ **{name}** Sneak Attack missed!")
                        run["log"].append({"type": "feature", "uid": uid, "name": name,
                                           "feature": fid, "round": rnd})
                        enemies[_feat_tidx]["hp"] = e_hp

                    elif fid == "sacred_flame" and stats:
                        dmg = max(1, random.randint(1, 8) + wis)
                        e_hp = max(0, e_hp - dmg)
                        last_hitter = (uid, name)
                        round_lines.append(f"🔥 **{name}** Sacred Flame → **{dmg} radiant dmg** *(auto-hit)*")
                        run["log"].append({"type": "feature", "uid": uid, "name": name,
                                           "feature": fid, "dmg": dmg, "round": rnd})
                        enemies[_feat_tidx]["hp"] = e_hp

                    elif fid == "magic_missile" and stats:
                        n_bolts   = min(6, 3 + (level - 1) // 3)
                        total_dmg = sum(random.randint(1, 4) + 1 for _ in range(n_bolts))
                        mm_sc = _get_subclass(self.db, uid, gid, stats["char_class"])
                        sculpt_add = 0
                        sculpt_txt = ""
                        if mm_sc == "evocation":
                            sculpt_add = random.randint(1, 4)
                            total_dmg += sculpt_add
                            sculpt_txt = f" *(+{sculpt_add} Sculpt)*"
                        e_hp      = max(0, e_hp - total_dmg)
                        last_hitter = (uid, name)
                        bolt_s = "bolts" if n_bolts != 1 else "bolt"
                        round_lines.append(
                            f"✨ **{name}** Magic Missile — {n_bolts} {bolt_s} → **{total_dmg} dmg** *(auto-hit)*{sculpt_txt}")
                        run["log"].append({"type": "feature", "uid": uid, "name": name,
                                           "feature": fid, "dmg": total_dmg, "round": rnd})
                        enemies[_feat_tidx]["hp"] = e_hp

                    elif fid == "divine_smite" and stats:
                        r  = random.randint(1, 20)
                        t  = r + stats["atk_bonus"]
                        c  = r == 20
                        bx = f"{stats['atk_bonus']:+d}"
                        if c or t >= enemy["ac"]:
                            d1  = _roll(stats["dmg_expr"])
                            sm1 = random.randint(1, 8)
                            sm2 = random.randint(1, 8)
                            if c:
                                d2  = _roll(stats["dmg_expr"])
                                sm3 = random.randint(1, 8)
                                sm4 = random.randint(1, 8)
                                dmg = d1 + d2 + sm1 + sm2 + sm3 + sm4
                                round_lines.append(
                                    f"⚡ **{name}** Divine Smite ✨CRIT! → **{dmg} dmg** (+4d8 radiant)")
                            else:
                                dmg = d1 + sm1 + sm2
                                round_lines.append(
                                    f"⚡ **{name}** Divine Smite (rolled {r} {bx} = **{t}**) → **{dmg} dmg** (+2d8 radiant)")
                            e_hp = max(0, e_hp - dmg)
                            last_hitter = (uid, name)
                        else:
                            round_lines.append(
                                f"⚡ **{name}** Divine Smite missed! (rolled {r} {bx} = **{t}** vs AC {enemy['ac']})")
                        run["log"].append({"type": "feature", "uid": uid, "name": name,
                                           "feature": fid, "round": rnd})
                        enemies[_feat_tidx]["hp"] = e_hp

                    elif fid == "cure_wounds_rng" and stats:
                        wis_cw  = stats["mods"]["wisdom"]
                        heal    = max(1, random.randint(1, 8) + wis_cw)
                        max_hp  = run["player_max_hp"].get(uid, 999)
                        old_hp  = run["player_hp"].get(uid, 0)
                        actual  = min(max_hp, old_hp + heal) - old_hp
                        run["player_hp"][uid] = old_hp + actual
                        round_lines.append(f"💚 **{name}** Cure Wounds → **+{actual} HP** *(action)*")
                        run["log"].append({"type": "feature", "uid": uid, "name": name,
                                           "feature": fid, "heal": actual, "round": rnd})

                    elif fid == "burning_hands" and stats:
                        bh_dice = 3 + (level - 1) // 4
                        bh_dmg  = sum(random.randint(1, 6) for _ in range(bh_dice))
                        bh_sc   = _get_subclass(self.db, uid, gid, stats["char_class"])
                        bh_sculpt = 0
                        if bh_sc == "evocation":
                            bh_sculpt = random.randint(1, 4)
                            bh_dmg   += bh_sculpt
                        e_hp = max(0, e_hp - bh_dmg)
                        last_hitter = (uid, name)
                        sculpt_t = f" *(+{bh_sculpt} Sculpt)*" if bh_sculpt else ""
                        round_lines.append(
                            f"🔥 **{name}** Burning Hands ({bh_dice}d6) → **{bh_dmg} fire dmg** *(auto-hit)*{sculpt_t}")
                        run["log"].append({"type": "feature", "uid": uid, "name": name,
                                           "feature": fid, "dmg": bh_dmg, "round": rnd})
                        enemies[_feat_tidx]["hp"] = e_hp

                    elif fid == "thunderwave" and stats:
                        int_mod = stats["mods"]["intelligence"]
                        tw_dmg  = sum(random.randint(1, 8) for _ in range(2)) + int_mod
                        tw_dmg  = max(1, tw_dmg)
                        run["enemy_atk_penalty"] = max(run.get("enemy_atk_penalty", 0), 2)
                        e_hp = max(0, e_hp - tw_dmg)
                        last_hitter = (uid, name)
                        round_lines.append(
                            f"🌊 **{name}** Thunderwave → **{tw_dmg} thunder dmg** *(auto-hit)* · "
                            f"**{enemies[_feat_tidx]['name']}** is pushed back! *(ATK −2 next round)*")
                        run["log"].append({"type": "feature", "uid": uid, "name": name,
                                           "feature": fid, "dmg": tw_dmg, "round": rnd})
                        enemies[_feat_tidx]["hp"] = e_hp

                    elif fid == "scorching_ray" and stats:
                        sr_hits: list[str] = []
                        sr_total = 0
                        for _ in range(3):
                            sr_r = random.randint(1, 20)
                            sr_t = sr_r + stats["atk_bonus"]
                            if sr_r == 20 or sr_t >= enemy["ac"]:
                                sr_d1 = sum(random.randint(1, 6) for _ in range(2))
                                if sr_r == 20:
                                    sr_d2 = sum(random.randint(1, 6) for _ in range(2))
                                    sr_d  = sr_d1 + sr_d2
                                    sr_hits.append(f"✨CRIT **{sr_d}**")
                                else:
                                    sr_d  = sr_d1
                                    sr_hits.append(f"**{sr_d}**")
                                e_hp = max(0, e_hp - sr_d)
                                sr_total += sr_d
                                last_hitter = (uid, name)
                            else:
                                sr_hits.append("miss")
                        round_lines.append(
                            f"☀️ **{name}** Scorching Ray → {' | '.join(sr_hits)} *(total {sr_total} fire)*")
                        run["log"].append({"type": "feature", "uid": uid, "name": name,
                                           "feature": fid, "dmg": sr_total, "round": rnd})
                        enemies[_feat_tidx]["hp"] = e_hp

                    elif fid == "fireball" and stats:
                        fb_dmg = sum(random.randint(1, 6) for _ in range(8))
                        fb_sc  = _get_subclass(self.db, uid, gid, stats["char_class"])
                        fb_bonus = 0
                        if fb_sc == "evocation":
                            fb_bonus = max(0, stats["mods"]["intelligence"])
                            fb_dmg  += fb_bonus
                        e_hp = max(0, e_hp - fb_dmg)
                        last_hitter = (uid, name)
                        evoc_t = f" *(+{fb_bonus} Evocation)*" if fb_bonus else ""
                        round_lines.append(
                            f"💥 **{name}** FIREBALL! (8d6) → **{fb_dmg} fire dmg** *(auto-hit)*{evoc_t}")
                        run["log"].append({"type": "feature", "uid": uid, "name": name,
                                           "feature": fid, "dmg": fb_dmg, "round": rnd})
                        enemies[_feat_tidx]["hp"] = e_hp

                    elif fid == "volley" and stats:
                        if level < 11:
                            round_lines.append(f"🏹 **{name}** Volley requires Lv 11+!")
                        else:
                            vol_hits: list[str] = []
                            vol_fs = run.get("fighting_style", {}).get(uid)
                            vol_fe = run.get("favored_enemy", {}).get(uid)
                            vol_fe_add = 2 if vol_fe and _enemy_matches_type(enemy["name"], vol_fe) else 0
                            is_marked_v = uid in run.get("hunters_mark_uids", set())
                            for _ in range(2):
                                vr = random.randint(1, 20)
                                vt = vr + stats["atk_bonus"]
                                if vol_fs == "archery":
                                    vt += 2
                                if vr == 20 or vt >= enemy["ac"]:
                                    vd1 = _roll(stats["dmg_expr"])
                                    v_mark = random.randint(1, 6) if is_marked_v else 0
                                    if vr == 20:
                                        vd2  = _roll(stats["dmg_expr"])
                                        v_mark2 = random.randint(1, 6) if is_marked_v else 0
                                        vdmg = vd1 + vd2 + v_mark + v_mark2 + vol_fe_add
                                        vol_hits.append(f"✨CRIT **{vdmg}**")
                                    else:
                                        vdmg = vd1 + v_mark + vol_fe_add
                                        vol_hits.append(f"**{vdmg}**")
                                    e_hp = max(0, e_hp - vdmg)
                                    last_hitter = (uid, name)
                                else:
                                    vol_hits.append("miss")
                            round_lines.append(f"🏹 **{name}** Volley! → {' | '.join(vol_hits)}")
                            run["log"].append({"type": "feature", "uid": uid, "name": name,
                                               "feature": fid, "round": rnd})
                            enemies[_feat_tidx]["hp"] = e_hp

            # ── Enemy retaliates (not on surprise round 1) ─────────────────
            _counterspelled = bool(run.get("counterspell_uids"))
            run["counterspell_uids"] = set()
            if _counterspelled:
                round_lines.append(f"🚫 **{enemy['name']}** is disrupted — no retaliation this round!")
            if not enemy_first and not (surprise and rnd == 1) and not _counterspelled:
                non_fled = [uid for uid in active
                            if uid not in run["fled"] and run["player_hp"].get(uid, 0) > 0]
                taunt_uids = set(run.get("taunt_targets", set()))
                run["taunt_targets"] = set()
                # Each alive enemy attacks one random player
                for _ret_eobj in enemies:
                    if _ret_eobj["hp"] <= 0:
                        continue
                    if not non_fled:
                        break
                    taunt_now   = [u for u in taunt_uids if u in non_fled]
                    target_uid  = random.choice(taunt_now) if taunt_now else random.choice(non_fled)
                    target_name = next((n for u, n in run["participants"] if u == target_uid), target_uid)
                    stats       = self._get_char_combat_stats(target_uid, gid)
                    if stats:
                        e_atk_bonus = enemy["atk_bonus"]
                        ret_notes: list[str] = []

                        if run.get("natures_wrath_active"):
                            e_atk_bonus -= 2
                            run["natures_wrath_active"] = False
                            ret_notes.append("*(Restrained −2)*")

                        # BM Disarm penalty
                        e_atk_pen = run.get("enemy_atk_penalty", 0)
                        if e_atk_pen:
                            e_atk_bonus -= e_atk_pen
                            ret_notes.append(f"*(Disarmed −{e_atk_pen})*")

                        # EK Eldritch Strike: enemy -2 ATK if fire bolt hit this round
                        if run.get("eldritch_strike_rnd", {}).get(target_uid) == rnd:
                            e_atk_bonus -= 2
                            ret_notes.append("*(Eldritch Strike −2)*")

                        roll      = random.randint(1, 20)
                        total_atk = roll + e_atk_bonus

                        t_sc = _get_subclass(self.db, target_uid, gid, stats["char_class"])

                        if target_uid in run.get("arcane_distraction", set()):
                            roll2d = random.randint(1, 20)
                            roll   = min(roll, roll2d)
                            total_atk = roll + e_atk_bonus
                            run["arcane_distraction"].discard(target_uid)
                            ret_notes.append("*(Mage Hand disadv)*")

                        if target_uid in run.get("warding_flare", set()):
                            roll2w = random.randint(1, 20)
                            roll   = min(roll, roll2w)
                            total_atk = roll + e_atk_bonus
                            run["warding_flare"].discard(target_uid)
                            ret_notes.append("*(Warding Flare!)*")

                        in_dodge = target_uid in dodgers or target_uid in cunning_dodgers
                        # EK Shield: +5 AC temporarily
                        ek_ac    = 5 if target_uid in run.get("shield_spell_ac", set()) else 0
                        dodge_ac = stats["ac"] + (2 if in_dodge else 0) + ek_ac
                        if ek_ac:
                            ret_notes.append("*(Shield +5 AC)*")
                        note_sfx = (" " + " ".join(ret_notes)) if ret_notes else ""
                        if roll == 20 or total_atk >= dodge_ac:
                            dmg1 = _roll(enemy["dmg"])
                            if roll == 20:
                                dmg2 = _roll(enemy["dmg"])
                                dmg  = dmg1 + dmg2
                            else:
                                dmg  = dmg1
                            if in_dodge:
                                dmg = max(1, dmg // 2)
                            if target_uid in run.get("vanish_uids", set()):
                                dmg = max(1, dmg // 2)
                                run["vanish_uids"].discard(target_uid)
                                ret_notes.append("*(Vanish — half dmg)*")
                                note_sfx = (" " + " ".join(ret_notes)).rstrip()
                            if target_uid in run.get("misty_step_uids", set()):
                                dmg = max(1, dmg // 2)
                                run["misty_step_uids"].discard(target_uid)
                                ret_notes.append("*(Misty Step — half dmg)*")
                                note_sfx = (" " + " ".join(ret_notes)).rstrip()
                            if target_uid in run.get("beast_protect_uids", set()):
                                dmg = max(1, dmg // 2)
                                run["beast_protect_uids"].discard(target_uid)
                                ret_notes.append("*(Beast Guard — half dmg)*")
                                note_sfx = (" " + " ".join(ret_notes)).rstrip()
                            if target_uid in run.get("raging_uids", set()) and t_sc == "totem_warrior":
                                dmg = max(1, dmg // 2)
                                ret_notes.append("*(Bear — half dmg)*")
                                note_sfx = (" " + " ".join(ret_notes)).rstrip()
                            # Protection fighting style: other fighter with shield reduces dmg
                            prot_users = [pu for pu in active
                                          if pu != target_uid and pu in run.get("protection_uids", set())
                                          and run["player_hp"].get(pu, 0) > 0]
                            if prot_users:
                                prot_red = min(3, dmg)
                                dmg     -= prot_red
                                ret_notes.append(f"*(Protection −{prot_red})*")
                                note_sfx = (" " + " ".join(ret_notes)).rstrip()
                            ward = run.get("ward_hp", {}).get(target_uid, 0)
                            ward_abs = 0
                            if ward > 0:
                                ward_abs = min(ward, dmg)
                                dmg     -= ward_abs
                                run["ward_hp"][target_uid] = ward - ward_abs
                            run["player_hp"][target_uid] = max(0, run["player_hp"][target_uid] - dmg)
                            dodge_txt = " *(half dmg — dodged)*" if in_dodge else ""
                            ward_txt  = f" *(Ward absorbed {ward_abs})*" if ward_abs else ""
                            if roll == 20:
                                round_lines.append(
                                    f"💥 **{_ret_eobj['name']}** ✨ **CRIT!** on **{target_name}** — {dmg1} + {dmg2} = **{dmg} dmg**{dodge_txt}{ward_txt}{note_sfx}")
                            else:
                                round_lines.append(
                                    f"💥 **{_ret_eobj['name']}** hits **{target_name}** → {dmg} dmg{dodge_txt}{ward_txt}{note_sfx}")
                            run["log"].append({
                                "type": "enemy_hit", "enemy": _ret_eobj["name"],
                                "target": target_uid, "target_name": target_name,
                                "dmg": dmg, "round": rnd,
                            })
                            if run["player_hp"][target_uid] <= 0:
                                # Indomitable: Fighter saves vs death
                                indom_left = run.get("indomitable_uses", {}).get(target_uid, 0)
                                if stats and stats["char_class"] == "fighter" and indom_left > 0:
                                    con_mod = stats["mods"]["constitution"]
                                    isave   = random.randint(1, 20) + con_mod
                                    run["indomitable_uses"][target_uid] -= 1
                                    if isave >= 15:
                                        run["player_hp"][target_uid] = 1
                                        round_lines.append(
                                            f"💪 **{target_name}** Indomitable! CON save {isave} ≥ 15 — survives at 1 HP!")
                                    else:
                                        run.setdefault("downed", {})[target_uid] = {"successes": 0, "failures": 0}
                                        round_lines.append(
                                            f"💪 **{target_name}** Indomitable failed (save {isave}) — goes down!")
                                else:
                                    run.setdefault("downed", {})[target_uid] = {"successes": 0, "failures": 0}
                                    round_lines.append(
                                        f"💀 **{target_name}** goes down! *(death saves begin next round)*")
                                # Refresh non_fled so a dead player isn't retargeted
                                non_fled = [u for u in non_fled
                                            if run["player_hp"].get(u, 0) > 0]
                        else:
                            round_lines.append(f"💨 **{_ret_eobj['name']}** attacks **{target_name}** — MISS!{note_sfx}")
                            # BM Riposte: counter-attack on miss (targets the riposting enemy)
                            if target_uid in run.get("bm_riposte_set", set()):
                                rip_pend = run.get("bm_pending", {}).get(target_uid, {})
                                rip_die  = rip_pend.get("die", 0) if rip_pend.get("type") == "riposte" else 0
                                rip_r    = random.randint(1, 20)
                                t_stat_r = stats
                                rip_t    = rip_r + (t_stat_r["atk_bonus"] if t_stat_r else 0)
                                if rip_r == 20 or rip_t >= enemy["ac"]:
                                    rd1  = _roll(t_stat_r["dmg_expr"] if t_stat_r else "1d6")
                                    if rip_r == 20:
                                        rd2  = _roll(t_stat_r["dmg_expr"] if t_stat_r else "1d6")
                                        rdmg = rd1 + rd2 + rip_die
                                        round_lines.append(
                                            f"🔄 **{target_name}** Riposte ✨CRIT! → **{rdmg} dmg** (+{rip_die} die)")
                                    else:
                                        rdmg = rd1 + rip_die
                                        round_lines.append(
                                            f"🔄 **{target_name}** Riposte → **{rdmg} dmg** (+{rip_die} die)")
                                    _ret_eobj["hp"] = max(0, _ret_eobj["hp"] - rdmg)
                                    last_hitter = (target_uid, target_name)
                                else:
                                    round_lines.append(f"🔄 **{target_name}** Riposte missed! (rolled {rip_r})")
                                run["bm_riposte_set"].discard(target_uid)
                                run.get("bm_pending", {}).pop(target_uid, None)

            # ── Round result ───────────────────────────────────────────────
            still_active = [uid for uid, _ in run["participants"]
                            if uid not in run["fled"]
                            and uid not in run.get("dead", set())
                            and run["player_hp"].get(uid, 0) > 0]
            all_enemies_dead = all(e["hp"] <= 0 for e in enemies)
            color = var.COLOR_WIN if all_enemies_dead else var.COLOR_COMBAT

            result_embed = discord.Embed(
                title=f"Round {rnd} — Results",
                description="\n".join(round_lines) or "*(nothing happened)*",
                color=color,
            )
            await channel.send(embed=result_embed)

            if all_enemies_dead:
                # Kill blow messages for each enemy that died this round
                for _ke_idx, _ke in enumerate(enemies):
                    if _ke_idx in already_killed:
                        continue
                    if _ke["hp"] <= 0:
                        already_killed.add(_ke_idx)
                if last_hitter:
                    kill_entry = {
                        "type": "kill", "uid": last_hitter[0], "name": last_hitter[1],
                        "enemy": enemy["name"], "kill_flavor": None,
                    }
                    run["log"].append(kill_entry)
                    kill_entries_log.append(kill_entry)
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
                if all(uid in run["fled"]
                       for uid, _ in run["participants"]
                       if uid not in run.get("dead", set())):
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
        if encounter.get("image"):
            embed.set_image(url=encounter["image"])
        embed.set_footer(text=f"⏱️ {var.INTERACTION_TIMEOUT}s to decide")

        view = InteractionView(active, encounter, self)
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
        # Apply Help bonus: +4 from a party member who clicked Help (must be a different player)
        helper_uid  = view.helper_uid
        help_bonus  = 4 if (helper_uid and helper_uid != roller_uid) else 0
        # Ranger Natural Explorer (Lv 1+): +1 to all skill checks
        explore_bonus = 1 if (stats and stats["char_class"] == "ranger") else 0
        total       = roll + mod + help_bonus + explore_bonus
        dc          = encounter["dc"]
        success     = total >= dc

        help_line    = (f"\n🤝 **{view.helper_name}** helped — +{help_bonus} bonus!\n"
                        if help_bonus else "")
        explore_line = "\n🌿 *Natural Explorer — +1 to skill check*\n" if explore_bonus else ""
        flavor_line  = f'\n*"{flavor}"*\n' if flavor else ""
        roll_detail  = (f"🎲 Rolled **{roll}** {mod:+d}"
                        + (f" +{help_bonus} (help)" if help_bonus else "")
                        + (f" +{explore_bonus} (explorer)" if explore_bonus else "")
                        + f" = **{total}** vs DC **{dc}**")
        desc_lines  = [
            f"**{roller_name}** attempts a **{skill.title()}** check!",
            help_line,
            explore_line,
            flavor_line,
            roll_detail,
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
                # Enemy gets a free surprise hit — they capitalised on the failed check
                fight_enc = {
                    "type":           "combat",
                    "name":           encounter["name"],
                    "intro":          "The situation erupts into violence!",
                    "enemy":          fallback,
                    "enemy_surprise": True,
                }
                return await self._run_combat(channel, fight_enc, run_id)

            # No combat fallback — punish with HP damage scaled to DC
            n_dice    = max(1, dc // 5)
            dmg_lines = []
            for _uid in active:
                _dmg  = sum(random.randint(1, 4) for _ in range(n_dice))
                _prev = run["player_hp"].get(_uid, 0)
                run["player_hp"][_uid] = max(0, _prev - _dmg)
                _pname = next((n for u, n in run["participants"] if u == _uid), _uid)
                if run["player_hp"][_uid] <= 0 and _uid not in run.get("dead", set()):
                    run.setdefault("downed", {})[_uid] = {"successes": 0, "failures": 0}
                    dmg_lines.append(f"💀 **{_pname}** — **{_dmg}** dmg — goes down!")
                else:
                    dmg_lines.append(
                        f"❤️ **{_pname}** — **{_dmg}** dmg → {run['player_hp'][_uid]} HP")
            await channel.send(embed=discord.Embed(
                title="💢 The Setback",
                description=(
                    f"The failed check takes its toll — everyone suffers **{n_dice}d4** damage:\n\n"
                    + "\n".join(dmg_lines)
                ),
                color=var.COLOR_ERROR))
            await asyncio.sleep(2)
            return "victory"

    # ── Choice / branching node ───────────────────────────────────────────────

    async def _run_choice(self, channel: discord.TextChannel,
                          encounter: dict, run_id: str) -> tuple[str, list]:
        run    = self._runs[run_id]
        active = [uid for uid, _ in run["participants"]
                  if uid not in run["fled"] and run["player_hp"].get(uid, 0) > 0]
        if not active:
            return "defeat", []

        embed = discord.Embed(
            title=f"🗺️ {encounter['name']}",
            description=f"*{encounter['intro']}*",
            color=var.COLOR_INTERACTION,
        )
        if encounter.get("image"):
            embed.set_image(url=encounter["image"])
        embed.set_footer(text=f"⏱️ {var.INTERACTION_TIMEOUT}s — first to choose decides for the party")

        view = ChoiceView(active, encounter)
        msg  = await channel.send(embed=embed, view=view)
        try:
            await asyncio.wait_for(view._done.wait(), timeout=var.INTERACTION_TIMEOUT)
        except asyncio.TimeoutError:
            view.chosen = encounter["options"][0]

        for item in view.children:
            item.disabled = True
        try:
            await msg.edit(view=view)
        except Exception:
            pass

        chosen = view.chosen or encounter["options"][0]
        result_text = chosen.get("result_text", "The party presses on.")
        await channel.send(embed=discord.Embed(
            description=f"**{chosen['label']}** — *{result_text}*",
            color=var.COLOR_WIN,
        ))
        await asyncio.sleep(1)
        return "victory", chosen.get("encounters", [])


async def setup(bot: commands.Bot):
    await bot.add_cog(DungeonMasterCog(bot))
    log.info("✅ DND/DungeonMaster cog loaded")
