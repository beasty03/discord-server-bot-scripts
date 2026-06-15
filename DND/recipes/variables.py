from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ============================================================================
# RECIPES
#
# id          → unique recipe identifier (matches output item id)
# tier        → visual tier badge (common / uncommon / rare / epic)
# unlock      → item id of the scroll that unlocks this recipe, or None (always known)
# inputs      → list of (item_id, qty) required materials
# output      → (item_id, qty) produced
# description → shown in /recipes and /craft
# ============================================================================

RECIPES: list[dict] = [
    {
        "id":          "small_health_potion",
        "name":        "Small Health Potion",
        "emoji":       "🧪",
        "tier":        "common",
        "unlock":      None,
        "inputs":      [("herb", 2)],
        "output":      ("small_health_potion", 1),
        "description": "A modest healing draught. Restores 1d4+1 HP.",
    },
    {
        "id":          "health_potion",
        "name":        "Health Potion",
        "emoji":       "🧪",
        "tier":        "uncommon",
        "unlock":      "recipe_hp_medium",
        "inputs":      [("herb", 3), ("leather_scrap", 1)],
        "output":      ("health_potion", 1),
        "description": "A sturdy potion brewed with tanned hide. Restores 2d4+2 HP.",
    },
    {
        "id":          "large_health_potion",
        "name":        "Large Health Potion",
        "emoji":       "🧪",
        "tier":        "rare",
        "unlock":      "recipe_hp_large",
        "inputs":      [("herb", 5), ("leather_scrap", 2), ("arcane_shard", 1)],
        "output":      ("large_health_potion", 1),
        "description": "An alchemical masterwork. Restores 4d4+4 HP.",
    },
]

# ── Tier display ──────────────────────────────────────────────────────────────
TIER_EMOJI = {
    "common":   "⚪",
    "uncommon": "🟢",
    "rare":     "🔵",
    "epic":     "🟣",
}

COLOR_RECIPES = 0x8E44AD
COLOR_WIN     = 0x57F287
COLOR_ERROR   = 0xED4245
COLOR_INFO    = 0x5865F2
