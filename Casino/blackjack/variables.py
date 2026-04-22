# variables.py

from utils.config_loader import get_bot_token, load_config #will work when is imported into workspace
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
# BLACKJACK COMMAND SETTINGS
# ============================================================================

# Starting Balance
STARTING_BALANCE = 1000  # Amount of currency new users start with

# Betting Settings
MIN_BET = 10    # Minimum bet amount
MAX_BET = 5000  # Maximum bet amount (set to 0 for no limit)

# Blackjack Payout Multipliers
BLACKJACK_MULTIPLIER = 2.5  # Payout on natural blackjack (21 on first 2 cards) — 1.5x profit
WIN_MULTIPLIER = 2.0         # Payout on regular win — doubles your bet
PUSH_REFUND = 1.0            # Refund on tie (push) — returns original bet

# Dealer Settings
DEALER_STAND_VALUE = 17  # Dealer must stand at this value or higher

# Cooldown Settings
COOLDOWN_SECONDS = 5  # Cooldown between blackjack commands per user

# Currency Settings
CURRENCY_NAME = "coins"  # Name of the currency (e.g., "coins", "credits", "gold")
CURRENCY_SYMBOL = "🪙"   # Emoji symbol for currency

# Embed Colors (in hex)
COLOR_WIN = 0x00FF00      # Green
COLOR_LOSE = 0xFF0000     # Red
COLOR_PUSH = 0xFFFF00     # Yellow
COLOR_ERROR = 0xFFA500    # Orange
COLOR_INFO = 0x00BFFF     # Light Blue
COLOR_PLAYING = 0x9B59B6  # Purple (in-game)

# Card Suits
SUITS = ["♠", "♥", "♦", "♣"]

# Messages
MESSAGE_INSUFFICIENT_FUNDS = "You don't have enough {currency}!"
MESSAGE_INVALID_BET = "Please enter a valid bet amount!"
MESSAGE_BET_TOO_LOW = "Minimum bet is {min_bet} {currency}!"
MESSAGE_BET_TOO_HIGH = "Maximum bet is {max_bet} {currency}!"
MESSAGE_BLACKJACK = "🃏 BLACKJACK! You hit 21 on your first two cards!"
MESSAGE_WIN = "🎉 You beat the dealer and won {amount} {currency}!"
MESSAGE_LOSE = "💸 The dealer wins! You lost {amount} {currency}!"
MESSAGE_PUSH = "🤝 It's a tie! Your bet of {amount} {currency} has been returned."
MESSAGE_BUST = "💥 BUST! You went over 21 and lost {amount} {currency}!"
MESSAGE_DEALER_BUST = "💥 Dealer busted! You won {amount} {currency}!"

# ============================================================================
# ADVANCED SETTINGS (Optional)
# ============================================================================

# Enable/Disable Features
ENABLE_DAILY_BONUS = True    # Allow users to claim daily bonus
DAILY_BONUS_AMOUNT = 500     # Amount for daily bonus
DAILY_BONUS_COOLDOWN = 86400  # 24 hours in seconds

# Leaderboard Settings
LEADERBOARD_TOP_COUNT = 10  # Number of users to show in leaderboard

# Button timeout (seconds before Hit/Stand buttons expire)
BUTTON_TIMEOUT = 60
