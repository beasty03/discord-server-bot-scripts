from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ============================================================================
# AUTOMOD DEFAULTS
# ============================================================================

DEFAULT_LOG_CHANNEL    = "mod-logs"

DEFAULT_SPAM_MESSAGES  = 5    # max messages
DEFAULT_SPAM_WINDOW    = 5    # per N seconds
DEFAULT_CAPS_PERCENT   = 80   # % uppercase before flagging
DEFAULT_CAPS_MIN_LEN   = 15   # minimum message length to check caps
DEFAULT_MAX_MENTIONS   = 5    # max @mentions per message
DEFAULT_WARN_THRESHOLD = 3    # violations before timeout
DEFAULT_TIMEOUT_MINS   = 5    # timeout duration in minutes

DEFAULT_LINK_WHITELIST = [
    "discord.com", "discord.gg", "tenor.com", "giphy.com",
    "imgur.com", "youtube.com", "youtu.be",
]

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_OK      = 0x57F287
COLOR_WARN    = 0xF1C40F
COLOR_ERROR   = 0xED4245
COLOR_INFO    = 0x5865F2
COLOR_STRIKE  = 0xFFA500
