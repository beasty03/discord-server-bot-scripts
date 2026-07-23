# Minecraft Server

Lets admins start, stop, and restart one or more Minecraft servers (the game process Wings runs *inside* its container) from Discord, via the Pterodactyl **Client API**. This is separate from the Panel/Wings/database containers — those keep running via `docker compose` regardless of whether a given game server is up.

Supports a single server or many — either one panel running several servers, or multiple panels each with their own API key.

Commands: 9

## Commands

- `/mc_list` — list every configured server with its current state. Anyone can use this.
- `/mc_status [server]` — show one server's state (`running` / `starting` / `stopping` / `offline`) plus CPU, memory, and uptime. Anyone can use this.
- `/mc_start [server]` — send a start signal. No-ops if already `running` or `starting`.
- `/mc_stop [server]` — send a stop signal, after a Confirm/Cancel prompt (disconnects all players).
- `/mc_restart [server]` — send a restart signal, after a Confirm/Cancel prompt (disconnects all players).
- `/set_mc_server <key> <server_id> [display_name] [panel_url] [client_api_key]` — add or update a server **without editing any config file or restarting the bot**. Only pass `panel_url`/`client_api_key` if this particular server is on a different panel/account than the shared default.
- `/remove_mc_server <key>` — remove a server added via `/set_mc_server`. Can't remove one that only exists in the static config file.
- `/set_mc_default <key>` — change which server the other commands act on when `server` is omitted.
- `/view_mc_config` — show every configured server (key, server ID, panel, masked API key) and whether each came from the config file or `/set_mc_server`.

`server` is optional everywhere and autocompletes from your configured servers — omit it to act on the default (see `/set_mc_default`).

`/mc_start`, `/mc_stop`, `/mc_restart`, `/set_mc_server`, `/remove_mc_server`, `/set_mc_default`, and `/view_mc_config` all require the **Administrator** permission.

## How the bot knows which API/server to talk to

There's no auto-discovery — a Client API key and a server ID are account-specific secrets that only exist once you generate/create them in the Panel's web UI, so they have to be entered once, either:

- **at runtime**, with `/set_mc_server` (recommended — no redeploy needed, and it's how you'd add a server that lives on a completely different panel/host later), or
- **at deploy time**, by editing `variables.py` / the shared config file (see below).

Whichever entry a server came from, it resolves its `panel_url` and `client_api_key` independently: if that entry doesn't specify its own, it falls back to the shared `PANEL_URL` / `CLIENT_API_KEY`. That's what makes "a server on another host" just work — set `panel_url`/`client_api_key` **only on that one entry** via `/set_mc_server`, and every other server keeps using the shared default. Runtime entries (`/set_mc_server`) always take priority over a config-file entry with the same key.

## Settings (variables.py / config file)

Configure one or more servers under `minecraft_servers` in the shared config file — this is the static baseline; `/set_mc_server` writes to `mc_servers_config.json` next to this cog and overlays on top of it, so you don't need to touch this file at all if you'd rather configure everything from Discord:

```json
{
  "minecraft_servers": {
    "survival": {
      "server_id": "abc12345",
      "display_name": "Survival"
    },
    "creative": {
      "server_id": "def67890",
      "display_name": "Creative",
      "panel_url": "http://other-panel.duckdns.org",
      "client_api_key": "ptlc_..."
    }
  },
  "minecraft_default_server": "survival",

  "minecraft_panel_url": "http://<subdomain>.duckdns.org",
  "minecraft_client_api_key": "ptlc_..."
}
```

- `server_id` (required per entry) — the short server identifier from the panel URL, e.g. the `abc12345` in `http://.../server/abc12345` (not the long UUID).
- `panel_url` / `client_api_key` (optional per entry) — only needed if that server lives on a **different** panel/account than the shared fallback. Most setups (one panel, several servers) can omit these and rely on the top-level `minecraft_panel_url` / `minecraft_client_api_key`.
- `display_name` (optional) — shown in embeds instead of the raw key.
- `minecraft_default_server` — which key `/mc_status`, `/mc_start`, `/mc_stop`, `/mc_restart` use when `server` is omitted. Defaults to the first entry in `minecraft_servers` if unset.

`client_api_key` must be a **Client** API key from Panel → Account → API Credentials — **not** the Application API key used for provisioning/admin.

### Single-server shorthand

If you only run one server you can skip `minecraft_servers` entirely and use the flat legacy shape — it's adopted automatically as a single entry keyed `default`:

```json
{
  "minecraft_server": {
    "panel_url": "http://<subdomain>.duckdns.org",
    "client_api_key": "ptlc_...",
    "server_id": "abc12345",
    "display_name": "Discordforge"
  }
}
```

Other variables in `variables.py`:

- `CONFIRM_TIMEOUT` — how long the `/mc_stop` / `/mc_restart` confirmation buttons stay active, default `30` seconds.

## Setup

### Prerequisites

- Python 3.10 or higher
- Discord bot token
- [auto-discord-server-deployment](https://github.com/beasty03/auto-discord-server-deployment) setup completed
- A running Pterodactyl Panel + Wings instance with each Minecraft server already created
- A Client API key (not Application) generated from each panel you use
- `aiohttp` installed (`pip install aiohttp`)

### Steps

1. **Copy this folder into your cogs directory:**
   ```
   auto-discord-server-deployment/cogs/Webhooks/minecraft_server/
   ```

2. **Add your server(s)** either with `/set_mc_server` after the bot is running (no restart needed), or under `minecraft_servers` in the config file (or use the single-server shorthand above).

3. **Load the cog** in your bot launcher as `Webhooks.minecraft_server.minecraft_server`.

4. Run `/mc_list` to confirm the bot can reach every configured server before trying `/mc_start`.

> `mc_servers_config.json` (created next to this cog the first time `/set_mc_server` is used) can contain a raw Client API key — it's gitignored, never commit it.

## How It Works

All commands call the Pterodactyl **Client API** (`/api/client/servers/{id}/...`), authenticated with a Bearer token:

- `GET /servers/{id}/resources` — current power state + live resource usage, used by `/mc_status`, `/mc_list`, and to skip redundant start/stop calls.
- `POST /servers/{id}/power` with `{"signal": "start" | "stop" | "restart"}` — the actual power action.

Each configured server resolves its own `panel_url` / `client_api_key`, falling back to the shared `minecraft_panel_url` / `minecraft_client_api_key` when it doesn't specify its own — so one panel with several servers only needs the fallback set once, while a server on a different panel/account can override both.

`/mc_stop` and `/mc_restart` show a Confirm/Cancel button view first since both disconnect every player currently on that server; the signal is only sent after Confirm is pressed. Nothing here touches the Panel, Wings, or database containers — those are managed with `docker compose` on the host, not through Discord.
