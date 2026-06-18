from pathlib import Path
from utils.config_loader import get_bot_token, load_config
import importlib.util as _ilu

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ── Load structured game data from DungeonMaster_data/ ──────────────────────
def _load(name: str, path: Path):
    spec = _ilu.spec_from_file_location(name, path)
    mod  = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_data_root = Path(__file__).parent.parent / "DungeonMaster_data"
_dm_data   = _load("dm_data", _data_root / "data.py")

# ============================================================================
# ABILITY SCORES
# ============================================================================

ABILITIES = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]

ABILITY_ABBR = {
    "strength":     "STR",
    "dexterity":    "DEX",
    "constitution": "CON",
    "intelligence": "INT",
    "wisdom":       "WIS",
    "charisma":     "CHA",
}

ROLL_METHOD    = "roll"
STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

# ============================================================================
# RACES — human, dwarf, elf from DungeonMaster_data. Extra races via DND_DLC.
# ============================================================================

RACES = _dm_data.RACES

# ============================================================================
# CLASSES — fighter, ranger, wizard from DungeonMaster_data. Extra classes via DND_DLC.
# ============================================================================

CLASSES = _dm_data.CLASSES

# ============================================================================
# ITEMS — unchanged; shop, recipes, and scribe depend on this list.
# ============================================================================

ITEMS = [
    {"id": "longsword",     "name": "Longsword",     "slot": "weapon",     "weapon_type": "martial", "ability": "strength",     "dmg": "1d8",  "handed": 1},
    {"id": "shortsword",    "name": "Shortsword",    "slot": "weapon",     "weapon_type": "martial", "ability": "dexterity",    "dmg": "1d6",  "handed": 1},
    {"id": "greataxe",      "name": "Greataxe",      "slot": "weapon",     "weapon_type": "martial", "ability": "strength",     "dmg": "1d12", "handed": 2},
    {"id": "greatsword",    "name": "Greatsword",    "slot": "weapon",     "weapon_type": "martial", "ability": "strength",     "dmg": "2d6",  "handed": 2},
    {"id": "handaxe",       "name": "Handaxe",       "slot": "weapon",     "weapon_type": "simple",  "ability": "strength",     "dmg": "1d6",  "handed": 1},
    {"id": "dagger",        "name": "Dagger",        "slot": "weapon",     "weapon_type": "simple",  "ability": "dexterity",    "dmg": "1d4",  "handed": 1},
    {"id": "shortbow",      "name": "Shortbow",      "slot": "weapon",     "weapon_type": "simple",  "ability": "dexterity",    "dmg": "1d6",  "handed": 2, "ranged": True},
    {"id": "longbow",       "name": "Longbow",       "slot": "weapon",     "weapon_type": "martial", "ability": "dexterity",    "dmg": "1d8",  "handed": 2, "ranged": True},
    {"id": "quarterstaff",  "name": "Quarterstaff",  "slot": "weapon",     "weapon_type": "simple",  "ability": "strength",     "dmg": "1d8",  "handed": 1},
    {"id": "mace",          "name": "Mace",          "slot": "weapon",     "weapon_type": "simple",  "ability": "strength",     "dmg": "1d6",  "handed": 1},
    {"id": "rapier",        "name": "Rapier",        "slot": "weapon",     "weapon_type": "martial", "ability": "dexterity",    "dmg": "1d8",  "handed": 1},
    {"id": "shield",        "name": "Shield",        "slot": "offhand",    "ac_bonus": 2},
    {"id": "leather_armor", "name": "Leather Armor", "slot": "armor"},
    {"id": "chain_mail",    "name": "Chain Mail",    "slot": "armor",      "ac_bonus": 4},
    {"id": "spellbook",     "name": "Spellbook",     "slot": "misc"},
    {"id": "small_health_potion", "name": "Small Health Potion", "emoji": "🧪",
     "slot": "consumable", "heal_expr": "1d4+1",  "tier": "common",   "sell": 8},
    {"id": "health_potion",       "name": "Health Potion",       "emoji": "🧪",
     "slot": "consumable", "heal_expr": "2d4+2",  "tier": "uncommon", "sell": 20},
    {"id": "large_health_potion", "name": "Large Health Potion", "emoji": "🧪",
     "slot": "consumable", "heal_expr": "4d4+4",  "tier": "rare",     "sell": 45},
    {"id": "herb",          "name": "Herb",          "emoji": "🌿", "slot": "material", "tier": "common",   "sell": 3},
    {"id": "leather_scrap", "name": "Leather Scrap", "emoji": "🪶", "slot": "material", "tier": "uncommon", "sell": 5},
    {"id": "arcane_shard",  "name": "Arcane Shard",  "emoji": "💎", "slot": "material", "tier": "rare",     "sell": 15},
    {"id": "recipe_hp_medium", "name": "Recipe: Health Potion",       "emoji": "📜",
     "slot": "recipe", "unlocks": "health_potion",       "sell": 60},
    {"id": "recipe_hp_large",  "name": "Recipe: Large Health Potion", "emoji": "📜",
     "slot": "recipe", "unlocks": "large_health_potion",  "sell": 150},
    {"id": "reroll_token",      "name": "Character Reroll Token", "slot": "misc"},
    {"id": "boar_tusk_charm",   "name": "Boar Tusk Charm",        "slot": "misc"},
    # Beast Master companions — bought from shop, auto-used by Beast Master rangers.
    # best-to-worst checked at combat init; wolf fallback is free (no item needed).
    {"id": "wolf_companion",         "name": "Wolf Companion",         "emoji": "🐺",
     "slot": "companion", "beast_name": "Wolf",        "beast_dmg": "1d6+2", "beast_atk_mod": -2,
     "tier": "common",    "sell": 50},
    {"id": "eagle_companion",        "name": "Eagle Companion",        "emoji": "🦅",
     "slot": "companion", "beast_name": "Eagle",       "beast_dmg": "1d4+3", "beast_atk_mod":  0,
     "tier": "uncommon",  "sell": 110},
    {"id": "bear_companion",         "name": "Bear Companion",         "emoji": "🐻",
     "slot": "companion", "beast_name": "Bear",        "beast_dmg": "1d8+3", "beast_atk_mod": -1,
     "tier": "rare",      "sell": 200},
    {"id": "baby_dragon_companion",  "name": "Baby Dragon Companion",  "emoji": "🐉",
     "slot": "companion", "beast_name": "Baby Dragon", "beast_dmg": "2d6+4", "beast_atk_mod":  0,
     "tier": "legendary", "sell": 750},
    # Wizard spell scrolls — consumed by /learn_spell to permanently teach the spell.
    {"id": "scroll_misty_step",    "name": "Scroll of Misty Step",    "emoji": "📜",
     "slot": "spell_scroll", "teaches": "misty_step",    "tier": "rare",  "sell": 140},
    {"id": "scroll_scorching_ray", "name": "Scroll of Scorching Ray",  "emoji": "📜",
     "slot": "spell_scroll", "teaches": "scorching_ray",  "tier": "rare",  "sell": 110},
    {"id": "scroll_fireball",      "name": "Scroll of Fireball",       "emoji": "📜",
     "slot": "spell_scroll", "teaches": "fireball",        "tier": "epic",  "sell": 280},
    {"id": "scroll_counterspell",  "name": "Scroll of Counterspell",   "emoji": "📜",
     "slot": "spell_scroll", "teaches": "counterspell",    "tier": "epic",  "sell": 220},
]

# ============================================================================
# LEVELING
# ============================================================================

REST_COST = 10

XP_THRESHOLDS = [
    0, 0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000,
    85000, 100000, 120000, 140000, 165000, 195000, 225000, 265000, 305000, 355000,
]
MAX_LEVEL = 20

# ============================================================================
# CLASS FEATURES — fighter, ranger, wizard from DungeonMaster_data. Extra classes via DND_DLC.
# ============================================================================

CLASS_FEATURES = _dm_data.CLASS_FEATURES

# ============================================================================
# RACE TRAITS — human, dwarf, elf from DungeonMaster_data. Extra races via DND_DLC.
# ============================================================================

RACE_TRAITS = _dm_data.RACE_TRAITS

# ============================================================================
# COMBAT FEATURES — fighter, ranger, wizard from DungeonMaster_data. Extra classes via DND_DLC.
# ============================================================================

COMBAT_FEATURES = _dm_data.COMBAT_FEATURES

# ============================================================================
# SUBCLASS COMBAT FEATURES — fighter/ranger/wizard subclasses from DungeonMaster_data. Extra via DND_DLC.
# ============================================================================

SUBCLASS_COMBAT_FEATURES = _dm_data.SUBCLASS_COMBAT_FEATURES

# ============================================================================
# LEVEL-UP CHOICES — fighter, ranger, wizard from DungeonMaster_data. Extra classes via DND_DLC.
# ============================================================================

LEVEL_UP_CHOICES = _dm_data.LEVEL_UP_CHOICES

# ============================================================================
# SHEET DELETION 
# ============================================================================

DELETION_COOLDOWN_DAYS = 0

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_DND   = 0x8E44AD
COLOR_INFO  = 0x5865F2
COLOR_WIN   = 0x57F287
COLOR_ERROR = 0xED4245

# ── Wizard spell data (re-exported from data.py for engine access) ────────────
WIZARD_CANTRIPS:        set[str]   = _dm_data.WIZARD_CANTRIPS
WIZARD_STARTING_SPELLS: list[str]  = _dm_data.WIZARD_STARTING_SPELLS
WIZARD_SPELLS:          list[dict] = _dm_data.WIZARD_SPELLS
