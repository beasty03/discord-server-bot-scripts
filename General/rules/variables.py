from utils.config_loader import get_bot_token, load_config

BOT_TOKEN = get_bot_token()
config = load_config()
GUILD_ID = int(config['guild_id'])
SERVER_NAME = config['server_name']

# Fallback channel name when none is set via /rules_channel
DEFAULT_CHANNEL_NAME = "rules"

# Rules embed appearance
RULES_TITLE = "Server Rules"
RULES_COLOR = 0x5865F2  # blurple

# Embed colors
COLOR_INFO  = 0x5865F2  # blurple
COLOR_ERROR = 0xED4245  # red
