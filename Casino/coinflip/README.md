# 🪙 Coin Flip

A heads-or-tails betting game. Play against the bot for a quick 50/50, or challenge another server member to a PvP flip where the winner takes both bets.

Commands: 1

## Commands

| Command | Description |
|---------|-------------|
| `/coinflip <amount>` | Flip against the bot (48% win chance, 2× payout) |
| `/coinflip <amount> <@user>` | Challenge another user — winner takes both bets |

## Game flow

### vs Bot
1. Run `/coinflip <amount>` — result is instant.
2. You win 48% of the time; profit = your bet (1:1).
3. Tie is not possible — every flip produces a winner.

### vs User (PvP)
1. Challenger runs `/coinflip <amount> <@user>`.  
   Their bet is deducted immediately and held.
2. The challenged user has **30 seconds** to click **Accept** or **Decline**.
   - **Decline / no response** → challenger's bet is refunded.
   - **Accept** → challengee's bet is deducted, coin flips automatically.
3. Winner receives both bets (net +`amount`). Result is posted publicly.

No house cut on PvP games — it is pure player-vs-player.

## Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_BET` | `10` | Minimum bet |
| `MAX_BET` | `-1` | Maximum bet (`-1` = no limit) |
| `WIN_CHANCE` | `48` | % win chance vs bot |
| `WIN_MULTIPLIER` | `2.0` | Payout multiplier vs bot |
| `CHALLENGE_TIMEOUT` | `30` | Seconds to accept a PvP challenge |
