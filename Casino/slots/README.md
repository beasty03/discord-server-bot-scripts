# 🎰 Slots

A slot machine game with 8 weighted symbols, 3-of-a-kind jackpots, and 2-of-a-kind consolation payouts.

Commands: 1

## How it works

1. Use `/slots <amount>` to spin.
2. Three reels are drawn instantly using weighted randomness — rarer symbols appear less often but pay more.
3. **3-of-a-kind** pays the symbol's jackpot multiplier.
4. **2-of-a-kind** (any pair) pays a small consolation multiplier.
5. No match = loss.
6. The result appears privately; a brief win/loss announcement is posted to the channel.

## Commands

| Command | Description |
|---------|-------------|
| `/slots <amount>` | Spin the slot machine |

## Symbol Table

| Symbol | Rarity | 3× Payout |
|--------|--------|-----------|
| 🍒 Cherry | Very Common | 2.0× |
| 🍋 Lemon | Common | 2.5× |
| 🍊 Orange | Common | 3.0× |
| 🍇 Grapes | Uncommon | 4.0× |
| 🔔 Bell | Uncommon | 5.0× |
| ⭐ Star | Rare | 8.0× |
| 💎 Diamond | Very Rare | 15.0× |
| 7️⃣ Seven | Jackpot | 25.0× |

> A **2-of-a-kind** always pays `TWO_OF_A_KIND_MULT` (default 1.5×) regardless of which symbol.

Multipliers are **total return** (including the original bet). Profit = payout − bet.

## Setup

1. Load the cog in your bot launcher:
   ```
   Casino/slots/slots.py
   ```
2. Configure `variables.py` as needed.

## Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_BET` | `10` | Minimum bet |
| `MAX_BET` | `-1` | Maximum bet (-1 = no limit) |
| `TWO_OF_A_KIND_MULT` | `1.5` | Return multiplier for any pair |
| `CURRENCY_NAME` | config | Currency name |
| `CURRENCY_SYMBOL` | config | Currency emoji |

Symbol weights and 3-of-a-kind multipliers are defined in `_SYMBOLS` inside `slots.py`:
```python
# (emoji, weight, 3× return multiplier)
_SYMBOLS = [
    ("🍒", 30, 2.0),
    ...
    ("7️⃣",  2, 25.0),
]
```
Lower weight = rarer. Adjust freely.

## Multiplier Event

When a Multiplier Event is active (`/startevent Multiplier`), the **profit** portion of any slot win is boosted by the active multiplier. The original bet is always returned on top.

## Technical notes

- Bet is deducted upfront; winnings are credited immediately after the spin.
- `games_won` / `games_lost` columns are added to `casino_stats` automatically on cog load.
- A 2-of-a-kind with `mult = 1.5` returns 50% profit — a very small win to soften frequent near-misses.
