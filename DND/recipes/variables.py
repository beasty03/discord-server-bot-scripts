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

RECIPES: list[dict] = []  # all recipes are now registered via DND_DLC/recipes/variables.py

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
