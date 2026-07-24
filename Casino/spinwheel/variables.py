from utils.config_loader import get_bot_token, load_config
from pathlib import Path

BOT_TOKEN   = get_bot_token()
config      = load_config()
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
        PROJECT_ROOT = Path(__file__).parent.parent.parent
        DATABASE_NAME = str(PROJECT_ROOT / 'database' / 'user_database.db')
else:
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    DATABASE_NAME = str(PROJECT_ROOT / 'database' / 'user_database.db')

STARTING_BALANCE = 1000
CURRENCY_NAME    = config.get("currency_name",   "coins")
CURRENCY_SYMBOL  = config.get("currency_symbol", "🪙")

# ============================================================================
# SPIN THE WHEEL SETTINGS
# ============================================================================

MIN_BET = 10
MAX_BET = -1   # -1 = no limit

# (label, multiplier, weight) — win chance for each segment is weight / sum(weights)
# Total weight: 25
# EV ≈ (0×9 + 0.5×3 + 1.2×4 + 1.5×3 + 2×2 + 3×2 + 5×1 + 10×1) / 25 = 35.8/25 ≈ 1.43×
SEGMENTS = [
    ("💀 Bust",   0.0,  9),
    ("🔴 0.5×",   0.5,  3),
    ("✨ 1.2×",   1.2,  4),
    ("💛 1.5×",   1.5,  3),
    ("💚 2×",     2.0,  2),
    ("💙 3×",     3.0,  2),
    ("💜 5×",     5.0,  1),
    ("🔥 10×",   10.0,  1),
]

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_WIN     = 0x57F287
COLOR_LOSE    = 0xED4245
COLOR_ERROR   = 0xED4245
COLOR_INFO    = 0x5865F2

# ============================================================================
# MESSAGES
# ============================================================================

MESSAGE_INSUFFICIENT_FUNDS = "You don't have enough {currency}!"
MESSAGE_BET_TOO_LOW        = "Minimum bet is {min_bet} {currency}!"
MESSAGE_BET_TOO_HIGH       = "Maximum bet is {max_bet} {currency}!"
