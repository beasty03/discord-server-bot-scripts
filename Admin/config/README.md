# General/config — Config Cog

Manages global channel and role restrictions for all bot commands. Registers a single `bot.tree.add_check()` that runs before every slash command — no other cog needs to be modified.

Commands: 6

## Rules

| Command type | Where it works | Who can use it |
|---|---|---|
| `/help` | Anywhere | Everyone |
| `set_*`, `add_allowed_channel`, `remove_allowed_channel`, `view_config`, `startevent` | Control panel channel only | Staff roles (Admin / Moderator) |
| Everything else | Allowed channels only | Everyone |

> **Bootstrap safety:** If no control-panel channel is configured yet (and none named `control-panel` exists), admin commands skip the channel check and only enforce the staff role — so you can run `/set_control_panel` on first boot without being locked out.

## Commands

| Command | Description |
|---------|-------------|
| `/add_allowed_channel #channel` | Add a channel to the allowed list (call multiple times for multiple channels) |
| `/remove_allowed_channel #channel` | Remove a channel from the allowed list |
| `/set_control_panel #channel` | Set the channel where admin/set commands must be run |
| `/set_staff_roles @role …` | Set up to 4 roles that count as staff |
| `/view_config` | Show current allowed channels, control panel, and staff roles |

All commands above are themselves admin commands — they require the staff role and the control-panel channel.

## Variables (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_ALLOWED_CHANNEL_NAMES` | `["general"]` | Fallback channel names before any channels are configured |
| `DEFAULT_CONTROL_PANEL_NAME` | `"control-panel"` | Fallback control panel channel name |
| `DEFAULT_STAFF_ROLE_NAMES` | `["Admin", "Administrator", "Moderator", "Mod"]` | Fallback staff role names |

> Users with Discord's built-in **Administrator** permission are always treated as staff regardless of role names.

## Persistence

Settings are stored in `General/config/bot_settings.json` (created automatically on first use):

```json
{
  "allowed_channels":  [{ "id": 123456, "name": "general" }],
  "control_panel":     { "id": 789012, "name": "control-panel" },
  "staff_role_names":  ["Admin", "Moderator"]
}
```

## Setup

1. Load `General/config/config.py` in your bot launcher — it must load **before** any other cog so the global check is registered first.
2. Run `/set_control_panel #your-admin-channel` from any channel (bootstrap mode).
3. Run `/add_allowed_channel #general` (and any other channels) from the control panel.
4. Run `/set_staff_roles @Admin @Moderator` to lock down who can use admin commands.
