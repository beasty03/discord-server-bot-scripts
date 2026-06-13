from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ── Channel defaults ──────────────────────────────────────────────────────────
# Channels (by name) where regular bot commands are allowed.
# Used as fallback when no channels have been configured via /add_allowed_channel.
DEFAULT_ALLOWED_CHANNEL_NAMES = ["general"]

# Channel (by name) where admin/set commands must be run.
# Used as fallback when no channel has been set via /set_control_panel.
DEFAULT_CONTROL_PANEL_NAME = "control-panel"

# ── Role defaults ─────────────────────────────────────────────────────────────
# Role names that count as staff (Admin OR Moderator).
# Users with Discord administrator permission are always treated as staff.
DEFAULT_STAFF_ROLE_NAMES = ["Admin", "Administrator", "Moderator", "Mod"]

# ── Embed colors ──────────────────────────────────────────────────────────────
COLOR_OK    = 0x57F287
COLOR_ERROR = 0xED4245
COLOR_INFO  = 0x5865F2
