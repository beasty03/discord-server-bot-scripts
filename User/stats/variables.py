from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ── Currency ──────────────────────────────────────────────────────────────────
CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ── Level system ──────────────────────────────────────────────────────────────
# Level is computed from total games played: level = floor(sqrt(games)) + 1
# Level 1 = 0 games, Level 2 = 1 game, Level 5 = 16 games, Level 11 = 100 games
LEVEL_BAR_LENGTH = 12   # characters in the progress bar

# ── Embed colors ──────────────────────────────────────────────────────────────
COLOR_INFO  = 0x5865F2   # blurple
COLOR_ERROR = 0xED4245   # red
