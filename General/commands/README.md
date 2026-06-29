
# 📋 Commands

Posts and maintains a pinned command list in a designated channel, grouped by category. Admins set the channel once — the bot auto-updates the post on every restart and on demand. A setup status embed is also sent to `#bot-logs` whenever something is not configured.

## 📋 Features

- 📌 **Pinned command list** — posts a multi-embed message listing all loaded slash commands grouped by category (Casino, User, General, Events, DnD, Webhooks)
- 🔄 **Auto-refresh on startup** — updates the existing pinned post every time the bot restarts, no manual action needed
- ⚠️ **Setup warnings** — sends a status embed to `#bot-logs` on startup and refresh if the welcome channel, member role, roles panel, or command channel are not configured
- 🛡️ **Admin view** — `/see_admin_commands` shows admin-only commands (Config, Welcome System, Rules, Commands) in an ephemeral embed
- 🔒 **Admin-only** — all three commands require Administrator permission
- 🚫 **`set_*` filtered** — setup commands are automatically hidden from the public list

## 🚀 Installation

Load the cog as `General.commands.commands`.

## 🎮 Commands

| Command | Description |
|---------|-------------|
| `/set_command_channel <channel>` | Set the channel where the command list is posted and pinned |
| `/refresh_commands` | Manually refresh the command list and server status |
| `/see_admin_commands` | Show all admin-only commands (ephemeral, visible only to you) |

## ⚙️ How it works

1. Run `/set_command_channel #your-channel` — the bot posts and pins the command list there and saves the message ID.
2. On every bot restart the pinned post is edited in place automatically.
3. Use `/refresh_commands` any time to update it manually (e.g. after loading new cogs).
4. If the welcome channel, member role, self-roles panel, or command channel are not yet configured, a warning embed appears in `#bot-logs`.

## ⚙️ Configuration (`variables.py`)

Colors and server name/guild ID are loaded automatically from the shared config file — no manual changes needed.
