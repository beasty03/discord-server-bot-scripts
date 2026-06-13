from utils.config_loader import get_bot_token, load_config

BOT_TOKEN = get_bot_token()
config = load_config()
GUILD_ID = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# Default time to post yesterday's Wordle recap (interpreted in WORDLE_TIMEZONE)
WORDLE_POST_HOUR   = 0
WORDLE_POST_MINUTE = 5

# Default timezone for the post time — use any IANA name, e.g. "Europe/Brussels"
WORDLE_TIMEZONE = "UTC"

# Fallback channel name when no channel has been set via /set_wordle_channel
DEFAULT_CHANNEL_NAME = "general"

# Embed colors
COLOR_INFO  = 0x5865F2  # blurple
COLOR_ERROR = 0xED4245  # red
