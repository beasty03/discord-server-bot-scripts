from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

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
# RACES / CLASSES — all content now lives in DND_DLC; engine registry is the
# source of truth.  These empty lists are fallbacks for the rare case where
# the engine cog hasn't loaded yet.
# ============================================================================

RACES   = []
CLASSES = []

# ============================================================================
# ITEMS — base equipment list.  DLC items are appended at runtime by
# CharacterCog._scan_dlc_items() via register_item().
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
    # Beast Master companions
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
    # Wizard spell scrolls
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
# DISPLAY-DATA FALLBACKS — all empty; engine registry is the real source.
# combat.py helpers fall back to these when EngineCore isn't loaded.
# ============================================================================

CLASS_FEATURES:           dict = {}
RACE_TRAITS:              dict = {}
COMBAT_FEATURES:          dict = {}
SUBCLASS_COMBAT_FEATURES: dict = {}
LEVEL_UP_CHOICES:         dict = {}

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

# ============================================================================
# WIZARD SPELL DATA — used by /prepare_spells, /spells, /learn_spell.
# Cantrips are always available; all others require /prepare_spells selection.
# ============================================================================

WIZARD_CANTRIPS: set[str] = {"magic_missile"}

WIZARD_STARTING_SPELLS: list[str] = [
    "magic_missile", "shield_spell", "burning_hands", "thunderwave",
]

WIZARD_SPELLS: list[dict] = [
    {"id": "magic_missile",  "name": "Magic Missile",  "emoji": "✨",
     "school": "evocation",   "level": 0,
     "action_type": "action", "level_req": 1, "once_per": None,
     "desc": "Auto-hit — 1d4+1 bolts; scales to 6 bolts at Lv 16 (cantrip, always available)"},
    {"id": "shield_spell",   "name": "Shield",          "emoji": "🛡️",
     "school": "abjuration",  "level": 1,
     "action_type": "bonus",  "level_req": 1, "once_per": "combat",
     "desc": "+5 AC vs the next attack targeting you this round (bonus action, once per combat)"},
    {"id": "burning_hands",  "name": "Burning Hands",   "emoji": "🔥",
     "school": "evocation",   "level": 1,
     "action_type": "action", "level_req": 1, "once_per": "combat",
     "desc": "Cone of fire — 3d6 auto-hit; scales +1d6 per 4 levels (once per combat)"},
    {"id": "thunderwave",    "name": "Thunderwave",      "emoji": "🌊",
     "school": "evocation",   "level": 1,
     "action_type": "action", "level_req": 1, "once_per": "combat",
     "desc": "2d8 + INT thunder auto-hit; enemy ATK −2 next round (once per combat)"},
    {"id": "misty_step",     "name": "Misty Step",       "emoji": "💨",
     "school": "conjuration", "level": 2,
     "action_type": "bonus",  "level_req": 3, "once_per": "combat",
     "desc": "Teleport away — half damage from the next hit against you (bonus action, Lv 3+, once per combat)"},
    {"id": "scorching_ray",  "name": "Scorching Ray",    "emoji": "☀️",
     "school": "evocation",   "level": 2,
     "action_type": "action", "level_req": 3, "once_per": "combat",
     "desc": "Three fire rays — each needs an attack roll, 2d6 fire each hit (Lv 3+, once per combat)"},
    {"id": "fireball",       "name": "Fireball",         "emoji": "💥",
     "school": "evocation",   "level": 3,
     "action_type": "action", "level_req": 5, "once_per": "combat",
     "desc": "8d6 fire explosion auto-hit; Evocation adds INT mod bonus dmg (Lv 5+, once per combat)"},
    {"id": "counterspell",   "name": "Counterspell",     "emoji": "🚫",
     "school": "abjuration",  "level": 3,
     "action_type": "bonus",  "level_req": 5, "once_per": "combat",
     "desc": "Disrupt the enemy — they skip their attack this round (bonus action, Lv 5+, once per combat)"},
]
