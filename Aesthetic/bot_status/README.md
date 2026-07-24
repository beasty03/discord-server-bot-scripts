# 🤖 Bot Status

Lets admins change the bot's Discord presence — its online status (online/idle/dnd/invisible) and its activity (the "Playing ..." line shown under its name) — from a slash command instead of editing code and restarting.

Commands: 4

## Commands

- `/set_bot_status <status>` — set the online status: `online`, `idle`, `dnd`, or `invisible`.
- `/set_bot_activity <type> <text>` — set the activity verb (`playing`, `watching`, `listening`, `competing`) and its text, e.g. `watching` + `the server burn`.
- `/clear_bot_activity` — remove the activity line, keeping whatever status is set.
- `/view_bot_status` — show what's currently configured. Anyone can use this.

`/set_bot_status`, `/set_bot_activity`, and `/clear_bot_activity` require **Administrator**.

## Setup

### Prerequisites

- Python 3.10 or higher
- Discord bot token
- [auto-discord-server-deployment](https://github.com/beasty03/auto-discord-server-deployment) setup completed

### Steps

1. **Copy this folder into your cogs directory:**
   ```
   auto-discord-server-deployment/cogs/Aesthetic/bot_status/
   ```

2. **Load the cog** in your bot launcher as `Aesthetic.bot_status.bot_status`.

3. Run `/set_bot_status status:online` and `/set_bot_activity type:watching text:"the server"` to try it out.

> `bot_status_config.json` (created next to this cog the first time a setting is changed) is gitignored — it's just local runtime state, not a secret, but there's no need to commit it.

## How It Works

Status and activity are stored in `bot_status_config.json` next to this cog and reapplied via `bot.change_presence(...)` immediately whenever a command changes them. They're also reapplied automatically on every `on_ready` — so a reconnect or a full restart doesn't reset the bot back to Discord's blank default presence; it picks up wherever it was left.
