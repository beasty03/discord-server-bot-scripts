from utils.config_loader import get_bot_token, load_config

BOT_TOKEN = get_bot_token()
config = load_config()
GUILD_ID = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# Fallback channel name when none is set via /selfroles_channel
DEFAULT_CHANNEL_NAME = "roles"

# Role panel embed appearance
PANEL_TITLE       = "Self-Assignable Roles"
PANEL_DESCRIPTION = "Click a button below to add or remove a role from yourself."
PANEL_COLOR       = 0x5865F2  # blurple

# Embed colors
COLOR_INFO  = 0x5865F2  # blurple
COLOR_ERROR = 0xED4245  # red
