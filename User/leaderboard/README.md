# User/leaderboard — Leaderboard Cog

Shows server-wide coin rankings.

## Commands

| Command | Description |
|---------|-------------|
| `/bal_top` | Top N richest players, with game count. |

## Variables (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `CURRENCY_NAME` | `"coins"` | Displayed currency name |
| `CURRENCY_SYMBOL` | `"🪙"` | Emoji shown next to amounts |
| `LEADERBOARD_TOP_COUNT` | `10` | How many players to show |
| `COLOR_INFO` | `0x5865F2` | Embed color |

## Setup

1. Load the cog from your bot launcher (`User/leaderboard/leaderboard.py`).
2. Ensure `ForgeDB` is initialised — the command reads the `users` and `casino_stats` tables.

## Dependencies

- `forge_db.ForgeDB` — `execute` for the leaderboard query.
- Tables: `users` (balance), `casino_stats` (games_played) via `LEFT JOIN`.
