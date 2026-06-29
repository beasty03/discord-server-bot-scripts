from utils.config_loader import get_bot_token, load_config
from pathlib import Path

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_OK      = 0x57F287   # green  — status check passed
COLOR_WARN    = 0xF39C12   # orange — something not configured
COLOR_ERROR   = 0xED4245   # red    — command error
COLOR_STATUS  = 0x5865F2   # blurple — status header embed

COLOR_CASINO  = 0xF1C40F
COLOR_USER    = 0x3498DB
COLOR_GENERAL = 0x2ECC71
COLOR_ADMIN   = 0xE74C3C
COLOR_DND     = 0x9B59B6
COLOR_QUOTES  = 0xE67E22
COLOR_EVENTS  = 0xF39C12
COLOR_HOOKS   = 0x95A5A6
