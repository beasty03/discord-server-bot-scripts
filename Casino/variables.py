# variables.py

from utils.config_loader import get_bot_token, load_config
from pathlib import Path

# ============================================================================
# CENTRAL CONFIG LOADER
# ============================================================================
 
# Load bot token and config from central config.json
BOT_TOKEN = get_bot_token()  # or get_bot_token('SpecificBotName')
config = load_config()
GUILD_ID = int(config['guild_id'])
SERVER_NAME = config['server_name']
 
# Database path from config (nested under 'paths')
if 'paths' in config:
    paths = config['paths']
    if 'database_file' in paths:
        DATABASE_NAME = str(Path(paths['database_file']))
    elif 'db_file' in paths:
        DATABASE_NAME = str(Path(paths['db_file']))
    elif 'database_dir' in paths:
        DATABASE_DIR = Path(paths['database_dir'])
        DATABASE_NAME = str(DATABASE_DIR / 'user_database.db')
    else:
        # Fallback
        PROJECT_ROOT = Path(__file__).parent.parent.parent
        DATABASE_DIR = PROJECT_ROOT / 'database'
        DATABASE_DIR.mkdir(exist_ok=True)
        DATABASE_NAME = str(DATABASE_DIR / 'user_database.db')
else:
    # Fallback: use database folder in project root
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    DATABASE_DIR = PROJECT_ROOT / 'database'
    DATABASE_DIR.mkdir(exist_ok=True)
    DATABASE_NAME = str(DATABASE_DIR / 'user_database.db')

# ============================================================================
# GAMBLE COMMAND SETTINGS
# ============================================================================

# Starting Balance
STARTING_BALANCE = 1000  # Amount of currency new users start with

# Gambling Settings
MIN_BET = 10  # Minimum bet amount
MAX_BET = 5000  # Maximum bet amount (set to 0 for no limit)

# Win/Loss Settings
WIN_MULTIPLIER = 2.0  # Multiplier for winning (2.0 = double your bet)
WIN_CHANCE = 45  # Percentage chance to win (0-100)

# Cooldown Settings
COOLDOWN_SECONDS = 5  # Cooldown between gamble commands per user

# Currency Settings
CURRENCY_NAME = "coins"  # Name of the currency (e.g., "coins", "credits", "gold")
CURRENCY_SYMBOL = "🪙"  # Emoji symbol for currency

# Embed Colors (in hex)
COLOR_WIN = 0x00FF00  # Green
COLOR_LOSE = 0xFF0000  # Red
COLOR_ERROR = 0xFFA500  # Orange
COLOR_INFO = 0x00BFFF  # Light Blue

# Messages
MESSAGE_INSUFFICIENT_FUNDS = "You don't have enough {currency}!"
MESSAGE_INVALID_BET = "Please enter a valid bet amount!"
MESSAGE_BET_TOO_LOW = "Minimum bet is {min_bet} {currency}!"
MESSAGE_BET_TOO_HIGH = "Maximum bet is {max_bet} {currency}!"
MESSAGE_WIN = "🎉 You won {amount} {currency}!"
MESSAGE_LOSE = "💸 You lost {amount} {currency}!"

# ============================================================================
# ADVANCED SETTINGS (Optional)
# ============================================================================

# Enable/Disable Features
ENABLE_DAILY_BONUS = True  # Allow users to claim daily bonus
DAILY_BONUS_AMOUNT = 500  # Amount for daily bonus
DAILY_BONUS_COOLDOWN = 86400  # 24 hours in seconds

# Leaderboard Settings
LEADERBOARD_TOP_COUNT = 10  # Number of users to show in leaderboard