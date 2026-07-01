from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ============================================================================
# PET TYPES
# ============================================================================

PET_TYPES = {
    "cat":        {"emoji": "🐱",  "name": "Cat"},
    "dog":        {"emoji": "🐶",  "name": "Dog"},
    "bunny":      {"emoji": "🐰",  "name": "Bunny"},
    "chick":      {"emoji": "🐤",  "name": "Chick"},
    "turtle":     {"emoji": "🐢",  "name": "Turtle"},
    "dragon":     {"emoji": "🐲",  "name": "Dragon"},
    "waifu":      {"emoji": "🌸",  "name": "Waifu"},
    "goth_mommy": {"emoji": "🖤",  "name": "Goth Mommy"},
}

# ============================================================================
# STARTING STATS
# ============================================================================

START_HUNGER    = 20    # 0 = full, 100 = starving
START_HAPPINESS = 80
START_HEALTH    = 100
START_ENERGY    = 100
START_WEIGHT    = 10

# ============================================================================
# DECAY RATES  (per hour)
# ============================================================================

DECAY_HUNGER    = 5.0   # hunger increases each hour
DECAY_HAPPINESS = 3.0   # happiness decreases each hour
DECAY_ENERGY    = 3.0   # energy decreases each hour

# Health changes per hour based on conditions
HEALTH_LOSS_STARVING  = 3.0   # hunger >= 80
HEALTH_LOSS_HUNGRY    = 1.0   # hunger >= 60
HEALTH_LOSS_UNHAPPY   = 2.0   # happiness <= 20
HEALTH_LOSS_LOW_HAPPY = 0.5   # happiness <= 40
HEALTH_LOSS_TIRED     = 1.0   # energy <= 10
HEALTH_GAIN_THRIVING  = 0.5   # hunger <= 30, happiness >= 60, energy >= 50

# ============================================================================
# ACTION CONFIG
# ============================================================================

FEED_COOLDOWN_MINS   = 30
FEED_HUNGER_REDUCE   = 35
FEED_WEIGHT_GAIN     = 1
FEED_COST            = 50    # coins (0 = free)

PLAY_COOLDOWN_MINS   = 60
PLAY_HAPPINESS_GAIN  = 25
PLAY_ENERGY_COST     = 20
PLAY_WEIGHT_LOSS     = 1

CLEAN_COOLDOWN_MINS  = 240   # 4 hours
CLEAN_HEALTH_GAIN    = 15
CLEAN_HAPPINESS_GAIN = 5

REST_COOLDOWN_MINS   = 180   # 3 hours
REST_ENERGY_GAIN     = 50
REST_HAPPINESS_GAIN  = 5

WEIGHT_MIN  = 5
WEIGHT_MAX  = 25

# ============================================================================
# LIFE STAGES  (age in days)
# ============================================================================

STAGE_EGG_DAYS   = 1    # 0 → 1 day
STAGE_BABY_DAYS  = 3    # 1 → 3 days
STAGE_CHILD_DAYS = 7    # 3 → 7 days
STAGE_TEEN_DAYS  = 14   # 7 → 14 days
                         # 14+ = Adult

# ============================================================================
# VIEW TIMEOUT
# ============================================================================

VIEW_TIMEOUT = 90    # seconds before buttons disable

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_HAPPY   = 0x57F287   # green
COLOR_NEUTRAL = 0x5865F2   # blurple
COLOR_SAD     = 0xF1C40F   # yellow
COLOR_SICK    = 0xED4245   # red
COLOR_DEAD    = 0x36393F   # dark grey
COLOR_ERROR   = 0xED4245
COLOR_OK      = 0x57F287
