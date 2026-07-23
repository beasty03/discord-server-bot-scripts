# 📖 Help

A Discord bot cog that gives users an interactive overview of all available commands, grouped by category via a dropdown select menu.

Commands: 1

## Features

- 📖 **Single command** — `/help` shows everything, no need to remember command names
- 🗂️ **Category dropdown** — browse Casino, General, Webhooks, and Admin sections
- ⚡ **Dynamic** — reads commands directly from loaded cogs at runtime; stays up to date automatically when commands are added or removed
- 👁️ **Ephemeral** — the help message is only visible to the user who ran it
- 🎨 **Color-coded embeds** — each category has its own accent color

## Commands

| Command | Description |
|---|---|
| `/help` | Open the interactive command browser |

## How It Works

1. Run `/help` — a home embed appears listing all four categories.
2. Use the **dropdown** to pick a category.
3. The embed updates in-place showing every command in that category, grouped by feature (e.g. Gamble, Blackjack, Roulette …).
4. Switch categories at any time using the same dropdown.

## Categories

| Category | Contents |
|---|---|
| 🎰 Casino | Gamble, Blackjack, Roulette, Higher or Lower, Baccarat |
| 📋 General | Rules, Self Roles |
| 🔔 Webhooks | Wordle Recap |
| 🛡️ Admin | Welcome System (admin-only setup commands) |

## Setup

### Prerequisites

- Python 3.10 or higher
- Discord bot token
- [auto-discord-server-deployment](https://github.com/beasty03/auto-discord-server-deployment) setup completed

### Steps

1. **Copy this folder into your cogs directory:**
   ```
   auto-discord-server-deployment/cogs/General/help/
   ```

2. **Load the cog** in your bot launcher as `General.help.help`.

> No extra configuration is required. The cog reads `server_name` and `guild_id` from the shared `config.json` automatically.

## Configuration (variables.py)

| Setting | Default | Description |
|---|---|---|
| `BOT_NAME` | from `config.json` | Displayed in embed footers |
| `COLOR_HOME` | `0x5865F2` | Home embed color (blurple) |
| `COLOR_CASINO` | `0xE67E22` | Casino category color (orange) |
| `COLOR_GENERAL` | `0x3498DB` | General category color (blue) |
| `COLOR_WEBHOOKS` | `0x9B59B6` | Webhooks category color (purple) |
| `COLOR_ADMIN` | `0xE74C3C` | Admin category color (red) |

## Adding a New Category

To add a new category, append an entry to the `CATEGORIES` list in `help.py`:

```python
{
    "label":       "🔧 Utilities",
    "value":       "utilities",
    "description": "Utility tools — My New Cog",
    "color":       0x1ABC9C,
    "sections": [
        ("🔧 My Feature", "MyCogClassName"),
    ],
},
```

The `sections` list maps a display name to the **class name** of the loaded cog (as it appears in `bot.cogs`).

## important: Install discord.py if missing
pip install discord.py
