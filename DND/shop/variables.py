from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ── How many slots the shop picks each day ────────────────────────────────────
MAX_SHOP_ITEMS   = 4
MAX_SHOP_BUNDLES = 2

# ── Tier definitions ──────────────────────────────────────────────────────────
# weight    → relative chance of being picked for a given day
#             (common ≈60 % of weight pool, epic ≈3 %)
# stock_min/max → how many units appear when selected
TIERS = {
    "common": {
        "label":     "Common",
        "emoji":     "⚪",
        "weight":    60,
        "stock_min": 5,
        "stock_max": 10,
    },
    "uncommon": {
        "label":     "Uncommon",
        "emoji":     "🟢",
        "weight":    25,
        "stock_min": 3,
        "stock_max": 5,
    },
    "rare": {
        "label":     "Rare",
        "emoji":     "🔵",
        "weight":    12,
        "stock_min": 1,
        "stock_max": 3,
    },
    "epic": {
        "label":     "Epic",
        "emoji":     "🟣",
        "weight":    3,
        "stock_min": 1,
        "stock_max": 1,
    },
    "legendary": {
        "label":     "Legendary",
        "emoji":     "🟡",
        "weight":    1,
        "stock_min": 1,
        "stock_max": 1,
    },
}

# ============================================================================
# BASE SHOP ITEMS
#
# id      → must match an id in character/variables.py ITEMS
# tier    → controls appearance frequency and stock quantity
# max_qty → max a single player can own at once
# ============================================================================

SHOP_ITEMS = []

SHOP_BUNDLES = []

# ── Embed colours ──────────────────────────────────────────────────────────────
COLOR_SHOP  = 0xF1C40F
COLOR_WIN   = 0x57F287
COLOR_ERROR = 0xED4245
COLOR_INFO  = 0x5865F2
