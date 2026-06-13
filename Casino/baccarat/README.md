# 🃏 Baccarat

A Discord bot that lets users play Baccarat using virtual currency. Bet on Player, Banker, or Tie — cards are dealt automatically following official baccarat rules and the result is shown immediately.

## Features

- 🃏 **Full baccarat rules** — official third-card drawing rules for both Player and Banker
- 🎯 **Three bet types** — Player (1:1), Banker (0.95:1), Tie (8:1)
- ↩️ **Tie push** — Player and Banker bets are refunded on a tie (configurable)
- 💰 **Shared balance** — uses the same casino economy as Blackjack, Roulette, and Higher or Lower
- 📊 **Statistics** — balance, games played, net profit/loss
- 🎁 **Daily Bonus** — claim daily rewards
- 🏅 **Leaderboard** — top players by balance

## Commands

| Command | Description |
|---|---|
| `/baccarat <amount>` | Start a Baccarat round |
| `/bac_balance` | Check your balance and statistics |
| `/bac_daily` | Claim your daily bonus |
| `/bac_leaderboard` | View top players |

## How to Play

1. Use `/baccarat <amount>` to place a wager.
2. Three buttons appear — pick your bet:
   - **👤 Player** — you think the Player hand wins
   - **🏦 Banker** — you think the Banker hand wins
   - **🤝 Tie** — you think both hands are equal
3. Cards are dealt automatically following standard baccarat rules.
4. The hand closest to **9** wins.

## Payout Table

| Bet | Pays | Notes |
|---|---|---|
| 👤 Player | 1:1 | No commission |
| 🏦 Banker | 0.95:1 | 5% house commission |
| 🤝 Tie | 8:1 | Player/Banker bets pushed on tie |

## Card Values

| Card | Value |
|---|---|
| 2–9 | Face value |
| 10, J, Q, K | 0 |
| A | 1 |

Hand total = sum of cards **mod 10** (only the last digit counts). A hand of `7 + 8 = 15` counts as **5**.

## Third-Card Rules (automatic)

**Natural (8 or 9 on first two cards):** no more cards drawn for either hand.

**Player draws if:** total is 0–5. Stands on 6–7.

**Banker draws based on Player's third card:**

| Banker Total | Draws if Player's 3rd card is |
|---|---|
| 0–2 | Always draws |
| 3 | Any except 8 |
| 4 | 2–7 |
| 5 | 4–7 |
| 6 | 6–7 |
| 7 | Never (stands) |

## Setup

### Prerequisites

- Python 3.10 or higher
- Discord bot token
- [auto-discord-server-deployment](https://github.com/beasty03/auto-discord-server-deployment) setup completed

### Steps

1. **Copy this folder into your cogs directory:**
   ```
   auto-discord-server-deployment/cogs/Casino/baccarat/
   ```

2. **Configure `variables.py`** — adjust bet limits, payouts, and commission if needed.

3. **Load the cog** in your bot launcher as `Casino.baccarat.baccarat`.

## Configuration (variables.py)

| Setting | Default | Description |
|---|---|---|
| `STARTING_BALANCE` | `1000` | Balance for new users |
| `MIN_BET` | `10` | Minimum bet |
| `MAX_BET` | `-1` | Maximum bet (-1 = no limit) |
| `PLAYER_MULTIPLIER` | `2.0` | Payout on Player win |
| `BANKER_MULTIPLIER` | `1.95` | Payout on Banker win (after 5% commission) |
| `TIE_MULTIPLIER` | `9.0` | Payout on Tie win |
| `TIE_PUSHES_SIDE_BETS` | `True` | Refund Player/Banker bets on a tie |
| `BUTTON_TIMEOUT` | `60` | Seconds before bet buttons expire |

## important: Install discord.py if missing
pip install discord.py
