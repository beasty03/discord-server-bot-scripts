# 🟩 Wordle

Bet coins and guess the hidden 5-letter word in 6 tries. Each guess reveals which letters are correct (🟩), in the word but wrong spot (🟨), or not in the word at all (⬛). Guess it in fewer attempts to earn a higher payout.

Commands: 2

## 📋 Features

- 🟩🟨⬛ **Classic colour feedback** — updated live after every guess
- 📝 **Modal input** — click the button and type your guess in a popup
- 💰 **Tiered payouts** — fewer attempts = bigger multiplier (up to 6×)
- 🌐 **Wordnik API** — fresh real words every game (falls back to built-in list if API is down)
- 🏳️ **Give up button** — reveal the word and end early at any time
- ⏰ **Auto-timeout** — game closes after 5 minutes of inactivity

## 🚀 Installation

Load the cog as `Minigames.wordle.wordle`.

Add your Wordnik API key to `config.json` (shared with Hangman):
```json
"wordnik_api_key": "YOUR_KEY_HERE"
```

## 🎮 Commands

| Command | Description |
|---------|-------------|
| `/wordle <amount>` | Start a Wordle game with the given bet |

## ⚙️ How it works

1. Use `/wordle <amount>` — your bet is deducted and a 5-letter word is chosen.
2. Click **📝 Make a guess** → type a 5-letter word in the popup.
3. The board updates showing colour feedback for each letter.
4. **Win** (guess correctly within 6 tries): earn a payout based on attempts used.
5. **Lose** (6 wrong guesses, give up, or timeout): lose your bet.

## 💰 Payout table

| Solved on attempt | Multiplier |
|---|---|
| 1st | 6× |
| 2nd | 4× |
| 3rd | 3× |
| 4th | 2.5× |
| 5th | 1.5× |
| 6th | 1.2× |

## ⚙️ Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_BET` / `MAX_BET` | `10` / `-1` | Bet limits (`-1` = no max) |
| `WORD_LENGTH` | `5` | Letters in the target word |
| `MAX_ATTEMPTS` | `6` | Guesses allowed before losing |
| `WIN_MULTIPLIERS` | `[6.0, 4.0, 3.0, 2.5, 1.5, 1.2]` | Payout per attempt (index 0 = 1st guess) |
| `BUTTON_TIMEOUT` | `300` | Seconds before game auto-closes |
| `WORDNIK_MIN_CORPUS` | `100000` | Minimum corpus frequency — higher = more familiar words |
| `WORDNIK_PART_OF_SPEECH` | `noun` | Word type filter |

## Requirements

No extra database tables — uses the existing `casino_stats` table.
