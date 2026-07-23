# 🎲 Under/Over

Roll two dice and bet on whether the sum will be under 7, exactly 7, or over 7.

Commands: 1

## How to play

1. Use `/underover <amount>` to place your bet.
2. Three buttons appear — pick your bet type.
3. Two dice are rolled instantly.
4. Win or lose based on the result.

## Commands

| Command | Description |
|---------|-------------|
| `/underover <amount>` | Place an Under/Over bet |

## Bets & payouts

| Bet | Wins when | Probability | Payout (total return) |
|-----|-----------|-------------|----------------------|
| 🔽 Under 7  | Sum is 2 – 6  | 15/36 ≈ 41.7% | **2.2×** |
| 7️⃣ Exactly 7 | Sum is exactly 7 | 6/36 ≈ 16.7% | **5.5×** |
| 🔼 Over 7   | Sum is 8 – 12 | 15/36 ≈ 41.7% | **2.2×** |

House edge: ~8.3% on all bet types.

## Setup

Load the cog as `Casino.underover.underover`.

## Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_BET` | `10` | Minimum bet |
| `MAX_BET` | `-1` | Maximum bet (-1 = no limit) |
| `PAYOUT_UNDER` | `2.2` | Total-return multiplier for Under 7 |
| `PAYOUT_EXACT` | `5.5` | Total-return multiplier for Exactly 7 |
| `PAYOUT_OVER` | `2.2` | Total-return multiplier for Over 7 |
| `BUTTON_TIMEOUT` | `60` | Seconds before bet is refunded |

On timeout: bet is refunded.
