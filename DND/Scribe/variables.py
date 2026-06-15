from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# Channel to auto-post stories after a campaign completes.
# Set via /set_scribe_channel — 0 means no auto-post.
SCRIBE_CHANNEL_ID = 0

# Embed colors
COLOR_STORY = 0x8E44AD  # purple
COLOR_INFO  = 0x5865F2
COLOR_ERROR = 0xED4245
