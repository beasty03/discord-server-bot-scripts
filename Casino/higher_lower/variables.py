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
STARTING_BALANCE = 1000
CURRENCY_NAME    = config.get("currency_name",   "coins")
CURRENCY_SYMBOL  = config.get("currency_symbol", "🪙")

# Betting limits
MIN_BET = 10
MAX_BET = 5000  # set to 0 for no limit

# Numbers drawn from this range (inclusive)
NUMBER_RANGE = (1, 10)

# Payout multipliers per correct round (round 1 = index 0, round 2 = index 1, …)
# Players can cash out after any correct guess to lock in that multiplier
ROUND_MULTIPLIERS = [1.8, 3.0, 5.0, 8.0, 12.0]

# Embed colors
COLOR_WIN     = 0x57F287  # green
COLOR_LOSE    = 0xED4245  # red
COLOR_ERROR   = 0xED4245  # red
COLOR_INFO    = 0x5865F2  # blurple
COLOR_PLAYING = 0x9B59B6  # purple

# Daily bonus
ENABLE_DAILY_BONUS   = True
DAILY_BONUS_AMOUNT   = 500
DAILY_BONUS_COOLDOWN = 86400  # 24 hours

# Leaderboard
LEADERBOARD_TOP_COUNT = 10

# Seconds before buttons expire
BUTTON_TIMEOUT = 60

# Messages
MESSAGE_INSUFFICIENT_FUNDS = "You don't have enough {currency}!"
MESSAGE_INVALID_BET        = "Please enter a valid bet amount!"
MESSAGE_BET_TOO_LOW        = "Minimum bet is {min_bet} {currency}!"
MESSAGE_BET_TOO_HIGH       = "Maximum bet is {max_bet} {currency}!"
