from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ── Bet limits ────────────────────────────────────────────────────────────────
MIN_BET = 50
MAX_BET = -1   # -1 = no limit

# ── Player limits ─────────────────────────────────────────────────────────────
MIN_PLAYERS = 2
MAX_PLAYERS = 8

# ── Timers ────────────────────────────────────────────────────────────────────
JOIN_WINDOW     = 90   # seconds for join lobby
PREFLOP_TIMEOUT = 30   # seconds to check or fold after seeing hole cards

# ── Reveal delays ─────────────────────────────────────────────────────────────
DEAL_DELAY   = 5   # seconds between deal and flop reveal
REVEAL_DELAY = 3   # seconds between flop→turn and turn→river

# ── Currency ──────────────────────────────────────────────────────────────────
CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ── Embed colors ──────────────────────────────────────────────────────────────
COLOR_WIN   = 0x57F287
COLOR_LOSE  = 0xED4245
COLOR_INFO  = 0x5865F2
COLOR_ERROR = 0xED4245
COLOR_FLOP  = 0xF1C40F   # gold
COLOR_TURN  = 0xE67E22   # orange
COLOR_RIVER = 0xE74C3C   # red
