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

ITEMS = []  # All items live in DND_DLC — loaded at startup via register(api).

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
