# 🎲 Craps

A classic casino dice game. Roll two dice and bet on the pass line — win fast on a natural or fight to make your point.

Commands: 1

## How to play

1. Use `/craps <amount>` to place a pass line bet.
2. Press **🎲 Roll Come-Out** to throw the dice.

### Come-out roll

| Result | Outcome |
|--------|---------|
| **7 or 11** | **Natural** — instant win (1:1 payout) |
| **2, 3, or 12** | **Craps** — instant loss |
| **4, 5, 6, 8, 9, or 10** | **Point** is set — keep rolling |

### Point phase

Once a point is set, keep pressing **🎲 Roll Again** until:
- You roll the **point number** again → **Win** (1:1 payout)
- You roll a **7** → **Seven out** (lose)

Pass line has a ~1.41% house edge — one of the fairest bets in any casino.

## Commands

| Command | Description |
|---------|-------------|
| `/craps <amount>` | Place a pass line bet and start rolling |

## Setup

Load the cog as `Casino.craps.craps`.

## Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_BET` | `10` | Minimum bet |
| `MAX_BET` | `-1` | Maximum bet (-1 = no limit) |
| `BUTTON_TIMEOUT` | `120` | Seconds before the game times out and refunds the bet |

On timeout: bet is refunded.
