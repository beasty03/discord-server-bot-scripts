# 🃏 Poker

Multiplayer Texas Hold'em with ante buy-in. Players join a lobby, receive private hole cards via DM, and compete for the full pot across a Flop → Turn → River reveal. Best hand wins.

Commands: 1

## Commands

| Command | Description |
|---------|-------------|
| `/poker <ante>` | Open a table — you auto-join as host |

## Game flow

1. **Join phase** (`JOIN_WINDOW` seconds)
   - Public embed shows who has joined.
   - Any server member can click **🃏 Join** to buy in.
   - The host can click **▶️ Force Start** once 2+ players are seated.
   - If fewer than `MIN_PLAYERS` join before the timer expires, the game is cancelled (no charge).

2. **Antes deducted** — all players pay the ante at game start.

3. **Hole cards dealt** — each player receives their 2 hole cards as a **Discord DM**.
   - Players with DMs blocked receive an auto-check and are warned publicly.

4. **Pre-Flop decision** (`PREFLOP_TIMEOUT` seconds)
   - Public message shows **✅ Check (Stay In)** and **❌ Fold (Lose Ante)** buttons.
   - Only players in the game can click.
   - Non-respondents auto-check.
   - The last remaining player cannot fold.
   - If only 1 player survives the fold, they win the pot immediately.

5. **Flop → Turn → River** — community cards revealed with delays between each.

6. **Showdown** — all remaining players' hole cards + hand ranks are revealed publicly. Best hand wins the full pot. On a tie the pot is split evenly.

## Casino Event

Poker can appear as a random casino event (`CASINO_GAMES` in `Events/casino_event/variables.py`).

- Players join with `/join <wage>` during the join window.
- **Minimum 3 players** required (set via `POKER_EVENT_MIN_PLAYERS`). If fewer join, bets are refunded.
- **Pot mode** — the house doubles the prize pool (same as the Gamble event).
- No pre-flop fold phase in event mode — everyone plays through to showdown.
- Hole cards sent via DM; community cards revealed publicly with delays.

## Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_BET` | `50` | Minimum ante |
| `MAX_BET` | `-1` | Maximum ante (`-1` = no limit) |
| `MIN_PLAYERS` | `2` | Minimum players to start a standalone game |
| `MAX_PLAYERS` | `8` | Maximum seats at the table |
| `JOIN_WINDOW` | `90` | Seconds the lobby stays open |
| `PREFLOP_TIMEOUT` | `30` | Seconds to check or fold |
| `DEAL_DELAY` | `5` | Pause (s) between deal and flop reveal |
| `REVEAL_DELAY` | `3` | Pause (s) between each community card |

## Hand rankings (high to low)

Royal Flush · Straight Flush · Four of a Kind · Full House · Flush · Straight · Three of a Kind · Two Pair · One Pair · High Card

Best 5-card hand selected from each player's 2 hole cards + 5 community cards (C(7,5) evaluation).
