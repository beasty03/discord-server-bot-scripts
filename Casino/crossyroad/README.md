# 🐔 Crossy Road

An interactive hop-or-cashout game. Cross traffic lanes one at a time — each hop risks a car, but the further you go the bigger the reward. Cash out any time or get wiped out trying.

Commands: 1

## How it works

1. Use `/crossyroad <amount>` to start a game (ephemeral — only you see it).
2. Your road appears showing all lanes and their payout values.
3. Press **🏃 HOP!** to attempt crossing the next lane.
   - Each hop has a `CAR_CHANCE`% chance of a car hitting you — you lose your bet.
   - If you survive, your current value increases to the next lane's multiplier.
4. Press **💰 Cash Out** at any time (after at least 1 successful hop) to collect your current value.
5. Cross all lanes to automatically cash out at the maximum multiplier.
6. A public result is posted to the channel on cashout or wipeout.

### Example road display

```
🏠 Home
🛣️  Lane 7 · 🪙 10,000
🛣️  Lane 6 · 🪙 6,000
🐔 Lane 5 · 🪙 3,500     ← next hop
✅ Lane 4 · 🪙 2,250
✅ Lane 3 · 🪙 1,500
✅ Lane 2 · 🪙 1,100
✅ Lane 1 · 🪙 850
🏁 Start · 🪙 500
```

## Commands

| Command | Description |
|---------|-------------|
| `/crossyroad <amount>` | Start a Crossy Road game |

## Payout Table (defaults)

| Lanes Crossed | Return Multiplier | Profit on 500 bet |
|---------------|-------------------|-------------------|
| 1 | 1.7× | +350 |
| 2 | 2.2× | +600 |
| 3 | 3.0× | +1,000 |
| 4 | 4.5× | +1,750 |
| 5 | 7.0× | +3,000 |
| 6 | 12.0× | +5,500 |
| 7 | 20.0× | +9,500 |

> Multipliers are **total return** (including original bet). Profit = payout − bet.

## Setup

1. Load the cog in your bot launcher:
   ```
   Casino/crossyroad/crossyroad.py
   ```
2. Configure `variables.py` as needed.

## Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_BET` | `10` | Minimum bet |
| `MAX_BET` | `-1` | Maximum bet (-1 = no limit) |
| `CAR_CHANCE` | `35` | % chance of a car per hop (1–100) |
| `LANE_MULTIPLIERS` | `[1.7, 2.2, 3.0, 4.5, 7.0, 12.0, 20.0]` | Return multiplier per lane crossed |
| `BUTTON_TIMEOUT` | `60` | Seconds before buttons expire |
| `CURRENCY_NAME` | config | Currency name |
| `CURRENCY_SYMBOL` | config | Currency emoji |

The number of lanes is determined by the length of `LANE_MULTIPLIERS`. Add or remove entries to change it.

## Timeout behaviour

| State at timeout | Result |
|------------------|--------|
| 0 lanes crossed | Bet refunded |
| 1+ lanes crossed | Auto-cashout at current value |

## Multiplier Event

When a Multiplier Event is active (`/startevent Multiplier`), the **profit** on any cashout is boosted by the active multiplier. The original bet is always returned on top.

## Technical notes

- Bet is deducted upfront when the game starts.
- Only the player who started the game can press the buttons.
- `games_won` / `games_lost` columns are added to `casino_stats` automatically on cog load.
- Car hit = loss (no partial refund), matching the risk-vs-reward design.
