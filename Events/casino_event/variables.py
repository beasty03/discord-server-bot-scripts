from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ── Channel ───────────────────────────────────────────────────────────────────
# ID of the channel where event announcements are posted.
EVENT_CHANNEL_ID = 0  # ← set this to your event channel ID

# ── Timing ────────────────────────────────────────────────────────────────────
# Random interval between events. A value is picked uniformly in [MIN, MAX] each time.
EVENT_INTERVAL_MIN = 30   # minimum minutes between events
EVENT_INTERVAL_MAX = 90   # maximum minutes between events

# How long the join window stays open (seconds).
JOIN_WINDOW = 60

# ── Economy ───────────────────────────────────────────────────────────────────
# Coins deducted from each player who joins an event.
EVENT_BET = 100

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ── Gamble resolver settings ──────────────────────────────────────────────────
GAMBLE_WIN_CHANCE     = 45   # percent chance to win
GAMBLE_WIN_MULTIPLIER = 2.0  # payout multiplier on a win

# ── Games eligible for events (can_be_multiplayer) ────────────────────────────
# Add or remove entries here to control which games can appear as events.
# Resolvers are defined in casino_event.py — add a matching key there too.
CASINO_GAMES = [
    {
        "id":          "roulette",
        "label":       "🎡 Roulette",
        "description": "Bet on Red, Black, Odd, or Even — winners split the pot!",
        "color":       0xE74C3C,
    },
    {
        "id":          "gamble",
        "label":       "🎲 Gamble",
        "description": "45% chance to win — winners split the house-doubled pot!",
        "color":       0xF1C40F,
        "pot_mode":    True,
    },
    {
        "id":          "baccarat",
        "label":       "🃏 Baccarat",
        "description": "Bet on Player, Banker, or Tie — winners split the pot!",
        "color":       0x3498DB,
    },
    {
        "id":          "horseracing",
        "label":       "🏇 Horse Racing",
        "description": "Pick a horse and hope it wins — winners split the pot!",
        "color":       0xF1C40F,
    },
    {
        "id":          "poker",
        "label":       "🃏 Poker",
        "description": "Texas Hold'em — best hand wins the house-doubled pot! (min 3 players)",
        "color":       0x9B59B6,
        "pot_mode":    True,
    },
    {
        "id":          "craps",
        "label":       "🎲 Craps",
        "description": "Everyone bets the pass line — shared dice roll, win or lose together!",
        "color":       0x2ECC71,
    },
    {
        "id":          "underover",
        "label":       "🎯 Under/Over",
        "description": "Pick Under 7, Exactly 7, or Over 7 — one shared dice roll decides all!",
        "color":       0x3498DB,
    },
]

# ── Poker event settings ──────────────────────────────────────────────────────
POKER_EVENT_MIN_PLAYERS = 3   # minimum players needed to run a poker event

# ── Embed colors ──────────────────────────────────────────────────────────────
COLOR_INFO  = 0x5865F2   # blurple — status embeds
COLOR_WIN   = 0x57F287
COLOR_ERROR = 0xED4245
