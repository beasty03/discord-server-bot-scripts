
# 🎲 Gamble Bot
 
A Discord bot that allows users to gamble virtual currency with customizable settings and statistics tracking.
 
## 📋 Features
 
- 🎰 **Gambling System** - Bet virtual currency for a chance to win
- 💰 **Balance Tracking** - Automatic user account creation with starting balance
- 📊 **Statistics** - Track total wins, losses, and games played
- 🎁 **Daily Bonus** - Claim daily rewards (optional)
- 🏆 **Leaderboard** - See top players by balance
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
   git clone <gamble-bot-repo-url> gamble
- WIN_MULTIPLIER = 5.0
- WIN_CHANCE = 20
- WIN_MULTIPLIER = 1.5
- WIN_CHANCE = 60
- STARTING_BALANCE = 5000
- CURRENCY_NAME = "gold"
- CURRENCY_SYMBOL = "💰"
- /gamble 100

- COLOR_WIN = 0x00FF00      # Green
- COLOR_LOSE = 0xFF0000     # Red
- COLOR_ERROR = 0xFFA500    # Orange
- COLOR_INFO = 0x00BFFF     # Light Blue
- MESSAGE_WIN = "🎉 You won {amount} {currency}!"
- MESSAGE_LOSE = "💸 You lost {amount} {currency}!"
- MESSAGE_INSUFFICIENT_FUNDS = "You don't have enough {currency}!"

## important: Install discord.py if missing
pip install discord.py
 
# Ensure utils folder exists with config_loader.py
gamble/
├── bot.py              # Main bot script
├── variables.py        # Configuration file
├── gamble.db          # SQLite database (auto-created)
└── README.md          # This file