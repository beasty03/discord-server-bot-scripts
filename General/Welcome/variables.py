from utils.config_loader import get_bot_token, load_config
from pathlib import Path

BOT_TOKEN = get_bot_token()
config = load_config()
GUILD_ID = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

if 'paths' in config:
    paths = config['paths']
    if 'database_file' in paths:
        DATABASE_NAME = str(Path(paths['database_file']))
    elif 'db_file' in paths:
        DATABASE_NAME = str(Path(paths['db_file']))
    elif 'database_dir' in paths:
        DATABASE_NAME = str(Path(paths['database_dir']) / 'user_database.db')
    else:
        PROJECT_ROOT = Path(__file__).parent.parent.parent
        DATABASE_NAME = str(PROJECT_ROOT / 'database' / 'user_database.db')
else:
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    DATABASE_NAME = str(PROJECT_ROOT / 'database' / 'user_database.db')

# Required by DatabaseManager
STARTING_BALANCE = 0
CURRENCY_NAME    = config.get("currency_name",   "coins")
CURRENCY_SYMBOL  = config.get("currency_symbol", "🪙")

# Embed colors
COLOR_WIN   = 0x57F287  # green
COLOR_LOSE  = 0xED4245  # red
COLOR_ERROR = 0xED4245  # red
COLOR_INFO  = 0x5865F2  # blurple

# How many days after joining a member's messages are monitored
MONITORING_PERIOD_DAYS = 7

# How often (in hours) the activity digest is posted to #bot-logs
MESSAGE_LOG_INTERVAL_HOURS = 1

# Fallback T&C shown before an admin sets custom text via /set_terms
DEFAULT_TERMS = (
    "By clicking **Accept** you agree to:\n"
    "• Follow all rules posted in #rules\n"
    "• Treat every member with respect\n"
    "• Comply with Discord's Terms of Service (https://discord.com/terms)\n"
    "• Accept that breaking these rules may result in a mute, kick, or ban"
)
