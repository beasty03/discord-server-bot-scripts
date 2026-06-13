from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ── Channel ───────────────────────────────────────────────────────────────────
EVENT_CHANNEL_ID = 0  # ← set via /set_double_money_channel

# ── Multiplier range ──────────────────────────────────────────────────────────
# A random multiplier is picked uniformly in [MIN, MAX] each time the event fires.
MULTIPLIER_MIN = 1.1
MULTIPLIER_MAX = 2.0

# ── Duration ──────────────────────────────────────────────────────────────────
EVENT_DURATION = 300  # seconds (5 minutes)

# ── Currency ──────────────────────────────────────────────────────────────────
CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ── Embed colors ──────────────────────────────────────────────────────────────
COLOR_ACTIVE = 0xF1C40F  # gold
COLOR_END    = 0x57F287  # green
COLOR_ERROR  = 0xED4245  # red
