# Self Roles

Posts a persistent panel in a channel with buttons for each self-assignable role. Users click a button to add or remove that role from themselves. Admins manage the list via slash commands — the panel updates in place every time a role is added or removed.

Commands: 4

## Commands

- `/selfroles_channel #channel` — set the channel where the panel is posted
- `/selfroles_add @role [label]` — add a role to the panel (optional custom button label)
- `/selfroles_remove @role` — remove a role from the panel
- `/selfroles_post` — post or refresh the panel (also used after setting the channel for the first time)

`/selfroles_add` and `/selfroles_remove` require **Manage Roles**.
`/selfroles_channel` and `/selfroles_post` require **Manage Server**.

## Settings (variables.py)

- `DEFAULT_CHANNEL_NAME` — fallback channel name when none is set via slash command, default `"roles"`
- `PANEL_TITLE` — title shown at the top of the embed, default `"Self-Assignable Roles"`
- `PANEL_DESCRIPTION` — instructions shown below the title, default `"Click a button below to add or remove a role from yourself."`
- `PANEL_COLOR` — embed accent color (hex), default `0x5865F2` (blurple)

## Setup

### Prerequisites

- Python 3.10 or higher
- Discord bot token
- [auto-discord-server-deployment](https://github.com/beasty03/auto-discord-server-deployment) setup completed
- Bot must have the **Manage Roles** permission and its role must sit **above** any role it assigns

### Steps

1. **Copy this folder into your cogs directory:**
   ```
   auto-discord-server-deployment/cogs/General/self_roles/
   ```

2. **Configure `variables.py`** — adjust the panel title, description, or default channel if needed.

3. **Load the cog** in your bot launcher as `General.self_roles.self_roles`.

4. **Set your channel** with `/selfroles_channel #roles`.

5. **Add roles** with `/selfroles_add @RoleName` — repeat for each role.

6. **Post the panel** with `/selfroles_post`.

## How It Works

Each role gets its own button with a persistent `custom_id` (`selfrole_{role_id}`). Clicking a button toggles the role — if the user already has it, it's removed; otherwise it's added. The panel message is edited in place whenever the role list changes, so the channel stays clean. On bot restart, the buttons are re-registered automatically so they keep working without re-posting.

> **Note:** Discord limits a single message to 25 buttons. The panel will refuse to add more than 25 roles.
