from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ============================================================================
# GAME SETTINGS
# ============================================================================

ROWS = 6
COLS = 7

MIN_BET        = 10
MAX_BET        = -1    # -1 = no limit
BUTTON_TIMEOUT = 180   # seconds before game auto-closes

WIN_MULTIPLIER = 2.0   # payout when player wins (includes stake)

PLAYER_EMOJI = "🔴"
BOT_EMOJI    = "🟡"
EMPTY_EMOJI  = "⚫"

COL_LABELS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣"]

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_WIN     = 0x57F287
COLOR_LOSE    = 0xED4245
COLOR_DRAW    = 0xF1C40F
COLOR_ERROR   = 0xED4245
COLOR_PLAYING = 0x5865F2
