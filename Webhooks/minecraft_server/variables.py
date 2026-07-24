from utils.config_loader import get_bot_token, load_config

BOT_TOKEN = get_bot_token()
config = load_config()
GUILD_ID = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ── Pterodactyl client API — one or many game servers ─────────────────────────
# This controls the game server(s) (what Wings runs *inside* a container),
# not the Panel/Wings/database containers themselves — those are managed via
# `docker compose`, not this cog.
#
# Multi-server config shape (config.json), one entry per Pterodactyl server,
# keyed by the server's name (used to select it and shown in embeds):
# {
#   "minecraft_servers": {
#     "Survival": {"server_id": "abc12345", "description": "Main survival world"},
#     "Creative": {
#       "server_id": "def67890",
#       "panel_url": "http://other-panel.duckdns.org", "client_api_key": "ptlc_..."
#     }
#   },
#   "minecraft_default_server": "Survival",
#
#   # Shared fallbacks — used by any entry above that omits its own
#   # panel_url / client_api_key (the common case: one panel, many servers on it).
#   "minecraft_panel_url": "http://<subdomain>.duckdns.org",
#   "minecraft_client_api_key": "ptlc_..."
# }
#
# `server_id` is the short identifier from the panel URL, e.g. the "abc12345"
# in http://.../server/abc12345 — not the long UUID from the Application API.
# `client_api_key` must be a *Client* API key (Panel → Account → API
# Credentials), never the Application key used for provisioning.
# `description` is optional — a short blurb shown alongside the server in embeds.
#
# Single-server setups can keep using the old flat shape below — it's adopted
# automatically as one entry keyed by its display_name (or "Minecraft Server" if unset):
# { "minecraft_server": {"panel_url": ..., "client_api_key": ..., "server_id": ..., "display_name": ...} }

PANEL_URL      = (config.get('minecraft_panel_url') or '').rstrip('/')
CLIENT_API_KEY = config.get('minecraft_client_api_key', '')


def _normalize_servers() -> dict:
    raw = config.get('minecraft_servers')
    if isinstance(raw, dict) and raw:
        return raw
    if isinstance(raw, list) and raw:
        out = {}
        for entry in raw:
            key = entry.get('key') or entry.get('name') or entry.get('server_id')
            if key:
                out[key] = entry
        return out

    # Back-compat: old single-server flat shape
    legacy = config.get('minecraft_server', {})
    sid = config.get('minecraft_server_id') or legacy.get('server_id')
    if sid:
        name = legacy.get('display_name', 'Minecraft Server')
        return {
            name: {
                'server_id':      sid,
                'panel_url':      config.get('minecraft_panel_url') or legacy.get('panel_url', ''),
                'client_api_key': config.get('minecraft_client_api_key') or legacy.get('client_api_key', ''),
            }
        }
    return {}


SERVERS = _normalize_servers()
DEFAULT_SERVER_NAME = config.get('minecraft_default_server') or (next(iter(SERVERS), None))

# How long the /mc_stop and /mc_restart confirmation prompts stay active (seconds)
CONFIRM_TIMEOUT = 30

# Embed colors
COLOR_OK    = 0x57F287  # green
COLOR_WARN  = 0xFEE75C  # yellow
COLOR_ERROR = 0xED4245  # red
COLOR_INFO  = 0x5865F2  # blurple
