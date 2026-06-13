# Casino/bank — Bank Cog

Centralised currency management for the entire bot. This is the **only** place that provides `/balance`, `/bal`, `/daily`, `/top`, and `/give` — all other casino cogs have had these removed.

## Commands

| Command | Description |
|---------|-------------|
| `/balance [member]` | Full stats card — balance, games played, total won/lost, net P/L. Optionally look up another member. |
| `/bal [member]` | Quick one-line balance check. |
| `/daily` | Claim the daily coin bonus. Shows time remaining when on cooldown. |
| `/top` | Leaderboard — top N players sorted by balance, with game count. |
| `/give @member amount` | Transfer coins from your account to another player. |

## Variables (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `CURRENCY_NAME` | `"coins"` | Displayed currency name |
| `CURRENCY_SYMBOL` | `"🪙"` | Emoji shown next to amounts |
| `GIVE_MIN` | `1` | Minimum amount per `/give` |
| `GIVE_MAX` | `0` | Maximum amount per `/give` (`0` = no limit) |
| `LEADERBOARD_TOP_COUNT` | `10` | How many players `/top` displays |
| `COLOR_INFO` | `0x5865F2` | Blurple — neutral embeds |
| `COLOR_WIN` | `0x57F287` | Green — success embeds |
| `COLOR_ERROR` | `0xED4245` | Red — error embeds |

## Setup

1. Add the cog to your bot loader:
   ```
   Casino/bank/bank.py
   ```
2. Ensure `ForgeDB` is initialised before this cog loads — it relies on the `users` and `casino_stats` tables created by `ForgeDB`.
3. Adjust `variables.py` as needed (currency name, give limits, leaderboard size).

## Dependencies

- `forge_db.ForgeDB` — uses `ensure_user`, `get_balance`, `update_balance`, `claim_daily`, and raw `execute` for stats queries.
- Tables: `users` (balance), `casino_stats` (games_played, total_won, total_lost).
