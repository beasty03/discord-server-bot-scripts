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

# Card suits
SUITS = ["♠", "♥", "♦", "♣"]

# Payout multipliers (amount returned including original bet)
PLAYER_MULTIPLIER = 2.0    # 1:1  — bet 100, win 200
BANKER_MULTIPLIER = 1.95   # 0.95:1 after 5% commission — bet 100, win 195
TIE_MULTIPLIER    = 9.0    # 8:1  — bet 100, win 900

# On a tie, player and banker bets are pushed (refunded) rather than lost
TIE_PUSHES_SIDE_BETS = True

# Embed colors
COLOR_PLAYER  = 0x3498DB   # blue  — player wins
COLOR_BANKER  = 0xE74C3C   # red   — banker wins
COLOR_TIE     = 0x2ECC71   # green — tie
COLOR_WIN     = 0x57F287
COLOR_LOSE    = 0xED4245
COLOR_ERROR   = 0xED4245
COLOR_INFO    = 0x5865F2
COLOR_PLAYING = 0x9B59B6

# Daily bonus
ENABLE_DAILY_BONUS   = True
DAILY_BONUS_AMOUNT   = 500
DAILY_BONUS_COOLDOWN = 86400  # 24 hours

# Leaderboard
LEADERBOARD_TOP_COUNT = 10

# Seconds before bet buttons expire
BUTTON_TIMEOUT = 60

# Messages
MESSAGE_INSUFFICIENT_FUNDS = "You don't have enough {currency}!"
MESSAGE_INVALID_BET        = "Please enter a valid bet amount!"
MESSAGE_BET_TOO_LOW        = "Minimum bet is {min_bet} {currency}!"
MESSAGE_BET_TOO_HIGH       = "Maximum bet is {max_bet} {currency}!"
