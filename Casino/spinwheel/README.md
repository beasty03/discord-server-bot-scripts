# 🎡 Spin the Wheel

Spin a prize wheel and see what multiplier you land on. Instant result, no buttons needed.

## How to play

1. Use `/spinwheel <amount>` to spin.
2. The wheel lands on one of the segments.
3. Your payout = bet × multiplier.
4. 💀 Bust = you lose your bet.

## Commands

| Command | Description |
|---------|-------------|
| `/spinwheel <amount>` | Spin the prize wheel |

## Wheel segments

| Segment | Multiplier | Weight |
|---------|-----------|--------|
| 💀 Bust  | 0×  | 6 |
| ✨ 1.2× | 1.2× | 5 |
| 💛 1.5× | 1.5× | 4 |
| 💚 2×   | 2×  | 3 |
| 💙 3×   | 3×  | 2 |
| 💜 5×   | 5×  | 1 |
| 🔥 10×  | 10× | 1 |
| ⭐ 25×  | 25× | 1 |

Higher weight = more likely to land there. Total weight: 23.

## Setup

Load the cog as `Casino.spinwheel.spinwheel`.

## Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_BET` | `10` | Minimum bet |
| `MAX_BET` | `-1` | Maximum bet (-1 = no limit) |

Wheel segments are defined in `_SEGMENTS` inside `spinwheel.py` as `(label, multiplier, weight)` tuples.
