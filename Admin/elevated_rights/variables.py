from utils.config_loader import get_bot_token, load_config

BOT_TOKEN = get_bot_token()
config = load_config()
GUILD_ID = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# How often (seconds) the background loop checks for expired grants
CHECK_INTERVAL_SECONDS = 60

# Longest duration a single /elevate can grant, in hours. Set to 0 to disable the cap.
MAX_DURATION_HOURS = 24 * 7  # 1 week

# Duration used if the user omits the `duration` option on /elevate
DEFAULT_DURATION = "1h"

# Embed colors
COLOR_INFO  = 0x5865F2  # blurple
COLOR_ERROR = 0xED4245  # red
