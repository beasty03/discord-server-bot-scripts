# ❌ Tic-Tac-Toe

Play Tic-Tac-Toe against the bot on a 3×3 button grid. Bet coins — win to double your bet, lose to forfeit it.

Commands: 1

## 📋 Features

- 🎮 **Button-based 3×3 grid** — click any open cell to place your mark
- 🤖 **Minimax AI** — the bot plays optimally but occasionally makes deliberate mistakes to keep games winnable
- 🔴🔵 **Colour-coded cells** — player is 🔴, bot is 🔵
- 🏆 **Win detection** — winning line buttons turn green
- 🏳️ **Give Up button** — forfeit early at any time
- ⏰ **Auto-timeout** — game ends after 2 minutes of inactivity

## 🚀 Installation

Load the cog as `Minigames.tictactoe.tictactoe`.

## 🎮 Commands

| Command | Description |
|---------|-------------|
| `/tictactoe <amount>` | Start a Tic-Tac-Toe game with the given bet |

## ⚙️ How it works

1. Use `/tictactoe <amount>` — your bet is deducted immediately.
2. An ephemeral 3×3 button grid appears; you go first as 🔴.
3. Click any open cell to place your mark. The bot responds as 🔵.
4. **Win**: receive **2×** your bet back.
5. **Lose / Draw / Give Up / Timeout**: lose your bet.

## ⚙️ Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_MISTAKE_CHANCE` | `0.20` | Probability the bot makes a random (non-optimal) move |
| `WIN_MULTIPLIER` | `2.0` | Payout multiplier on a win (includes stake) |
| `BUTTON_TIMEOUT` | `120` | Seconds before the game auto-closes |
| `PLAYER_EMOJI` | `🔴` | Emoji for the player's mark |
| `BOT_EMOJI` | `🔵` | Emoji for the bot's mark |

## Requirements

No extra database tables — uses the existing `casino_stats` table for win/loss tracking.
