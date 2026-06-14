import discord
from discord.ext import commands
from discord import app_commands
import logging
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('dnd_character_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

from forge_db import ForgeDB

log = logging.getLogger("launcher")

# ============================================================================
# REGISTRY LOOKUPS
# ============================================================================

def _get_race(rid):
    return next((r for r in var.RACES if r["id"] == rid), None)

def _get_class(cid):
    return next((c for c in var.CLASSES if c["id"] == cid), None)

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

def _derive(char: dict) -> dict:
    """Compute final scores, modifiers, AC, max HP, etc. from stored base data."""
    race  = _get_race(char["race"]) if char["race"] else None
    klass = _get_class(char["char_class"]) if char["char_class"] else None

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

_RACE_CHOICES  = [app_commands.Choice(name=r["name"], value=r["id"]) for r in var.RACES]
_CLASS_CHOICES = [app_commands.Choice(name=c["name"], value=c["id"]) for c in var.CLASSES]

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
        self.bot = bot
        self.db  = ForgeDB.get()

    async def cog_load(self):
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

    # ── helpers ───────────────────────────────────────────────────────────────

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
        max_hp = _derive(char)["max_hp"]
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

        stats = _roll_stats()
        self.db.execute(
            f"""INSERT INTO dnd_characters
                   (user_id, guild_id, name, race, char_class, level, xp,
                    strength, dexterity, constitution, intelligence, wisdom, charisma,
                    hp, created_at)
               VALUES (?, ?, ?, NULL, NULL, 1, 0, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (uid, gid, name,
             stats["strength"], stats["dexterity"], stats["constitution"],
             stats["intelligence"], stats["wisdom"], stats["charisma"],
             datetime.utcnow().isoformat()),
        )

        rolled = " · ".join(f"{var.ABILITY_ABBR[ab]} {stats[ab]}" for ab in var.ABILITIES)
        embed = discord.Embed(
            title=f"🎲 {name} enters the world!",
            description=(
                f"Rolled abilities (4d6 drop lowest):\n`{rolled}`\n\n"
                "Now pick your `/race` and `/class` to finish your character."
            ),
            color=var.COLOR_DND,
        )
        embed.set_footer(text=var.SERVER_NAME)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /race ───────────────────────────────────────────────────────────────────

    @app_commands.command(name="race", description="Set your character's race.")
    @app_commands.describe(race="Which race to play")
    @app_commands.choices(race=_RACE_CHOICES)
    async def set_race(self, interaction: discord.Interaction, race: app_commands.Choice[str]):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if not self._fetch_char(uid, gid):
            await interaction.response.send_message(embed=self._no_char_embed(), ephemeral=True)
            return

        r = _get_race(race.value)
        self.db.execute(
            "UPDATE dnd_characters SET race = ? WHERE user_id = ? AND guild_id = ?",
            (race.value, uid, gid),
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

    # ── /class ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="class", description="Set your character's class.")
    @app_commands.describe(char_class="Which class to play")
    @app_commands.choices(char_class=_CLASS_CHOICES)
    async def set_class(self, interaction: discord.Interaction, char_class: app_commands.Choice[str]):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if not self._fetch_char(uid, gid):
            await interaction.response.send_message(embed=self._no_char_embed(), ephemeral=True)
            return

        c = _get_class(char_class.value)
        self.db.execute(
            "UPDATE dnd_characters SET char_class = ? WHERE user_id = ? AND guild_id = ?",
            (char_class.value, uid, gid),
        )

        # Grant starting equipment (only adds missing items — won't duplicate).
        for item_id in c.get("start_items", []):
            self.db.execute(
                """INSERT INTO dnd_inventory (user_id, guild_id, item_id, qty, equipped)
                   VALUES (?, ?, ?, 1, 0)
                   ON CONFLICT(user_id, guild_id, item_id) DO NOTHING""",
                (uid, gid, item_id),
            )

        self._recompute_hp(uid, gid)

        gear = ", ".join(_get_item(i)["name"] for i in c.get("start_items", []) if _get_item(i)) or "none"
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

        d = _derive(char)
        race  = _get_race(char["race"])
        klass = _get_class(char["char_class"])

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

        d     = _derive(char)
        klass = _get_class(char["char_class"]) if char["char_class"] else None

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
            item    = _get_item(item_id)
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

    # ── /level ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="level", description="Show your level and XP progress.")
    async def level(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        char = self._fetch_char(uid, gid)
        if not char:
            await interaction.response.send_message(embed=self._no_char_embed(), ephemeral=True)
            return

        d   = _derive(char)
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
    @app_commands.choices(char_class=_CLASS_CHOICES)
    async def class_upgrade(self, interaction: discord.Interaction, char_class: app_commands.Choice[str] | None = None):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if char_class is not None:
            cid = char_class.value
        else:
            char = self._fetch_char(uid, gid)
            cid = char["char_class"] if char else None

        if not cid:
            await interaction.response.send_message(
                embed=self._err("Specify a class, or set yours with `/class` first."),
                ephemeral=True,
            )
            return

        c        = _get_class(cid)
        features = var.CLASS_FEATURES.get(cid, [])

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

    # ── /race_upgrade ─────────────────────────────────────────────────────────────

    @app_commands.command(name="race_upgrade", description="Browse racial traits.")
    @app_commands.describe(race="Race to browse (defaults to your current race)")
    @app_commands.choices(race=_RACE_CHOICES)
    async def race_upgrade(self, interaction: discord.Interaction, race: app_commands.Choice[str] | None = None):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if race is not None:
            rid = race.value
        else:
            char = self._fetch_char(uid, gid)
            rid = char["race"] if char else None

        if not rid:
            await interaction.response.send_message(
                embed=self._err("Specify a race, or set yours with `/race` first."),
                ephemeral=True,
            )
            return

        r      = _get_race(rid)
        traits = var.RACE_TRAITS.get(rid, [])
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


async def setup(bot: commands.Bot):
    await bot.add_cog(CharacterCog(bot))
    log.info("✅ DND/Character cog loaded")
