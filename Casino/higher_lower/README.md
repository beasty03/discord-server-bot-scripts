# 🎴 Higher or Lower

A Discord casino game where players guess whether the next number will be higher or lower than the current one. Each correct guess stacks a multiplier — cash out at any time to lock in your winnings, or keep pushing your luck for bigger payouts.

## Features

- 🎴 **Higher / Lower gameplay** — guess the next number correctly to climb the multiplier ladder
- 💰 **Cash Out anytime** — lock in winnings after any correct guess
- 📈 **Stacking multipliers** — up to 12x on the final round
- ⏰ **Smart timeout** — auto cash-out if you have winnings, refund if you hadn't guessed yet
- 📊 **Statistics** — balance, games played, net profit/loss
- 🎁 **Daily Bonus** — claim daily rewards
- 🏅 **Leaderboard** — top players by balance

## Commands

| Command | Description |
|---|---|
| `/highlow <amount>` | Start a Higher or Lower game |
| `/hl_balance` | Check your balance and statistics |
| `/hl_daily` | Claim your daily bonus |
| `/hl_leaderboard` | View top players |

## How to Play

1. Use `/highlow <amount>` to place a bet.
2. A random number (1–10) is shown.
3. Press **⬆️ Higher** or **⬇️ Lower** to guess the next number.
4. Equal numbers count as a loss (house edge).
5. If correct — your multiplier increases and you can:
   - Keep guessing for a higher payout
   - Press **💰 Cash Out** to take your winnings
6. If wrong — you lose your original bet.

## Multiplier Table

| Correct Guesses | Multiplier | Payout on 100 bet |
|---|---|---|
| 1 | 1.8x | 180 |
| 2 | 3.0x | 300 |
| 3 | 5.0x | 500 |
| 4 | 8.0x | 800 |
| 5 | 12.0x | 1200 |

Multipliers are configurable in `variables.py`.

## Setup

### Prerequisites

- Python 3.10 or higher
- Discord bot token
- [auto-discord-server-deployment](https://github.com/beasty03/auto-discord-server-deployment) setup completed

### Steps

1. **Copy this folder into your cogs directory:**
   ```
   auto-discord-server-deployment/cogs/Casino/higher_lower/
   ```

2. **Configure `variables.py`** — adjust bet limits, multipliers, currency, and number range.

3. **Load the cog** in your bot launcher as `Casino.higher_lower.higher_lower`.

## Configuration (variables.py)

| Setting | Default | Description |
|---|---|---|
| `STARTING_BALANCE` | `1000` | Balance for new users |
| `MIN_BET` | `10` | Minimum bet |
| `MAX_BET` | `-1` | Maximum bet (-1 = no limit) |
| `NUMBER_RANGE` | `(1, 10)` | Min and max of drawn numbers |
| `ROUND_MULTIPLIERS` | `[1.8, 3.0, 5.0, 8.0, 12.0]` | Payout per correct round |
| `CURRENCY_NAME` | `"coins"` | Currency name |
| `CURRENCY_SYMBOL` | `"🪙"` | Currency emoji |
| `BUTTON_TIMEOUT` | `60` | Seconds before buttons expire |

## important: Install discord.py if missing
pip install discord.py
