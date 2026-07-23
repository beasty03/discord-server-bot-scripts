# Events/casino — Casino Event Cog

Runs periodic multiplayer casino events in a configured channel. A random game is picked from a configurable list, players join during a timed window, then a single shared resolution is posted for all participants.

Commands: 6

## Flow

1. Background task fires every `EVENT_INTERVAL_MINUTES` minutes.
2. Bot picks a random game from `CASINO_GAMES` and posts a join embed.
3. Players click **🎮 Join Event** — their bet is deducted and a default bet is assigned.
4. Games with choices (Roulette, Baccarat) show an ephemeral bet-selection view to override the default.
5. After `JOIN_WINDOW` seconds the wheel/cards resolve once for everyone; results are posted.

## Commands

| Command | Description | Permission |
|---------|-------------|------------|
| `/startevent` | Manually trigger a casino event right now. | Administrator |

## Variables (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `EVENT_CHANNEL_ID` | `0` | **Set this** — channel where events are announced |
| `EVENT_INTERVAL_MINUTES` | `60` | Minutes between automatic events |
| `JOIN_WINDOW` | `60` | Seconds players have to join |
| `EVENT_BET` | `100` | Coins deducted from each participant |
| `GAMBLE_WIN_CHANCE` | `45` | Win % for the Gamble game type |
| `GAMBLE_WIN_MULTIPLIER` | `2.0` | Payout multiplier on a Gamble win |
| `CASINO_GAMES` | see file | List of multiplayer-eligible games |

## Adding a Game

1. Add an entry to `CASINO_GAMES` in `variables.py`:
   ```python
   {
       "id":          "mygame",
       "label":       "🎯 My Game",
       "description": "Short description shown in the join embed.",
       "color":       0xABCDEF,
   }
   ```
2. Add a resolver function in `casino_event.py`:
   ```python
   def resolve_mygame(participants, event_bet, db, gid):
       # participants: dict[uid -> bet_choice]
       # return (summary_str, [(uid, delta_str, emoji, bet_label), ...])
       ...
   ```
3. Register it in the `RESOLVERS` dict:
   ```python
   RESOLVERS = {
       ...
       "mygame": resolve_mygame,
   }
   ```
4. Optionally add a `_BetView` subclass and entry in `_BET_VIEWS` if the game needs a bet-selection step.

## Dependencies

- `forge_db.ForgeDB` — `ensure_user`, `get_balance`, `update_balance`.
- Tables: `users` (balance).
