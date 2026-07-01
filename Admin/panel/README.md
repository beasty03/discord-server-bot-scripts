# 🖥️ Admin Panel

Two admin tools in one cog: a cog status dashboard to see what's loaded, and a log control system to decide what gets posted to `#bot-logs` and `#mod-logs`.

## 📋 Features

### `/bot_status`
- Shows every known cog grouped by category (Casino, User, Tamagotchi, etc.)
- ✅ All loaded / ⚠️ Missing cogs listed by name
- Total loaded count in the description
- Ephemeral — only visible to the admin who ran it

### `/log settings` + `/log toggle`
- Toggle individual log categories on or off
- Changes persist across restarts (stored in `log_control_settings.json`)
- Other cogs check `is_log_enabled(category)` before posting

## 🚀 Installation

Load the cog as `Admin.panel.panel`.

No database tables required. Settings are stored in `Admin/panel/log_control_settings.json`.

## 🎮 Commands

All commands require **Administrator** permission.

| Command | Description |
|---------|-------------|
| `/bot_status` | View load status of all registered cogs |
| `/log settings` | Show current on/off state for every log category |
| `/log toggle <category>` | Enable or disable a specific log category |

## 📋 Log Categories

| Category | What it controls |
|----------|-----------------|
| `house_daily` | House daily income posts in `#bot-logs` |
| `fight_results` | Tamagotchi fight outcome summaries in `#bot-logs` |
| `api_warnings` | Missing Wordnik API key alerts in `#bot-logs` |
| `automod` | AutoMod violation logs posted to `#mod-logs` |
| `tamagotchi` | Pet adoption and death event logs in `#bot-logs` |

All categories default to **enabled** until explicitly toggled off.

## ⚙️ Adding log control to a new cog

```python
from Admin.panel.log_config import is_log_enabled

# Before posting to bot-logs:
if is_log_enabled("your_category"):
    await bot_logs.send(embed=embed)
```

Add the new category key + description to `Admin/panel/log_config.py → CATEGORIES` and `Admin/panel/variables.py → COG_GROUPS`.

## ⚙️ Adding a new cog to `/bot_status`

Open `Admin/panel/variables.py` and add the cog class name to the appropriate group in `COG_GROUPS`.

## Requirements

No extra database tables. Settings persist to `Admin/panel/log_control_settings.json`.
