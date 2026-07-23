# 🛡️ AutoMod

Automated message moderation with configurable filters. Detects bad words, spam, excessive caps, mass mentions, and unsafe links. Violations accumulate strikes and can auto-timeout offenders.

Commands: 15

## 📋 Features

- 🤬 **Bad word filter** — configurable word list, wildcards supported
- 📨 **Spam detection** — per-user message rate tracking (in-memory, resets on restart)
- 🔤 **Caps filter** — blocks messages above a configurable caps percentage
- 📣 **Mention filter** — blocks messages with too many @mentions at once
- 🔗 **Link filter** — blocks non-whitelisted URLs (Discord, Tenor, Giphy, YouTube etc. allowed by default)
- ⚠️ **Strike system** — strikes accumulate; reaching the threshold triggers an auto-timeout
- 📋 **Logging** — all actions posted to `#mod-logs`
- 🎭 **Role exemptions** — configurable roles that bypass all filters

## 🚀 Installation

Load the cog as `Admin.automod.automod`.

Settings are persisted to `Admin/automod/automod_settings.json`.

## 🎮 Commands

All commands require **Administrator** permission.

| Command | Description |
|---------|-------------|
| `/automod toggle <filter>` | Enable or disable a specific filter |
| `/automod settings` | View current automod configuration |
| `/automod add_bad_word <word>` | Add a word to the blocklist |
| `/automod remove_bad_word <word>` | Remove a word from the blocklist |
| `/automod list_bad_words` | List all blocked words |
| `/automod set_spam_limit <count> <seconds>` | Configure spam threshold |
| `/automod set_caps_threshold <percent>` | Set max allowed caps percentage |
| `/automod set_max_mentions <count>` | Set max mentions per message |
| `/automod add_link_whitelist <domain>` | Whitelist a domain |
| `/automod remove_link_whitelist <domain>` | Remove a domain from whitelist |
| `/automod list_link_whitelist` | List whitelisted domains |
| `/automod set_strike_threshold <count>` | Set strikes before auto-timeout |
| `/automod set_exempt_role <role>` | Set a role that bypasses all filters |

## ⚙️ How it works

1. Every non-bot message is checked against all enabled filters.
2. A violation deletes the message, warns the user in-channel (auto-deletes after 8s), and increments their strike count.
3. If strikes reach the threshold, the user is timed out for a configurable duration.
4. Admins and exempt-role members are never filtered.
5. All mod actions are logged to `#mod-logs`.

## ⚙️ Default configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_SPAM_LIMIT` | `5` | Messages per window before spam flag |
| `DEFAULT_SPAM_WINDOW` | `5` | Window size in seconds |
| `DEFAULT_CAPS_THRESHOLD` | `70` | Max caps percentage |
| `DEFAULT_MAX_MENTIONS` | `5` | Max @mentions per message |
| `DEFAULT_STRIKE_THRESHOLD` | `3` | Strikes before auto-timeout |
| `DEFAULT_TIMEOUT_MINUTES` | `10` | Timeout duration in minutes |

## Requirements

No extra database tables — settings are stored in `automod_settings.json`.
