# 💎 Diamond Mines

A minesweeper-style casino game. Reveal diamonds on a 4×4 grid and cash out before you hit a mine.

Commands: 1

## How to play

1. Use `/mines <amount> [mines]` to start. Default: 3 mines.
2. A 4×4 grid (16 tiles) appears — mines are hidden randomly.
3. Click tiles to reveal them:
   - **💎** — safe! Your multiplier increases.
   - **💣** — mine! You lose your bet and all mines are revealed.
4. Cash out at any time with the **💰 Cash Out** button to collect your current multiplier × bet.
5. Find every single safe tile and you get an automatic **jackpot cashout**.

The more mines you choose, the higher the multiplier climbs per safe tile — but the bigger the risk.

## Commands

| Command | Description |
|---------|-------------|
| `/mines <amount> [mines]` | Start a Diamond Mines game |

## Multiplier table (approximate)

| Mines | Safe tiles | 1 pick | 3 picks | 5 picks | All picks |
|-------|-----------|--------|---------|---------|-----------|
| 1     | 15        | 1.04×  | 1.14×   | 1.27×   | ~7×       |
| 3     | 13        | 1.16×  | 1.50×   | 2.05×   | ~42×      |
| 5     | 11        | 1.32×  | 2.05×   | 3.72×   | ~372×     |
| 10    | 6         | 2.55×  | 8.74×   | 51×     | ~3 100×   |

Formula: `C(16, k) / C(16 − mines, k) × 0.97^k`

## Setup

Load the cog as `Casino.diamond_mines.diamond_mines`.

## Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_BET` | `10` | Minimum bet |
| `MAX_BET` | `-1` | Maximum bet (-1 = no limit) |
| `MIN_MINES` | `1` | Minimum mines the player can pick |
| `MAX_MINES` | `12` | Maximum mines the player can pick |
| `GRID_SIZE` | `16` | Total tiles (4×4) |
| `HOUSE_EDGE` | `0.97` | Per-pick multiplier reduction factor |
| `BUTTON_TIMEOUT` | `120` | Seconds before the game times out |

On timeout: auto-cashes out if any safe tiles were found, otherwise refunds the bet.
