from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ============================================================================
# CHALLENGE SETTINGS
# ============================================================================

BET_MIN           = 100
CHALLENGE_TIMEOUT = 60    # seconds the opponent has to accept

# ============================================================================
# FIGHT FORMULAS
# ============================================================================

# Fight HP: health * multiplier, clamped
STAT_HP_MULT = 2.0
STAT_HP_MIN  = 20
STAT_HP_MAX  = 200

# Attack: weighted sum of weight + energy + happiness, clamped
STAT_ATK_WEIGHT = 0.8
STAT_ATK_ENERGY = 0.5
STAT_ATK_HAPPY  = 0.2
STAT_ATK_MIN    = 10
STAT_ATK_MAX    = 60

# Defense: fraction of health, clamped
STAT_DEF_HEALTH = 0.2
STAT_DEF_MIN    = 0
STAT_DEF_MAX    = 20

# ============================================================================
# FIGHT MECHANICS
# ============================================================================

MAX_ROUNDS  = 10
CRIT_CHANCE  = 0.10   # 10 % chance per attack
DODGE_CHANCE = 0.05   # 5 % chance to fully avoid an incoming hit

# Random variance per hit (added to base damage)
DMG_VARIANCE_MIN = -5
DMG_VARIANCE_MAX = 10

CRIT_MULTIPLIER = 1.5

# ============================================================================
# POST-FIGHT STAT EFFECTS
# ============================================================================

WIN_HAPPINESS_GAIN  = 10
WIN_HEALTH_GAIN     = 5
LOSE_HAPPINESS_LOSS = 15
LOSE_HEALTH_LOSS    = 10   # never lethal — floor is 1

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_CHALLENGE = 0xF1C40F   # gold — challenge waiting
COLOR_FIGHT     = 0xFF4500   # orange-red — fight in progress
COLOR_WIN       = 0x57F287   # green — victory
COLOR_LOSE      = 0xED4245   # red — defeat
COLOR_DRAW      = 0x5865F2   # blurple — draw
COLOR_ERROR     = 0xED4245
COLOR_OK        = 0x57F287
