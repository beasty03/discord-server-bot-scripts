import discord
from discord.ext import commands
from discord import app_commands
import logging
import random
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('dnd_character_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

from forge_db import ForgeDB

log = logging.getLogger("launcher")

def _roll(expr: str) -> int:
    expr = expr.strip().lower()
    if expr.startswith("d"):
        expr = "1" + expr
    m = re.match(r'^(\d+)d(\d+)([+-]\d+)?$', expr)
    if not m:
        return 0
    rolls = [random.randint(1, int(m.group(2))) for _ in range(max(1, int(m.group(1))))]
    return max(1, sum(rolls) + (int(m.group(3)) if m.group(3) else 0))

# ============================================================================
# REGISTRY LOOKUPS
# ============================================================================

def _get_race(rid, extra=None):
    return next((r for r in var.RACES + (extra or []) if r["id"] == rid), None)

def _get_class(cid, extra=None):
    return next((c for c in var.CLASSES + (extra or []) if c["id"] == cid), None)

def _race_traits(rid, extra_races=None):
    base = var.RACE_TRAITS.get(rid)
    if base is not None:
        return base
    race = _get_race(rid, extra_races)
    return race.get("traits", []) if race else []

def _class_features(cid, extra_classes=None):
    base = var.CLASS_FEATURES.get(cid)
    if base is not None:
        return base
    klass = _get_class(cid, extra_classes)
    return klass.get("features", []) if klass else []

def _get_item(iid):
    return next((i for i in var.ITEMS if i["id"] == iid), None)

def _is_weapon_prof(klass: dict | None, item: dict) -> bool:
    """True if klass is proficient with item.
    weapon_profs entries can be weapon types ("simple", "martial") or specific item IDs."""
    if not klass or not item.get("weapon_type"):
        return False
    profs = klass.get("weapon_profs", [])
    return item["weapon_type"] in profs or item["id"] in profs

# ============================================================================
# DICE / DERIVATION
# ============================================================================

def _roll_4d6_drop_lowest() -> int:
    rolls = sorted(random.randint(1, 6) for _ in range(4))
    return sum(rolls[1:])

def _roll_stats() -> dict:
    if var.ROLL_METHOD == "array":
        vals = list(var.STANDARD_ARRAY)
        random.shuffle(vals)
        return dict(zip(var.ABILITIES, vals))
    return {ab: _roll_4d6_drop_lowest() for ab in var.ABILITIES}

def _ability_mod(score: int) -> int:
    return (score - 10) // 2

def _prof_bonus(level: int) -> int:
    return 2 + (level - 1) // 4

def _derive(char: dict, extra_races=None, extra_classes=None) -> dict:
    """Compute final scores, modifiers, AC, max HP, etc. from stored base data."""
    race  = _get_race(char["race"], extra_races) if char["race"] else None
    klass = _get_class(char["char_class"], extra_classes) if char["char_class"] else None

    finals = {}
    for ab in var.ABILITIES:
        base = char[ab] or 10
        bonus = race["mods"].get(ab, 0) if race else 0
        finals[ab] = base + bonus
    mods = {ab: _ability_mod(finals[ab]) for ab in var.ABILITIES}

    level = char["level"] or 1
    if klass:
        hit_die = klass["hit_die"]
        avg_gain = hit_die // 2 + 1
        max_hp = (hit_die + mods["constitution"]) + (level - 1) * (avg_gain + mods["constitution"])
        max_hp = max(1, max_hp)
        ac = 10 + mods["dexterity"] + klass.get("armor", 0)
    else:
        hit_die = None
        max_hp = 0
        ac = 10 + mods["dexterity"]

    return {
        "finals":  finals,
        "mods":    mods,
        "prof":    _prof_bonus(level),
        "hit_die": hit_die,
        "max_hp":  max_hp,
        "ac":      ac,
        "level":   level,
    }

# ============================================================================
# APP-COMMAND CHOICES (built from the registry)
# ============================================================================

# ============================================================================
# CREATION VIEWS
# ============================================================================

class StatMethodView(discord.ui.View):
    """Let the player choose how to assign ability scores at character creation."""

    def __init__(self, cog: "CharacterCog", uid: str, gid: str,
                 char_name: str, display_name: str):
        super().__init__(timeout=60)
        self._cog          = cog
        self._uid          = uid
        self._gid          = gid
        self._char_name    = char_name
        self._display_name = display_name

    async def _create(self, interaction: discord.Interaction, method: str):
        if method == "roll":
            stats = {ab: _roll_4d6_drop_lowest() for ab in var.ABILITIES}
            method_label = "Rolled (4d6 drop lowest)"
        else:
            vals  = list(var.STANDARD_ARRAY)
            random.shuffle(vals)
            stats = dict(zip(var.ABILITIES, vals))
            method_label = "Standard array [15,14,13,12,10,8]"

        self._cog.db.execute(
            """INSERT INTO dnd_characters
                   (user_id, guild_id, name, race, char_class, level, xp,
                    strength, dexterity, constitution, intelligence, wisdom, charisma,
                    hp, created_at)
               VALUES (?, ?, ?, NULL, NULL, 1, 0, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (self._uid, self._gid, self._char_name,
             stats["strength"], stats["dexterity"], stats["constitution"],
             stats["intelligence"], stats["wisdom"], stats["charisma"],
             datetime.utcnow().isoformat()),
        )
        # Starting health potion for everyone
        self._cog.db.execute(
            """INSERT INTO dnd_inventory (user_id, guild_id, item_id, qty, equipped)
               VALUES (?, ?, 'health_potion', 1, 0)
               ON CONFLICT(user_id, guild_id, item_id) DO UPDATE SET qty = qty + 1""",
            (self._uid, self._gid),
        )

        rolled = " · ".join(f"{var.ABILITY_ABBR[ab]} {stats[ab]}" for ab in var.ABILITIES)
        embed  = discord.Embed(
            title=f"🎲 {self._char_name} enters the world!",
            description=(
                f"*{method_label}*\n`{rolled}`\n\n"
                "Now pick your `/race` and `/class` to finish your character.\n"
                "You start with **1 Health Potion** in your backpack."
            ),
            color=var.COLOR_DND,
        )
        embed.set_footer(text=var.SERVER_NAME)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    @discord.ui.button(label="🎲 Roll Stats", style=discord.ButtonStyle.primary)
    async def roll_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self._create(interaction, "roll")

    @discord.ui.button(label="📋 Standard Array", style=discord.ButtonStyle.secondary)
    async def array_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self._create(interaction, "array")

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class RerollTokenView(discord.ui.View):
    """Shown when a player is on cooldown but owns a Reroll Token."""

    def __init__(self, cog: "CharacterCog", uid: str, gid: str,
                 char_name: str, display_name: str):
        super().__init__(timeout=30)
        self._cog          = cog
        self._uid          = uid
        self._gid          = gid
        self._char_name    = char_name
        self._display_name = display_name

    @discord.ui.button(label="🔄 Use Reroll Token", style=discord.ButtonStyle.primary)
    async def use_token(self, interaction: discord.Interaction, _: discord.ui.Button):
        uid, gid = self._uid, self._gid
        rows = self._cog.db.execute(
            "SELECT qty FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id='reroll_token'",
            (uid, gid))
        if not rows or rows[0][0] <= 0:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description="You no longer have a Reroll Token.", color=var.COLOR_ERROR),
                view=None)
            return
        self._cog.db.execute(
            "UPDATE dnd_inventory SET qty=qty-1 WHERE user_id=? AND guild_id=? AND item_id='reroll_token'",
            (uid, gid))
        self._cog.db.execute(
            "DELETE FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id='reroll_token' AND qty<=0",
            (uid, gid))
        self._cog.db.execute(
            "DELETE FROM dnd_character_cooldowns WHERE user_id=? AND guild_id=?",
            (uid, gid))
        choose_embed = discord.Embed(
            title=f"✨ Creating **{self._char_name}**",
            description=(
                "🔄 Reroll Token used — cooldown cleared!\n\n"
                "**🎲 Roll Stats** — 4d6 drop lowest for each ability.\n\n"
                "**📋 Standard Array** — [15, 14, 13, 12, 10, 8] randomly distributed."
            ),
            color=var.COLOR_DND,
        )
        await interaction.response.edit_message(
            embed=choose_embed,
            view=StatMethodView(self._cog, uid, gid, self._char_name, self._display_name),
        )
        self.stop()

    @discord.ui.button(label="Wait it out", style=discord.ButtonStyle.secondary)
    async def wait_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.edit_message(
            embed=discord.Embed(
                description="No worries — your token is safe. Come back when the cooldown expires!",
                color=var.COLOR_INFO),
            view=None)
        self.stop()


class DeleteConfirmView(discord.ui.View):
    """Confirmation gate for /sheet_delete."""

    def __init__(self, cog: "CharacterCog", uid: str, gid: str, char_name: str):
        super().__init__(timeout=30)
        self._cog       = cog
        self._uid       = uid
        self._gid       = gid
        self._char_name = char_name

    @discord.ui.button(label="Yes, delete", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, _: discord.ui.Button):
        self._cog.db.execute(
            "DELETE FROM dnd_characters WHERE user_id=? AND guild_id=?", (self._uid, self._gid))
        self._cog.db.execute(
            "DELETE FROM dnd_inventory WHERE user_id=? AND guild_id=?", (self._uid, self._gid))
        self._cog.db.execute(
            """INSERT INTO dnd_character_cooldowns (user_id, guild_id, deleted_at)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id, guild_id) DO UPDATE SET deleted_at=excluded.deleted_at""",
            (self._uid, self._gid, datetime.utcnow().isoformat()))
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=(
                    f"🗑️ **{self._char_name}** has been deleted.\n"
                    f"You can create a new character in **7 days**."
                ),
                color=var.COLOR_ERROR),
            view=None)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.edit_message(
            embed=discord.Embed(description="Deletion cancelled.", color=var.COLOR_INFO),
            view=None)
        self.stop()

class EquipView(discord.ui.View):
    """Equip or unequip a weapon, armor, shield, or accessory."""
    _SLOT_EMOJI = {"weapon": "⚔️", "offhand": "🛡️", "armor": "🪖", "accessory": "💍"}

    def __init__(self, cog: "CharacterCog", uid: str, gid: str,
                 items: list[tuple]):
        super().__init__(timeout=30)
        self._cog   = cog
        self._uid   = uid
        self._gid   = gid
        self._items = items
        options = [
            discord.SelectOption(
                label=f"{'✅ ' if eq else ''}{item['name']}",
                value=iid,
                description=(
                    f"{self._SLOT_EMOJI.get(item['slot'], '📦')} "
                    f"{item['slot'].capitalize()}"
                    + (" — equipped" if eq else "")
                ),
            )
            for iid, eq, item in items
        ]
        sel = discord.ui.Select(placeholder="Choose an item to equip/unequip…", options=options)
        sel.callback = self._on_pick
        self.add_item(sel)

    async def _on_pick(self, interaction: discord.Interaction):
        chosen_id  = interaction.data["values"][0]
        chosen_row = next(((iid, eq, it) for iid, eq, it in self._items if iid == chosen_id), None)
        if not chosen_row:
            await interaction.response.edit_message(
                embed=discord.Embed(description="Item not found.", color=var.COLOR_ERROR), view=None)
            self.stop()
            return
        _, currently_eq, chosen_item = chosen_row
        slot = chosen_item.get("slot")

        if currently_eq:
            self._cog.db.execute(
                "UPDATE dnd_inventory SET equipped=0 "
                "WHERE user_id=? AND guild_id=? AND item_id=?",
                (self._uid, self._gid, chosen_id))
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description=f"🗃️ **{chosen_item['name']}** unequipped.",
                    color=var.COLOR_INFO), view=None)
        else:
            for iid, eq, it in self._items:
                if eq and it.get("slot") == slot and iid != chosen_id:
                    self._cog.db.execute(
                        "UPDATE dnd_inventory SET equipped=0 "
                        "WHERE user_id=? AND guild_id=? AND item_id=?",
                        (self._uid, self._gid, iid))
            self._cog.db.execute(
                "UPDATE dnd_inventory SET equipped=1 "
                "WHERE user_id=? AND guild_id=? AND item_id=?",
                (self._uid, self._gid, chosen_id))
            emoji = self._SLOT_EMOJI.get(slot, "📦")
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description=f"{emoji} **{chosen_item['name']}** equipped!",
                    color=var.COLOR_WIN), view=None)
        self.stop()


_CHAR_COLS = [
    "user_id", "guild_id", "name", "race", "char_class", "level", "xp",
    "strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma",
    "hp", "created_at",
]

# ============================================================================
# COG
# ============================================================================

class CharacterCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot               = bot
        self.db                = ForgeDB.get()
        self._extra_items:     list[dict] = []
        self._extra_shop_items: list[dict] = []  # proxy for DLC shop items (avoids ShopCog load-order issue)

    def register_item(self, data: dict):
        if not any(i["id"] == data["id"] for i in self._extra_items):
            self._extra_items.append(data)
            log.info("Character: registered DLC item '%s'", data["id"])

    def register_shop_item(self, data: dict):
        """Register a shop listing via CharacterCog so ShopCog can discover it at query time."""
        if not any(i["id"] == data["id"] for i in self._extra_shop_items):
            self._extra_shop_items.append(data)
            log.info("Character: proxied DLC shop item '%s'", data["id"])

    def _scan_dlc_items(self):
        """Scan DND_DLC for WEAPONS/CHAR_ITEMS/SHOP_ITEMS (old-style) and register them."""
        dlc_dir = Path(__file__).parent.parent.parent / "DND_DLC"
        if not dlc_dir.is_dir():
            return
        for var_file in sorted(dlc_dir.glob("*/variables.py")):
            folder = var_file.parent.name
            try:
                spec = _ilu.spec_from_file_location(f"dlc_{folder}_vars", var_file)
                mod = _ilu.module_from_spec(spec)
                spec.loader.exec_module(mod)
                for item in getattr(mod, "WEAPONS", []) + getattr(mod, "CHAR_ITEMS", []):
                    self.register_item(item)
                for item in getattr(mod, "SHOP_ITEMS", []):
                    self.register_shop_item(item)
            except Exception as exc:
                log.warning("Character: DLC scan failed for '%s': %s", folder, exc)

    def _item(self, iid: str) -> dict | None:
        found = next((i for i in var.ITEMS + self._extra_items if i["id"] == iid), None)
        if found:
            return found
        core = self._engine_core()
        return core.registry.items.get(iid) if core else None

    async def cog_load(self):
        # Ensure EngineCore is loaded so race/class DLC is available for autocomplete.
        if not self.bot.cogs.get("EngineCore"):
            try:
                import importlib as _il
                _EC = None
                # Strategy 1: derive engine path from DungeonMasterCog's module.
                # This works regardless of whether the code is deployed as cogs.DND.*
                # or DND.DungeonMaster.* — no hardcoded package prefix needed.
                _dm = self.bot.cogs.get("DungeonMasterCog")
                if _dm:
                    _dm_pkg = ".".join(type(_dm).__module__.split(".")[:-1])
                    for _tail in ("engine", "DungeonMaster.engine"):
                        try:
                            _mod = _il.import_module(f"{_dm_pkg}.{_tail}")
                            _EC = getattr(_mod, "EngineCore", None)
                            if _EC:
                                break
                        except ImportError:
                            continue
                # Strategy 2: try well-known absolute paths
                if _EC is None:
                    for _path in ("DND.DungeonMaster.engine", "DND.engine"):
                        try:
                            _mod = _il.import_module(_path)
                            _EC = getattr(_mod, "EngineCore", None)
                            if _EC:
                                break
                        except ImportError:
                            continue
                if _EC is not None:
                    await self.bot.add_cog(_EC(self.bot))
                    log.info("Character: auto-booted EngineCore")
                else:
                    log.warning("Character: EngineCore not found — /race and /class will have no options")
            except Exception as _e:
                log.warning("Character: could not auto-boot EngineCore: %s", _e)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS dnd_characters (
                user_id      TEXT    NOT NULL,
                guild_id     TEXT    NOT NULL,
                name         TEXT,
                race         TEXT,
                char_class   TEXT,
                level        INTEGER DEFAULT 1,
                xp           INTEGER DEFAULT 0,
                strength     INTEGER,
                dexterity    INTEGER,
                constitution INTEGER,
                intelligence INTEGER,
                wisdom       INTEGER,
                charisma     INTEGER,
                hp           INTEGER DEFAULT 0,
                created_at   TEXT,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS dnd_inventory (
                user_id   TEXT    NOT NULL,
                guild_id  TEXT    NOT NULL,
                item_id   TEXT    NOT NULL,
                qty       INTEGER DEFAULT 1,
                equipped  INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id, item_id)
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS dnd_character_cooldowns (
                user_id    TEXT NOT NULL,
                guild_id   TEXT NOT NULL,
                deleted_at TEXT NOT NULL,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        self._scan_dlc_items()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _engine_cog(self):
        return self.bot.cogs.get("DungeonMasterCog")

    def _engine_core(self):
        return self.bot.cogs.get("EngineCore")

    def _extra_races(self) -> list:
        seen: set[str] = set()
        out: list[dict] = []
        dm = self._engine_cog()
        for r in (dm._extra_races if dm else []):
            if r["id"] not in seen:
                seen.add(r["id"])
                out.append(r)
        core = self._engine_core()
        if core:
            for r in core.registry.races.values():
                if r["id"] not in seen:
                    seen.add(r["id"])
                    # DLC races use stat_bonuses; _derive() expects mods
                    if "mods" not in r:
                        r = {**r, "mods": r.get("stat_bonuses", {})}
                    out.append(r)
        return out

    def _extra_classes(self) -> list:
        seen: set[str] = set()
        out: list[dict] = []
        dm = self._engine_cog()
        for c in (dm._extra_classes if dm else []):
            if c["id"] not in seen:
                seen.add(c["id"])
                out.append(c)
        core = self._engine_core()
        if core:
            for c in core.registry.classes.values():
                if c["id"] not in seen:
                    seen.add(c["id"])
                    out.append(c)
        return out

    def _class_features(self, class_id: str) -> list:
        dm = self._engine_cog()
        if dm:
            return dm._get_class_features(class_id)
        return var.CLASS_FEATURES.get(class_id, [])

    def _race_traits(self, race_id: str) -> list:
        dm = self._engine_cog()
        if dm:
            return dm._get_race_traits(race_id)
        return var.RACE_TRAITS.get(race_id, [])

    def _combat_features(self, class_id: str) -> list:
        dm = self._engine_cog()
        if dm:
            return dm._get_combat_features(class_id)
        return var.COMBAT_FEATURES.get(class_id, [])

    def _subclass_combat_features(self, subclass_id: str) -> list:
        dm = self._engine_cog()
        if dm:
            return dm._get_subclass_combat_features(subclass_id)
        return var.SUBCLASS_COMBAT_FEATURES.get(subclass_id, [])

    def _level_up_choice(self, key: tuple) -> "dict | None":
        dm = self._engine_cog()
        if dm:
            return dm._get_level_up_choice(key)
        return var.LEVEL_UP_CHOICES.get(key)

    def _derive_char(self, char: dict) -> dict:
        return _derive(char, self._extra_races(), self._extra_classes())

    def _fetch_char(self, uid: str, gid: str) -> dict | None:
        rows = self.db.execute(
            f"SELECT {', '.join(_CHAR_COLS)} FROM dnd_characters WHERE user_id = ? AND guild_id = ?",
            (uid, gid),
        )
        return dict(zip(_CHAR_COLS, rows[0])) if rows else None

    def _recompute_hp(self, uid: str, gid: str):
        """Set current HP to the freshly-derived max — used after race/class changes."""
        char = self._fetch_char(uid, gid)
        if not char:
            return
        max_hp = self._derive_char(char)["max_hp"]
        self.db.execute(
            "UPDATE dnd_characters SET hp = ? WHERE user_id = ? AND guild_id = ?",
            (max_hp, uid, gid),
        )

    @staticmethod
    def _err(msg: str) -> discord.Embed:
        return discord.Embed(description=msg, color=var.COLOR_ERROR)

    @staticmethod
    def _no_char_embed() -> discord.Embed:
        return discord.Embed(
            description="You don't have a character yet. Start with `/name`, then set your `/race` and `/class`.",
            color=var.COLOR_ERROR,
        )

    # ── /name ───────────────────────────────────────────────────────────────────

    @app_commands.command(name="name", description="Name your character (creates one if you don't have one yet).")
    @app_commands.describe(name="Your character's name (1–32 characters)")
    async def set_name(self, interaction: discord.Interaction, name: str):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)
        name = name.strip()

        if not (1 <= len(name) <= 32):
            await interaction.response.send_message(
                embed=self._err("Name must be between 1 and 32 characters."), ephemeral=True)
            return

        self.db.ensure_user(uid, gid, interaction.user.display_name)
        char = self._fetch_char(uid, gid)

        if char:
            self.db.execute(
                "UPDATE dnd_characters SET name = ? WHERE user_id = ? AND guild_id = ?",
                (name, uid, gid),
            )
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"✏️ Your character is now named **{name}**.",
                    color=var.COLOR_WIN,
                ),
                ephemeral=True,
            )
            return

        # Weekly cooldown — bypassed by spending a Reroll Token from the shop
        cd_rows = self.db.execute(
            "SELECT deleted_at FROM dnd_character_cooldowns WHERE user_id=? AND guild_id=?",
            (uid, gid))
        if cd_rows:
            deleted_at   = datetime.fromisoformat(cd_rows[0][0])
            cooldown_end = deleted_at + timedelta(days=var.DELETION_COOLDOWN_DAYS)
            remaining    = cooldown_end - datetime.utcnow()
            if remaining.total_seconds() > 0:
                days     = remaining.days
                hours    = remaining.seconds // 3600
                time_txt = f"{days}d {hours}h" if days > 0 else f"{hours}h"

                token_rows = self.db.execute(
                    "SELECT qty FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id='reroll_token'",
                    (uid, gid))
                has_token = bool(token_rows and token_rows[0][0] > 0)

                cd_embed = self._err(
                    f"You can only create a new character once per week.\n"
                    f"Try again in **{time_txt}**."
                    + ("\n\nYou have a **🔄 Character Reroll Token** — use it to skip the wait!"
                       if has_token else
                       "\n\n*Buy a **Character Reroll Token** from `/shop` to skip the wait.*")
                )
                view = (RerollTokenView(self, uid, gid, name, interaction.user.display_name)
                        if has_token else None)
                await interaction.response.send_message(embed=cd_embed, view=view, ephemeral=True)
                return

        choose_embed = discord.Embed(
            title=f"✨ Creating **{name}**",
            description=(
                "How do you want to assign your ability scores?\n\n"
                "**🎲 Roll Stats** — 4d6 drop lowest for each ability. "
                "Random: you might roll higher *or* lower than average.\n\n"
                "**📋 Standard Array** — [15, 14, 13, 12, 10, 8] randomly "
                "distributed across your six abilities. Predictable and balanced."
            ),
            color=var.COLOR_DND,
        )
        await interaction.response.send_message(
            embed=choose_embed,
            view=StatMethodView(self, uid, gid, name, interaction.user.display_name),
            ephemeral=True,
        )

    # ── /race ───────────────────────────────────────────────────────────────────

    @app_commands.command(name="race", description="Set your character's race.")
    @app_commands.describe(race="Which race to play")
    async def set_race(self, interaction: discord.Interaction, race: str):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if not self._fetch_char(uid, gid):
            await interaction.response.send_message(embed=self._no_char_embed(), ephemeral=True)
            return

        r = _get_race(race, self._extra_races())
        if not r:
            await interaction.response.send_message(
                embed=self._err("Unknown race. Use the autocomplete suggestions."), ephemeral=True)
            return
        self.db.execute(
            "UPDATE dnd_characters SET race = ? WHERE user_id = ? AND guild_id = ?",
            (race, uid, gid),
        )
        self._recompute_hp(uid, gid)

        bonus = " · ".join(f"+{v} {var.ABILITY_ABBR[k]}" for k, v in r["mods"].items())
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"{r['emoji']} You are now a **{r['name']}**.\nRacial bonuses: `{bonus}`",
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )

    @set_race.autocomplete("race")
    async def race_autocomplete(self, interaction: discord.Interaction, current: str):
        all_races = var.RACES + self._extra_races()
        return [
            app_commands.Choice(name=f"{r['emoji']} {r['name']}", value=r["id"])
            for r in all_races
            if current.lower() in r["name"].lower()
        ][:25]

    # ── /class ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="class", description="Set your character's class.")
    @app_commands.describe(char_class="Which class to play")
    async def set_class(self, interaction: discord.Interaction, char_class: str):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if not self._fetch_char(uid, gid):
            await interaction.response.send_message(embed=self._no_char_embed(), ephemeral=True)
            return

        c = _get_class(char_class, self._extra_classes())
        if not c:
            await interaction.response.send_message(
                embed=self._err("Unknown class. Use the autocomplete suggestions."), ephemeral=True)
            return
        self.db.execute(
            "UPDATE dnd_characters SET char_class = ? WHERE user_id = ? AND guild_id = ?",
            (char_class, uid, gid),
        )

        # Grant starting equipment — weapons auto-equipped, everything else unequipped.
        for item_id in c.get("start_items", []):
            item_def   = self._item(item_id)
            auto_equip = 1 if (item_def and item_def.get("slot") == "weapon") else 0
            self.db.execute(
                """INSERT INTO dnd_inventory (user_id, guild_id, item_id, qty, equipped)
                   VALUES (?, ?, ?, 1, ?)
                   ON CONFLICT(user_id, guild_id, item_id) DO NOTHING""",
                (uid, gid, item_id, auto_equip),
            )

        self._recompute_hp(uid, gid)

        gear = ", ".join(self._item(i)["name"] for i in c.get("start_items", []) if self._item(i)) or "none"
        await interaction.response.send_message(
            embed=discord.Embed(
                description=(
                    f"{c['emoji']} You are now a **{c['name']}** "
                    f"(d{c['hit_die']} hit die).\nStarting gear: {gear}."
                ),
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )

    @set_class.autocomplete("char_class")
    async def class_autocomplete(self, interaction: discord.Interaction, current: str):
        all_classes = var.CLASSES + self._extra_classes()
        return [
            app_commands.Choice(name=f"{c['emoji']} {c['name']}", value=c["id"])
            for c in all_classes
            if current.lower() in c["name"].lower()
        ][:25]

    # ── /sheet ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="sheet", description="Show your full character sheet.")
    @app_commands.describe(member="Another player's sheet (leave empty for yourself)")
    async def sheet(self, interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        uid = str(target.id)
        gid = str(interaction.guild_id)

        char = self._fetch_char(uid, gid)
        if not char:
            who = "They don't" if member else "You don't"
            await interaction.response.send_message(
                embed=self._err(f"{who} have a character yet."), ephemeral=member is None)
            return

        d = self._derive_char(char)
        race  = _get_race(char["race"], self._extra_races())
        klass = _get_class(char["char_class"], self._extra_classes())

        self.db.ensure_user(uid, gid, target.display_name)
        coins = self.db.get_balance(uid, gid)

        title = char["name"] or target.display_name
        subtitle_bits = []
        if race:  subtitle_bits.append(f"{race['emoji']} {race['name']}")
        if klass: subtitle_bits.append(f"{klass['emoji']} {klass['name']}")
        subtitle = " · ".join(subtitle_bits) if subtitle_bits else "*setup incomplete — set /race and /class*"

        embed = discord.Embed(
            title=f"📜 {title}",
            description=f"Level {d['level']}  ·  {subtitle}",
            color=var.COLOR_DND,
        )

        abilities = "\n".join(
            f"`{var.ABILITY_ABBR[ab]}` {d['finals'][ab]:>2}  ({d['mods'][ab]:+d})"
            for ab in var.ABILITIES
        )
        embed.add_field(name="Abilities", value=abilities, inline=True)

        vitals = (
            f"❤️ HP **{char['hp']}/{d['max_hp']}**\n"
            f"🛡️ AC **{d['ac']}**\n"
            f"➕ Prof **+{d['prof']}**\n"
            + (f"🎲 Hit die **d{d['hit_die']}**\n" if d['hit_die'] else "")
            + f"{var.CURRENCY_SYMBOL} **{coins:,}** {var.CURRENCY_NAME}"
        )
        embed.add_field(name="Vitals", value=vitals, inline=True)

        next_label = (
            f"{var.XP_THRESHOLDS[d['level'] + 1]:,} for level {d['level'] + 1}"
            if d['level'] < var.MAX_LEVEL else "max level"
        )
        embed.add_field(name="XP", value=f"{char['xp']:,}  ·  next: {next_label}", inline=False)

        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=var.SERVER_NAME)
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    # ── /backpack ─────────────────────────────────────────────────────────────

    @app_commands.command(name="backpack", description="Show your inventory and equipped gear.")
    async def backpack(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        char = self._fetch_char(uid, gid)
        if not char:
            await interaction.response.send_message(embed=self._no_char_embed(), ephemeral=True)
            return

        d     = self._derive_char(char)
        klass = _get_class(char["char_class"], self._extra_classes()) if char["char_class"] else None

        rows = self.db.execute(
            "SELECT item_id, qty, equipped FROM dnd_inventory WHERE user_id = ? AND guild_id = ?",
            (uid, gid),
        )
        if not rows:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🎒 Backpack",
                    description="Empty. Set a `/class` for starting gear, or earn loot on a campaign.",
                    color=var.COLOR_INFO,
                ),
                ephemeral=True,
            )
            return

        lines = []
        for item_id, qty, equipped in rows:
            item    = self._item(item_id)
            label   = item["name"] if item else item_id
            qty_txt = f" ×{qty}" if qty and qty > 1 else ""
            eq_txt  = "  *(equipped)*" if equipped else ""

            atk_txt = ""
            if item and item.get("weapon_type") and item.get("ability"):
                ab_mod  = d["mods"][item["ability"]]
                is_prof = _is_weapon_prof(klass, item)
                atk     = ab_mod + (d["prof"] if is_prof else 0)
                ab_abbr = var.ABILITY_ABBR[item["ability"]]
                if is_prof:
                    atk_txt = f"  — ⚔️ {atk:+d} ({ab_abbr} {ab_mod:+d}, prof {d['prof']:+d})"
                else:
                    atk_txt = f"  — ⚔️ {atk:+d} ({ab_abbr} {ab_mod:+d}, *no prof*)"

            lines.append(f"• {label}{qty_txt}{eq_txt}{atk_txt}")

        embed = discord.Embed(
            title="🎒 Backpack",
            description="\n".join(lines),
            color=var.COLOR_INFO,
        )
        embed.set_footer(text=var.SERVER_NAME)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /equip ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="equip", description="Equip or unequip a weapon, armor, or shield.")
    async def equip(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if self.db.execute("SELECT 1 FROM dnd_active_runs WHERE user_id=? AND guild_id=?", (uid, gid)):
            await interaction.response.send_message(
                embed=discord.Embed(description="⚔️ You're on an active campaign — gear can't be swapped mid-adventure.", color=0xe74c3c),
                ephemeral=True)
            return

        char = self._fetch_char(uid, gid)
        if not char:
            await interaction.response.send_message(embed=self._no_char_embed(), ephemeral=True)
            return

        rows = self.db.execute(
            "SELECT item_id, equipped FROM dnd_inventory WHERE user_id=? AND guild_id=?",
            (uid, gid))

        EQUIPPABLE = {"weapon", "offhand", "armor", "accessory"}
        equippable = []
        for item_id, equipped in (rows or []):
            item = self._item(item_id)
            if item and item.get("slot") in EQUIPPABLE:
                equippable.append((item_id, bool(equipped), item))

        if not equippable:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="No equippable items in your backpack.",
                    color=var.COLOR_INFO),
                ephemeral=True)
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                description="🗡️ **Equip / unequip** — ✅ = currently equipped",
                color=var.COLOR_INFO),
            view=EquipView(self, uid, gid, equippable),
            ephemeral=True)

    # ── /level ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="level", description="Show your level and XP progress.")
    async def level(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        char = self._fetch_char(uid, gid)
        if not char:
            await interaction.response.send_message(embed=self._no_char_embed(), ephemeral=True)
            return

        d   = self._derive_char(char)
        lvl = d["level"]
        xp  = char["xp"] or 0

        if lvl < var.MAX_LEVEL:
            need  = var.XP_THRESHOLDS[lvl + 1]
            floor = var.XP_THRESHOLDS[lvl]
            span  = max(1, need - floor)
            done  = max(0, xp - floor)
            pct   = min(100, int(done / span * 100))
            filled = "█" * (pct // 10)
            empty  = "░" * (10 - pct // 10)
            progress = f"`{filled}{empty}` {pct}%\n**{xp:,}** / {need:,} xp (next level at {need:,})"
        else:
            progress = f"**{xp:,}** xp — maximum level reached."

        embed = discord.Embed(
            title=f"⭐ Level {lvl}",
            description=progress,
            color=var.COLOR_DND,
        )
        embed.add_field(name="Proficiency", value=f"+{d['prof']}", inline=True)
        if d["hit_die"]:
            embed.add_field(name="Hit die", value=f"d{d['hit_die']}", inline=True)
        embed.set_footer(text=f"{var.SERVER_NAME} · level-ups come from campaigns")
        await interaction.response.send_message(embed=embed, ephemeral=True)


    # ── /class_upgrade ────────────────────────────────────────────────────────────

    @app_commands.command(name="class_upgrade", description="Browse class features by level.")
    @app_commands.describe(char_class="Class to browse (defaults to your current class)")
    async def class_upgrade(self, interaction: discord.Interaction, char_class: str | None = None):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if char_class is not None:
            cid = char_class
        else:
            char = self._fetch_char(uid, gid)
            cid = char["char_class"] if char else None

        if not cid:
            await interaction.response.send_message(
                embed=self._err("Specify a class, or set yours with `/class` first."),
                ephemeral=True,
            )
            return

        c        = _get_class(cid, self._extra_classes())
        features = self._class_features(cid)

        by_level = defaultdict(list)
        for f in features:
            by_level[f["level"]].append(f["name"])

        lines = [
            f"`Lv {lvl:>2}` {', '.join(names)}"
            for lvl, names in sorted(by_level.items())
        ]

        embed = discord.Embed(
            title=f"{c['emoji']} {c['name']} — Class Features",
            description="\n".join(lines) or "*No features listed yet.*",
            color=var.COLOR_DND,
        )
        embed.set_footer(text=var.SERVER_NAME)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @class_upgrade.autocomplete("char_class")
    async def class_upgrade_autocomplete(self, interaction: discord.Interaction, current: str):
        all_classes = var.CLASSES + self._extra_classes()
        return [
            app_commands.Choice(name=f"{c['emoji']} {c['name']}", value=c["id"])
            for c in all_classes
            if current.lower() in c["name"].lower()
        ][:25]

    # ── /sheet_delete ─────────────────────────────────────────────────────────────

    @app_commands.command(name="sheet_delete", description="Permanently delete your character so you can start fresh.")
    async def sheet_delete(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        char = self._fetch_char(uid, gid)
        if not char:
            await interaction.response.send_message(embed=self._no_char_embed(), ephemeral=True)
            return

        name = char["name"] or interaction.user.display_name
        embed = discord.Embed(
            title="⚠️ Delete Character?",
            description=(
                f"This will permanently delete **{name}** and all their inventory.\n"
                "**This cannot be undone.**\n\nAre you sure?"
            ),
            color=var.COLOR_ERROR,
        )
        await interaction.response.send_message(
            embed=embed,
            view=DeleteConfirmView(self, uid, gid, name),
            ephemeral=True,
        )

    # ── /race_upgrade ─────────────────────────────────────────────────────────────

    @app_commands.command(name="race_upgrade", description="Browse racial traits.")
    @app_commands.describe(race="Race to browse (defaults to your current race)")
    async def race_upgrade(self, interaction: discord.Interaction, race: str | None = None):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if race is not None:
            rid = race
        else:
            char = self._fetch_char(uid, gid)
            rid = char["race"] if char else None

        if not rid:
            await interaction.response.send_message(
                embed=self._err("Specify a race, or set yours with `/race` first."),
                ephemeral=True,
            )
            return

        r      = _get_race(rid, self._extra_races())
        traits = self._race_traits(rid)
        bonus  = ", ".join(f"+{v} {var.ABILITY_ABBR[k]}" for k, v in r["mods"].items())

        lines = [f"**{t['name']}** — {t['desc']}" for t in traits]

        embed = discord.Embed(
            title=f"{r['emoji']} {r['name']} — Racial Traits",
            description="\n".join(lines) or "*No traits listed yet.*",
            color=var.COLOR_DND,
        )
        embed.add_field(name="Ability Bonuses", value=f"`{bonus}`", inline=False)
        embed.set_footer(text=var.SERVER_NAME)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @race_upgrade.autocomplete("race")
    async def race_upgrade_autocomplete(self, interaction: discord.Interaction, current: str):
        all_races = var.RACES + self._extra_races()
        return [
            app_commands.Choice(name=f"{r['emoji']} {r['name']}", value=r["id"])
            for r in all_races
            if current.lower() in r["name"].lower()
        ][:25]

    # ── /rest ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="rest", description=f"Fully restore your HP after a campaign. Costs coins.")
    async def rest(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if self.db.execute("SELECT 1 FROM dnd_active_runs WHERE user_id=? AND guild_id=?", (uid, gid)):
            await interaction.response.send_message(
                embed=discord.Embed(description="⚔️ You're on an active campaign — rest when the adventure is over.", color=0xe74c3c),
                ephemeral=True)
            return

        char = self._fetch_char(uid, gid)
        if not char:
            await interaction.response.send_message(embed=self._no_char_embed(), ephemeral=True)
            return

        max_hp = self._derive_char(char)["max_hp"]
        if char["hp"] >= max_hp:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"❤️ You're already at full HP ({max_hp}/{max_hp}).",
                    color=var.COLOR_INFO),
                ephemeral=True)
            return

        cost    = var.REST_COST
        balance = self.db.get_balance(uid, gid)
        if balance < cost:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        f"Not enough {var.CURRENCY_SYMBOL}! Resting costs **{cost:,}** "
                        f"but you only have **{balance:,}**."
                    ),
                    color=var.COLOR_ERROR),
                ephemeral=True)
            return

        healed = max_hp - char["hp"]
        self.db.execute(
            "UPDATE dnd_characters SET hp = ? WHERE user_id = ? AND guild_id = ?",
            (max_hp, uid, gid))
        self.db.execute(
            "DELETE FROM dnd_character_choices "
            "WHERE user_id=? AND guild_id=? AND choice_key=?",
            (uid, gid, "help_long_rest_used"))
        self.db.update_balance(uid, gid, -cost, "rest")
        new_bal = self.db.get_balance(uid, gid)

        await interaction.response.send_message(
            embed=discord.Embed(
                description=(
                    f"🛏️ You rest and recover fully.\n"
                    f"❤️ **+{healed} HP** → {max_hp}/{max_hp}\n"
                    f"Paid **{cost:,}** {var.CURRENCY_SYMBOL}  ·  Balance: **{new_bal:,}**"
                ),
                color=var.COLOR_WIN),
            ephemeral=True)

    # ── /backpack_use ─────────────────────────────────────────────────────────

    @app_commands.command(name="backpack_use", description="Use a consumable item from your backpack.")
    @app_commands.describe(item="Item to use", target="Who to use it on (default: yourself)")
    async def backpack_use(self, interaction: discord.Interaction,
                           item: str, target: discord.Member | None = None):
        uid  = str(interaction.user.id)
        gid  = str(interaction.guild_id)

        if self.db.execute("SELECT 1 FROM dnd_active_runs WHERE user_id=? AND guild_id=?", (uid, gid)):
            await interaction.response.send_message(
                embed=discord.Embed(description="⚔️ You're on an active campaign — use `/item` to consume items in combat.", color=0xe74c3c),
                ephemeral=True)
            return

        tgt  = target or interaction.user
        t_uid = str(tgt.id)

        rows = self.db.execute(
            "SELECT qty FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id=?",
            (uid, gid, item))
        if not rows or rows[0][0] < 1:
            await interaction.response.send_message(
                embed=self._err("You don't have that item."), ephemeral=True)
            return

        item_data = self._item(item)
        if not item_data or item_data.get("slot") != "consumable" or not item_data.get("heal_expr"):
            await interaction.response.send_message(
                embed=self._err("That item can't be used outside of combat."), ephemeral=True)
            return

        t_char = self._fetch_char(t_uid, gid)
        if not t_char:
            who = "That player doesn't" if tgt != interaction.user else "You don't"
            await interaction.response.send_message(
                embed=self._err(f"{who} have a character."), ephemeral=True)
            return

        max_hp = self._derive_char(t_char)["max_hp"]
        old_hp = t_char["hp"]
        heal   = _roll(item_data["heal_expr"])
        new_hp = min(max_hp, old_hp + heal)
        actual = new_hp - old_hp

        self.db.execute(
            "UPDATE dnd_inventory SET qty=qty-1 WHERE user_id=? AND guild_id=? AND item_id=?",
            (uid, gid, item))
        self.db.execute(
            "DELETE FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id=? AND qty<=0",
            (uid, gid, item))
        self.db.execute(
            "UPDATE dnd_characters SET hp=? WHERE user_id=? AND guild_id=?",
            (new_hp, t_uid, gid))

        emoji      = item_data.get("emoji", "🧪")
        target_txt = "yourself" if tgt == interaction.user else f"**{tgt.display_name}**"
        await interaction.response.send_message(
            embed=discord.Embed(
                description=(
                    f"{emoji} Used **{item_data['name']}** on {target_txt} → "
                    f"**+{actual} HP** ({new_hp}/{max_hp})"
                ),
                color=var.COLOR_WIN),
            ephemeral=True)

    @backpack_use.autocomplete("item")
    async def _backpack_use_ac(self, interaction: discord.Interaction, current: str):
        uid, gid = str(interaction.user.id), str(interaction.guild_id)
        rows = self.db.execute(
            "SELECT item_id, qty FROM dnd_inventory WHERE user_id=? AND guild_id=? AND qty>0",
            (uid, gid)) or []
        choices = []
        for iid, qty in rows:
            d = self._item(iid)
            if not d or d.get("slot") != "consumable":
                continue
            label = f"{d.get('emoji','')} {d['name']}{f' ×{qty}' if qty > 1 else ''}"
            if current.lower() in label.lower():
                choices.append(app_commands.Choice(name=label.strip(), value=iid))
        return choices[:25]

    # ── /backpack_give ────────────────────────────────────────────────────────

    @app_commands.command(name="backpack_give", description="Give an item from your backpack to another player.")
    @app_commands.describe(item="Item to give", qty="How many to give", target="Who to give it to")
    async def backpack_give(self, interaction: discord.Interaction,
                            item: str, target: discord.Member, qty: int = 1):
        uid  = str(interaction.user.id)
        gid  = str(interaction.guild_id)
        t_uid = str(target.id)

        if self.db.execute("SELECT 1 FROM dnd_active_runs WHERE user_id=? AND guild_id=?", (uid, gid)):
            await interaction.response.send_message(
                embed=discord.Embed(description="⚔️ You're on an active campaign — items can't be traded mid-adventure.", color=0xe74c3c),
                ephemeral=True)
            return

        if target == interaction.user:
            await interaction.response.send_message(
                embed=self._err("You can't give items to yourself."), ephemeral=True)
            return
        if qty < 1:
            await interaction.response.send_message(
                embed=self._err("Quantity must be at least 1."), ephemeral=True)
            return

        rows    = self.db.execute(
            "SELECT qty FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id=?",
            (uid, gid, item))
        current = rows[0][0] if rows else 0
        if current < qty:
            have = f"You only have {current}." if current else "You don't have that item."
            await interaction.response.send_message(embed=self._err(have), ephemeral=True)
            return

        item_data = self._item(item)
        label     = item_data["name"] if item_data else item

        self.db.execute(
            "UPDATE dnd_inventory SET qty=qty-? WHERE user_id=? AND guild_id=? AND item_id=?",
            (qty, uid, gid, item))
        self.db.execute(
            "DELETE FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id=? AND qty<=0",
            (uid, gid, item))
        self.db.execute(
            """INSERT INTO dnd_inventory (user_id, guild_id, item_id, qty, equipped)
               VALUES (?, ?, ?, ?, 0)
               ON CONFLICT(user_id, guild_id, item_id) DO UPDATE SET qty=qty+?""",
            (t_uid, gid, item, qty, qty))

        qty_txt = f"×{qty} " if qty > 1 else ""
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"🎒 Gave {qty_txt}**{label}** to **{target.display_name}**.",
                color=var.COLOR_WIN))

    @backpack_give.autocomplete("item")
    async def _backpack_give_ac(self, interaction: discord.Interaction, current: str):
        uid, gid = str(interaction.user.id), str(interaction.guild_id)
        rows = self.db.execute(
            "SELECT item_id, qty FROM dnd_inventory WHERE user_id=? AND guild_id=? AND qty>0",
            (uid, gid)) or []
        choices = []
        for iid, qty in rows:
            d     = self._item(iid)
            label = f"{d['name']}{f' ×{qty}' if qty > 1 else ''}" if d else iid
            if current.lower() in label.lower():
                choices.append(app_commands.Choice(name=label, value=iid))
        return choices[:25]



async def setup(bot: commands.Bot):
    await bot.add_cog(CharacterCog(bot))
    log.info("✅ DND/Character cog loaded")
