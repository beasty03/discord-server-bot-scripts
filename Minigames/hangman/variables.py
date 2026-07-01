from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ============================================================================
# WORDNIK API
# ============================================================================

# Add "wordnik_api_key": "YOUR_KEY" to your config.json to enable live words.
WORDNIK_API_KEY       = config.get("wordnik_api_key", "")
WORDNIK_API_URL       = "https://api.wordnik.com/v4/words.json/randomWord"
WORDNIK_MIN_LENGTH    = 5      # shortest word allowed
WORDNIK_MAX_LENGTH    = 10     # longest word allowed
WORDNIK_MIN_CORPUS    = 50000  # higher = more common/familiar words
WORDNIK_PART_OF_SPEECH = "noun"  # nouns are easiest to guess

# ============================================================================
# HANGMAN SETTINGS
# ============================================================================

MIN_BET       = 10
MAX_BET       = -1    # -1 = no limit
MAX_WRONG     = 6     # wrong guesses before losing
WIN_MULTIPLIER = 2.0  # payout multiplier on win (includes stake)
BUTTON_TIMEOUT = 180  # seconds before the game times out

WORDS = [
    # Food & drink
    "PIZZA", "BURGER", "COFFEE", "SUSHI", "PASTA", "WAFFLE", "PANCAKE",
    "CHOCOLATE", "STRAWBERRY", "PINEAPPLE", "AVOCADO", "BROCCOLI",
    # Animals
    "ELEPHANT", "PENGUIN", "DOLPHIN", "GORILLA", "CROCODILE", "FLAMINGO",
    "CHEETAH", "KANGAROO", "PORCUPINE", "OCTOPUS", "BUTTERFLY", "PLATYPUS",
    # Technology
    "KEYBOARD", "MONITOR", "INTERNET", "BLUETOOTH", "ALGORITHM", "DATABASE",
    "SMARTPHONE", "PROCESSOR", "HEADPHONES", "MICROPHONE",
    # Sports
    "FOOTBALL", "BASKETBALL", "SWIMMING", "VOLLEYBALL", "SKATEBOARD",
    "MARATHON", "SNOWBOARD", "BASEBALL", "BADMINTON",
    # Places & nature
    "MOUNTAIN", "WATERFALL", "LIBRARY", "STADIUM", "HOSPITAL", "PYRAMID",
    "PENINSULA", "VOLCANO", "RAINFOREST", "GLACIER",
    # Misc
    "UMBRELLA", "CALENDAR", "TELESCOPE", "SUNFLOWER", "ADVENTURE", "TREASURE",
    "LIGHTNING", "CARNIVAL", "CHANDELIER", "SYMPHONY", "DISCOVERY",
    "WILDERNESS", "BLUEPRINT", "PASSPORT", "HURRICANE", "SAXOPHONE",
    "PARACHUTE", "LABYRINTH", "CLOCKWORK", "FIREWORKS",
]

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_WIN     = 0x57F287
COLOR_LOSE    = 0xED4245
COLOR_ERROR   = 0xED4245
COLOR_PLAYING = 0x5865F2
