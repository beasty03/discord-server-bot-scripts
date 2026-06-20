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
    "Yben":  ("516905034378903566", "Yben"),
    "yben":  ("516905034378903566", "Yben"),
    "Siebe": ("364106811504197632", "Siebe"),
    "siebe": ("364106811504197632", "Siebe"),
    "Joran": ("442295615636897822", "Joran"),
    "joran": ("442295615636897822", "Joran"),
    "Your mom":                        ("external", "Your Mom"),
    "your mom":                        ("external", "Your Mom"),
    "Some dude thats a commentator":   ("external", "Some Dude"),
}
