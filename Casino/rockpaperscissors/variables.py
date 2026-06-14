from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ── Bet limits ────────────────────────────────────────────────────────────────
MIN_BET = 10
MAX_BET = -1   # -1 = no limit

# ── Timers ────────────────────────────────────────────────────────────────────
CHALLENGE_TIMEOUT = 30   # seconds for challenged user to accept
PICK_TIMEOUT      = 30   # seconds for both players to pick their move

# ── Currency ──────────────────────────────────────────────────────────────────
CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ── Embed colors ──────────────────────────────────────────────────────────────
COLOR_WIN   = 0x57F287
COLOR_LOSE  = 0xED4245
COLOR_TIE   = 0x95A5A6
COLOR_INFO  = 0x5865F2
COLOR_ERROR = 0xED4245
