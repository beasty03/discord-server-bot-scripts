# 🎯 Hangman

A classic word-guessing game. The bot picks a hidden word and you guess letters one at a time — guess too many wrong and the man gets hanged. Bet coins to play; a correct guess pays out 2×.

## 📋 Features

- 🔤 **Letter-by-letter guessing** — click the button and type a letter in the popup
- 🖼️ **Live ASCII hangman** — the drawing updates after every wrong guess (up to 6)
- 🟩🟥 **Colour-coded history** — shows correct and wrong letters at a glance
- 💀 **6 strikes = game over** — the word is revealed and you lose your bet
- 🏳️ **Give up button** — reveal the answer and cut your losses at any time
- ⏰ **Auto-timeout** — game ends after 3 minutes of inactivity

## 🚀 Installation

Load the cog as `Minigames.hangman.hangman`.

## 🎮 Commands

| Command | Description |
|---------|-------------|
| `/hangman <amount>` | Start a Hangman game with the given bet |

## ⚙️ How it works

1. Use `/hangman <amount>` to start — your bet is deducted immediately.
2. An ephemeral embed shows the hangman scaffold and the word as blanks (`_ _ _ _ _`).
3. Click **🔤 Guess a letter** — a popup appears where you type one letter.
4. Correct letters are revealed in the word; wrong ones add a body part to the drawing.
5. **Win** (guess all letters before 6 wrong): receive **2×** your bet back.
6. **Lose** (6 wrong guesses, give up, or timeout): lose your bet.

## ⚙️ Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_BET` | `10` | Minimum bet |
| `MAX_BET` | `-1` | Maximum bet (`-1` = no limit) |
| `MAX_WRONG` | `6` | Wrong guesses allowed before losing |
| `WIN_MULTIPLIER` | `2.0` | Payout multiplier on a win (includes stake) |
| `BUTTON_TIMEOUT` | `180` | Seconds before the game auto-closes |
| `WORDS` | *(list)* | Word pool the bot picks from |

## Requirements

No extra database tables — uses the existing `casino_stats` table for win/loss tracking.
