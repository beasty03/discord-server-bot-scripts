# ✂️ Rock Paper Scissors

Classic Rock Paper Scissors with betting. Play against the bot for an instant result, or challenge another server member to a simultaneous PvP match where both picks are hidden until revealed.

## Commands

| Command | Description |
|---------|-------------|
| `/rps <amount>` | Play against the bot — pick your move via buttons |
| `/rps <amount> <@user>` | Challenge another user to a PvP match |

## Game flow

### vs Bot
1. Run `/rps <amount>` — a private (ephemeral) button picker appears.
2. Pick ✊ Rock, 📄 Paper, or ✂️ Scissors.
3. Bot picks randomly. Result is shown privately + public announcement.
   - **Win** → profit = your bet (1:1)
   - **Loss** → lose your bet
   - **Tie** → bet refunded

### vs User (PvP)
1. Challenger runs `/rps <amount> <@user>`.  
   Their bet is deducted immediately and held.
2. The challenged user has **30 seconds** to click **Accept** or **Decline**.
   - **Decline / no response** → challenger's bet is refunded.
   - **Accept** → challengee's bet is deducted. Both players see ✊/📄/✂️ buttons in the public message.
3. Each player clicks their move — they receive a private confirmation only they can see.  
   The public message shows ✅ Ready / ⏳ Picking status without revealing choices.
4. Once both have picked (or 30 seconds pass), picks are revealed simultaneously.
   - **Winner takes both bets** (net +`amount`).
   - **Tie** → both bets refunded.
   - **Timeout** → both bets refunded regardless of who picked.

No house cut on PvP games — it is pure player-vs-player.

## Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_BET` | `10` | Minimum bet |
| `MAX_BET` | `-1` | Maximum bet (`-1` = no limit) |
| `CHALLENGE_TIMEOUT` | `30` | Seconds to accept a PvP challenge |
| `PICK_TIMEOUT` | `30` | Seconds for both players to pick a move |
