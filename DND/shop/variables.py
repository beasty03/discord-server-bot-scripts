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
}

# ============================================================================
# BASE SHOP ITEMS
#
# id      → must match an id in character/variables.py ITEMS
# tier    → controls appearance frequency and stock quantity
# max_qty → max a single player can own at once
# ============================================================================

SHOP_ITEMS = [
    {
        "id":          "health_potion",
        "name":        "Health Potion",
        "emoji":       "🧪",
        "description": "Heals 2d4+2 HP when used in combat.",
        "price":       50,
        "max_qty":     5,
        "tier":        "common",
    },
    {
        "id":          "reroll_token",
        "name":        "Character Reroll Token",
        "emoji":       "🔄",
        "description": "Bypass the 7-day character creation cooldown once.",
        "price":       500,
        "max_qty":     3,
        "tier":        "epic",
    },
    {
        "id":          "recipe_hp_medium",
        "name":        "Recipe: Health Potion",
        "emoji":       "📜",
        "description": "Unlocks the Health Potion crafting recipe (2d4+2 heal).",
        "price":       150,
        "max_qty":     1,
        "tier":        "uncommon",
    },
    {
        "id":          "recipe_hp_large",
        "name":        "Recipe: Large Health Potion",
        "emoji":       "📜",
        "description": "Unlocks the Large Health Potion crafting recipe (4d4+4 heal).",
        "price":       400,
        "max_qty":     1,
        "tier":        "rare",
    },
]

# ============================================================================
# BASE SHOP BUNDLES
#
# items → list of (item_id, qty) tuples
# tier  → same system as items
# ============================================================================

SHOP_BUNDLES = [
    {
        "id":          "adventurers_kit",
        "name":        "Adventurer's Kit",
        "emoji":       "🎒",
        "description": "Everything you need to survive your first adventure.",
        "items":       [("health_potion", 2), ("dagger", 1)],
        "price":       120,
        "tier":        "common",
    },
    {
        "id":          "survivor_pack",
        "name":        "Survivor Pack",
        "emoji":       "🛡️",
        "description": "Three potions for when things go very wrong.",
        "items":       [("health_potion", 3)],
        "price":       130,
        "tier":        "uncommon",
    },
]

# ── Embed colours ──────────────────────────────────────────────────────────────
COLOR_SHOP  = 0xF1C40F
COLOR_WIN   = 0x57F287
COLOR_ERROR = 0xED4245
COLOR_INFO  = 0x5865F2
