from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ============================================================================
# CURRENCY
# ============================================================================

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ============================================================================
# BANK SETTINGS
# ============================================================================

# Minimum amount a user can /give to someone else (1 = no real minimum)
GIVE_MIN = 1
# Maximum amount per /give (0 = no limit)
GIVE_MAX = 0

# How many players to show on /top
LEADERBOARD_TOP_COUNT = 10

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_INFO  = 0x5865F2  # blurple
COLOR_WIN   = 0x57F287  # green
COLOR_ERROR = 0xED4245  # red
