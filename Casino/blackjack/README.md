
# 🃏 Blackjack Bot

A Discord bot that lets users play Blackjack against the dealer using virtual currency, with interactive Hit/Stand buttons.

## 📋 Features

- 🃏 **Blackjack Game** - Full Hit/Stand gameplay against an automated dealer
- 💰 **Balance Tracking** - Automatic user account creation with starting balance
- 🏆 **Natural Blackjack** - 2.5× payout for 21 on first two cards
- 🤝 **Push (Tie)** - Bet is refunded on a draw
- 📊 **Statistics** - Track total wins, losses, and games played
- 🎁 **Daily Bonus** - Claim daily rewards (optional)
- 🏅 **Leaderboard** - See top players by balance
- ⚙️ **Fully Customizable** - Easy configuration through `variables.py`
- 🗄️ **SQLite Database** - Persistent data storage

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- Discord bot token (see setup guide below)
- [auto-discord-server-deployment](https://github.com/beasty03/auto-discord-server-deployment) setup completed

### Setup Steps

1. **Clone this folder into your cogs directory:**
   ```bash
   cd auto-discord-server-deployment/cogs
   git clone <blackjack-bot-repo-url> blackjack
   ```

2. **Configure `variables.py`** to match your server settings.

3. **Load the cog** in your bot launcher as `Casino.blackjack.blackjack`.

## 🎮 Commands

| Command | Description |
|---|---|
| `/blackjack <amount>` | Start a blackjack game with your bet |
| `/bj_balance` | Check your balance and statistics |
| `/bj_daily` | Claim your daily bonus |
| `/bj_leaderboard` | View top 10 players |

## 🎲 How to Play

1. Use `/blackjack <amount>` to place your bet.
2. You and the dealer are each dealt **2 cards**. One dealer card is hidden.
3. Press **Hit** to draw another card, or **Stand** to end your turn.
4. The dealer reveals their hidden card and draws until reaching **17 or higher**.
5. Closest to **21 without going over** wins!

### Payout Table

| Outcome | Payout |
|---|---|
| Natural Blackjack (21 on first 2 cards) | 2.5× bet |
| Regular Win | 2× bet |
| Push (Tie) | Bet returned |
| Bust / Lose | Bet lost |

## ⚙️ Configuration Examples

**High-risk settings:**
- `MIN_BET = 100`
- `MAX_BET = 10000`

**Custom currency:**
- `CURRENCY_NAME = "gold"`
- `CURRENCY_SYMBOL = "💰"`

**Custom colors:**
- `COLOR_WIN = 0x00FF00`    # Green
- `COLOR_LOSE = 0xFF0000`   # Red
- `COLOR_PUSH = 0xFFFF00`   # Yellow
- `COLOR_PLAYING = 0x9B59B6` # Purple

## important: Install discord.py if missing
pip install discord.py
