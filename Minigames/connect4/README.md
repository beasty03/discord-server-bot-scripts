# 🔴 Connect 4

Drop coloured discs into a 7-column, 6-row grid and try to connect four in a row before the bot does. Bet coins — win to double your bet, lose to forfeit it.

Commands: 1

## 📋 Features

- 🎮 **Button-based column selection** — 7 column buttons drop your disc into that column
- 🤖 **Heuristic AI** — win → block → positional scoring (center preference + window evaluation)
- 🔴🟡 **Colour-coded discs** — player is 🔴, bot is 🟡, empty is ⚫
- 📊 **Live board render** — the board updates as an emoji grid after every move
- 🏳️ **Give Up button** — forfeit early at any time
- ⏰ **Auto-timeout** — game ends after 2 minutes of inactivity

## 🚀 Installation

Load the cog as `Minigames.connect4.connect4`.

## 🎮 Commands

| Command | Description |
|---------|-------------|
| `/connect4 <amount>` | Start a Connect 4 game with the given bet |

## ⚙️ How it works

1. Use `/connect4 <amount>` — your bet is deducted immediately.
2. A 6×7 emoji board appears with 7 column buttons (split across two button rows) and a Give Up button.
3. Click a column to drop your 🔴 disc. The bot responds with 🟡.
4. First to connect four horizontally, vertically, or diagonally wins.
5. **Win**: receive **2×** your bet back.
6. **Lose / Full board / Give Up / Timeout**: lose your bet.

## ⚙️ Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `ROWS` | `6` | Number of board rows |
| `COLS` | `7` | Number of board columns |
| `WIN_MULTIPLIER` | `2.0` | Payout multiplier on a win (includes stake) |
| `BUTTON_TIMEOUT` | `120` | Seconds before the game auto-closes |
| `PLAYER_EMOJI` | `🔴` | Player disc emoji |
| `BOT_EMOJI` | `🟡` | Bot disc emoji |
| `EMPTY_EMOJI` | `⚫` | Empty cell emoji |

## Requirements

No extra database tables — uses the existing `casino_stats` table for win/loss tracking.
