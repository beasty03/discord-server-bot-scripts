from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ============================================================================
# PARTY SETTINGS
# ============================================================================

# Maximum members in a party (creator included).
MAX_PARTY_SIZE = 6

# How long the /party join picker stays clickable (seconds).
JOIN_LIST_TIMEOUT = 120

# How long an invite's Accept/Decline buttons stay live (seconds).
INVITE_TIMEOUT = 300

# Hard cap on how many parties the /party join picker will list at once
# (Discord allows max 25 buttons / 5 rows per message).
MAX_JOIN_BUTTONS = 20

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_PARTY = 0x8E44AD  # purple — D&D theme
COLOR_INFO  = 0x5865F2  # blurple
COLOR_WIN   = 0x57F287  # green
COLOR_ERROR = 0xED4245  # red
