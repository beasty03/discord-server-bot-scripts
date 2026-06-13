from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_QUOTE = 0x5865F2  # blurple
COLOR_WIN   = 0x57F287  # green
COLOR_ERROR = 0xED4245  # red
