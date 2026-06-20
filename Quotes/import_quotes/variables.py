from utils.config_loader import load_config

config      = load_config()
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_WIN   = 0x57F287  # green
COLOR_ERROR = 0xED4245  # red

# ============================================================================
# NAME MAPPING
# ============================================================================
# Maps names as written in old quotes to (discord_user_id, display_name).
# discord_user_id must be a string.
# Names missing from this map are still imported but stored with user_id "0"
# and flagged in the import report.
#
# Example:
#   "John":  ("123456789012345678", "John"),
#   "Janke": ("987654321098765432", "Janke"),

NAME_MAP: dict[str, tuple[str, str]] = {
    # "Name": ("discord_id", "display_name"),
}
