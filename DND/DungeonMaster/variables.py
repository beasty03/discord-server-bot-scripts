from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ── Timing ────────────────────────────────────────────────────────────────────
WANDER_JOIN_TIMEOUT = 60   # seconds party join window stays open
ROUND_TIMEOUT       = None # no timeout — players take as long as they need
INTERACTION_TIMEOUT = None # no timeout — players take as long as they need
KILL_MODAL_TIMEOUT  = 120  # seconds to describe the killing blow
RESULT_DELAY        = 8    # pause between rounds (seconds)

# ── Quest board ───────────────────────────────────────────────────────────────
# When more than MAX_SHOWN campaigns are available, rotate daily.
MAX_SHOWN_CAMPAIGNS = 5

# ============================================================================
# CAMPAIGNS
#
# All campaigns are registered via DND_DLC — see DND_DLC/campaigns/
# Engine loads them automatically at startup via each campaign's register(api).
# ============================================================================

CAMPAIGNS = []

# ── Embed colors ──────────────────────────────────────────────────────────────
COLOR_CAMPAIGN    = 0x8E44AD
COLOR_COMBAT      = 0xE74C3C
COLOR_INTERACTION = 0x3498DB
COLOR_WIN         = 0x57F287
COLOR_ERROR       = 0xED4245
COLOR_INFO        = 0x5865F2
