# 🚀 Rocket (Crash Game)

A DraftKings-style crash game. Watch the multiplier climb in real time and cash out before the rocket explodes.

## How to play

1. Use `/rocket <amount>` to place your bet.
2. The rocket launches at **1.00×** and climbs every 2 seconds.
3. Press **🚀 CASH OUT** at any time to lock in the current multiplier × bet.
4. If the rocket crashes before you cash out, you lose your bet.

The crash point is randomly determined before launch and hidden from the player.

## Commands

| Command | Description |
|---------|-------------|
| `/rocket <amount>` | Launch a Rocket game |

## Crash distribution

| Scenario | Approx. probability |
|----------|-------------------|
| Crash before 1.5× | ~34% |
| Crash before 2× | ~50% |
| Crash before 5× | ~80% |
| Survives past 10× | ~10% |
| Survives past 20× | ~5% |

Formula: `crash = 0.99 / (1 − rand)` — 1% of games crash instantly (house edge).

## Setup

Load the cog as `Casino.rocket.rocket`.

## Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_BET` | `10` | Minimum bet |
| `MAX_BET` | `-1` | Maximum bet (-1 = no limit) |
| `TICK_DELAY` | `2.0` | Seconds between multiplier updates |
| `TICK_STAGES` | `[1.0, 1.1, …, 50.0]` | Multiplier values the rocket can reach |
| `BUTTON_TIMEOUT` | `60` | Seconds before the game auto-crashes |

On timeout: bet is lost (treated as a crash).
