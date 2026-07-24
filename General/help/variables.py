from utils.config_loader import get_bot_token, load_config

BOT_TOKEN = get_bot_token()
config    = load_config()
GUILD_ID  = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))

# Displayed in the help home embed footer
BOT_NAME = config.get('server_name', 'Server Bot')

# Embed colors per category
COLOR_HOME     = 0x5865F2  # blurple
COLOR_USER     = 0xF1C40F  # gold
COLOR_EVENTS   = 0x1ABC9C  # teal
COLOR_CASINO   = 0xE67E22  # orange
COLOR_GENERAL  = 0x3498DB  # blue
COLOR_WEBHOOKS = 0x9B59B6  # purple
COLOR_ADMIN    = 0xE74C3C  # red
COLOR_AESTHETIC = 0xEB459E  # pink
COLOR_ERROR    = 0xED4245
