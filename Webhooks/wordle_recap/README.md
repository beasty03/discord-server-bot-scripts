# Wordle Recap

Posts yesterday's Wordle answer every day at a configurable time (default **00:05 UTC**) in a channel of your choice (default **#general**). The answer is fetched from the official NYT Wordle API.

Commands: 5

## Commands

- `/set_wordle_channel #channel` — set the channel where the recap is posted
- `/set_wordle_time <hour> <minute>` — set the time of the daily post in your configured timezone
- `/set_wordle_timezone <timezone>` — set the timezone for the post time (e.g. `Europe/Brussels`)
- `/wordle_recap` — manually post yesterday's answer right now (useful for testing)

All commands require the **Manage Server** permission.

## Settings (variables.py)

- `WORDLE_POST_HOUR` — hour of the daily post (in `WORDLE_TIMEZONE`), default `0`
- `WORDLE_POST_MINUTE` — minute of the daily post, default `5`
- `WORDLE_TIMEZONE` — fallback IANA timezone when none is set via slash command, default `"UTC"`
- `DEFAULT_CHANNEL_NAME` — fallback channel name when none is set via slash command, default `"general"`

## Setup

### Prerequisites

- Python 3.10 or higher
- Discord bot token
- [auto-discord-server-deployment](https://github.com/beasty03/auto-discord-server-deployment) setup completed
- `aiohttp` installed (`pip install aiohttp`)

### Steps

1. **Copy this folder into your cogs directory:**
   ```
   auto-discord-server-deployment/cogs/Webhooks/wordle_recap/
   ```

2. **Configure `variables.py`** — adjust the default post time or channel name if needed.

3. **Load the cog** in your bot launcher as `Webhooks.wordle_recap.wordle_recap`.

4. **Set your channel** with `/set_wordle_channel #your-channel` after the bot is running. Without this, it falls back to the first channel named `general`.

5. **(Optional)** Change the post time with `/set_wordle_time 0 5` (00:05 UTC is the default).

## How It Works

A background task runs every minute and checks whether the current UTC time matches the configured post time. When it fires it fetches yesterday's answer from:

```
https://www.nytimes.com/svc/wordle/v2/YYYY-MM-DD.json
```

The answer and Wordle number are then posted as a Discord embed. Settings (channel ID, post hour/minute) are persisted in the shared SQLite database under the `wordle_config` table, so they survive bot restarts.
