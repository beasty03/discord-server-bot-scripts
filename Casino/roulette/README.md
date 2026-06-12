# 🎡 Roulette Bot

A Discord bot that lets users play European Roulette (0–36) using virtual currency, with interactive bet-type buttons and a straight-up number modal.

## Features

- 🎡 **European Roulette** — numbers 0–36, nine bet types
- 💰 **Shared Balance** — uses the same casino economy as Blackjack
- 🎯 **All standard bets** — Red/Black, Odd/Even, Low/High, Dozens, Straight Up
- ⏰ **Timeout refund** — bet is returned if no choice is made in time
- 📊 **Statistics** — balance, games played, net profit/loss
- 🎁 **Daily Bonus** — claim daily rewards
- 🏅 **Leaderboard** — top players by balance
- ⚙️ **Fully Customizable** — easy configuration via `variables.py`

## Commands

| Command | Description |
|---|---|
| `/roulette <amount>` | Spin the wheel |
| `/rl_balance` | Check your balance and statistics |
| `/rl_daily` | Claim your daily bonus |
| `/rl_leaderboard` | View top 10 players |

## Bet Types & Payouts

| Bet | Covers | Pays |
|---|---|---|
| 🔴 Red / ⚫ Black | 18 numbers | 1:1 |
| Odd / Even | 18 numbers | 1:1 |
| Low (1–18) / High (19–36) | 18 numbers | 1:1 |
| 1st Dozen (1–12) | 12 numbers | 2:1 |
| 2nd Dozen (13–24) | 12 numbers | 2:1 |
| 3rd Dozen (25–36) | 12 numbers | 2:1 |
| 🎯 Straight Up (0–36) | 1 number | 35:1 |

> **Note:** Landing on 0 (green) loses all even-chance bets (Red/Black, Odd/Even, Low/High).

## How to Play

1. Use `/roulette <amount>` to place a wager.
2. Nine bet-type buttons appear — click one.
3. For **Straight Up**, a popup asks you to type a number (0–36).
4. The wheel spins instantly and the result is shown.
5. You have **60 seconds** to choose — if you don't, your bet is refunded.

## Setup

### Prerequisites

- Python 3.10 or higher
- Discord bot token
- [auto-discord-server-deployment](https://github.com/beasty03/auto-discord-server-deployment) setup completed

### Steps

1. **Copy this folder into your cogs directory:**
   ```
   auto-discord-server-deployment/cogs/Casino/roulette/
   ```

2. **Configure `variables.py`** — adjust bet limits, currency, colors, and messages.

3. **Load the cog** in your bot launcher as `Casino.roulette.roulette`.

## Configuration (variables.py)

| Setting | Default | Description |
|---|---|---|
| `STARTING_BALANCE` | `1000` | Balance for new users |
| `MIN_BET` | `10` | Minimum bet |
| `MAX_BET` | `5000` | Maximum bet (0 = no limit) |
| `CURRENCY_NAME` | `"coins"` | Currency name |
| `CURRENCY_SYMBOL` | `"🪙"` | Currency emoji |
| `DAILY_BONUS_AMOUNT` | `500` | Daily bonus payout |
| `BUTTON_TIMEOUT` | `60` | Seconds before bet buttons expire |

## important: Install discord.py if missing
pip install discord.py
