# Rules

Manages a persistent server rules embed. Admins can add, edit, and remove rules via slash commands — every change automatically updates the pinned embed in place so the rules channel always shows one clean, up-to-date message.

Commands: 5

## Commands

- `/rules_channel #channel` — set the channel where the rules embed is posted
- `/rules_add <rule>` — add a new rule to the bottom of the list
- `/rules_remove <number>` — remove a rule by its number
- `/rules_edit <number> <rule>` — edit an existing rule
- `/rules_post` — post or refresh the rules embed (also useful after setting the channel for the first time)

All commands require the **Manage Server** permission.

## Settings (variables.py)

- `DEFAULT_CHANNEL_NAME` — fallback channel name when none is set via slash command, default `"rules"`
- `RULES_TITLE` — title shown at the top of the embed, default `"Server Rules"`
- `RULES_COLOR` — embed accent color (hex), default `0x5865F2` (blurple)

## Setup

### Prerequisites

- Python 3.10 or higher
- Discord bot token
- [auto-discord-server-deployment](https://github.com/beasty03/auto-discord-server-deployment) setup completed

### Steps

1. **Copy this folder into your cogs directory:**
   ```
   auto-discord-server-deployment/cogs/General/rules/
   ```

2. **Configure `variables.py`** — adjust the title, color, or default channel name if needed.

3. **Load the cog** in your bot launcher as `General.rules.rules`.

4. **Set your channel** with `/rules_channel #rules`.

5. **Add your rules** with `/rules_add <text>`, one per command.

6. **Post the embed** with `/rules_post`.

## How It Works

Rules are stored in the shared SQLite database. The bot keeps track of the message it posted — every time a rule is added, removed, or edited the bot edits that same message in place rather than posting a new one, so the channel stays clean. If the message is manually deleted, `/rules_post` will post a fresh one.
