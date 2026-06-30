from utils.config_loader import get_bot_token, load_config
from pathlib import Path

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')
CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ============================================================================
# PERSONAL QUIZ
# ============================================================================

QUIZ_REWARD  = 100   # Coins awarded for a correct personal quiz answer
QUIZ_TIMEOUT = 30    # Seconds before the personal quiz times out

# ============================================================================
# QUIZ EVENT
# ============================================================================

EVENT_QUESTIONS        = 5    # Default number of questions per event
EVENT_QUESTION_TIMEOUT = 20   # Seconds each event question stays open
EVENT_REWARD_FIRST     = 250  # Max coins for the first correct answer (answer instantly)
EVENT_REWARD_MIN       = 75   # Min coins for the first correct answer (answer just before timeout)
# Only the FIRST correct answer per question wins. Reward scales linearly from
# EVENT_REWARD_FIRST (at 0 s) down to EVENT_REWARD_MIN (at EVENT_QUESTION_TIMEOUT s).

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_QUIZ  = 0x9B59B6   # purple — question embed
COLOR_WIN   = 0x57F287   # green  — correct
COLOR_LOSE  = 0xED4245   # red    — wrong / timed out
COLOR_EVENT = 0xF1C40F   # gold   — event announcements
