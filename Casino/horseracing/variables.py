from utils.config_loader import get_bot_token, load_config
from pathlib import Path

BOT_TOKEN = get_bot_token()
config = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
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
        DATABASE_NAME = str(Path(__file__).parent.parent.parent / 'database' / 'user_database.db')
else:
    DATABASE_NAME = str(Path(__file__).parent.parent.parent / 'database' / 'user_database.db')

STARTING_BALANCE = 1000
CURRENCY_NAME    = config.get("currency_name",   "coins")
CURRENCY_SYMBOL  = config.get("currency_symbol", "🪙")

MIN_BET = 10
MAX_BET = -1  # -1 = no limit

COLOR_WIN     = 0x57F287
COLOR_LOSE    = 0xED4245
COLOR_ERROR   = 0xED4245
COLOR_INFO    = 0x5865F2
COLOR_PLAYING = 0xF1C40F

# ── Horses ───────────────────────────────────────────────────────────────────
# Edit names, emojis, odds, and chance here.
# odds   = payout multiplier on a win (e.g. 5 → bet × 5 returned)
# chance = weighted probability out of 100 (all values must sum to 100)
HORSES = [
    {"id": 1, "name": "Thunder",  "emoji": "⚡", "odds": 2,  "chance": 34},
    {"id": 2, "name": "Splash",   "emoji": "💧", "odds": 3,  "chance": 26},
    {"id": 3, "name": "Blaze",    "emoji": "🔥", "odds": 5,  "chance": 18},
    {"id": 4, "name": "Lucky",    "emoji": "🍀", "odds": 7,  "chance": 12},
    {"id": 5, "name": "Midnight", "emoji": "🌙", "odds": 9,  "chance":  7},
    {"id": 6, "name": "Comet",    "emoji": "⭐", "odds": 14, "chance":  3},
]

BUTTON_TIMEOUT       = 60   # seconds to pick a horse after joining
JOIN_WINDOW          = 45   # seconds the lobby stays open for new riders
RACE_ANIMATION_DELAY = 2.5  # seconds between mid-race and final-result frames
TRACK_LENGTH         = 12   # number of progress bar segments

MESSAGE_INSUFFICIENT_FUNDS = "You don't have enough {currency}!"
MESSAGE_INVALID_BET        = "Please enter a valid bet amount!"
MESSAGE_BET_TOO_LOW        = "Minimum bet is {min_bet} {currency}!"
MESSAGE_BET_TOO_HIGH       = "Maximum bet is {max_bet} {currency}!"
