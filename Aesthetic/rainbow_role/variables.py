# Name used when /rainbow_join auto-creates the role (only if no role is configured yet)
DEFAULT_ROLE_NAME = "🌈 Rainbow"

# How often (seconds) the role's color shifts to the next hue
DEFAULT_INTERVAL_SECONDS = 5

# Degrees (out of 360) the hue advances each tick — lower = smoother, slower full cycle
HUE_STEP_DEGREES = 6

# Lowest interval an admin can set with /set_rainbow_speed (protects against Discord rate limits)
MIN_INTERVAL_SECONDS = 3

# Embed colors
COLOR_INFO  = 0x5865F2  # blurple
COLOR_ERROR = 0xED4245  # red
