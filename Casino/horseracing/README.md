# 🏇 Horse Racing

Multiplayer casino game where players bet on one of six horses and share a public race channel message.

Commands: 1

## Command

```
/horserace <amount>
```

- The first player to run the command opens a race lobby in the channel.
- Every subsequent `/horserace` from a different player joins the same race (different bets allowed).
- After the join window closes the race resolves automatically — no action required.

## How it works

1. Player runs `/horserace 200` → a public embed appears showing all 6 horses with odds and a countdown.
2. Each player gets an **ephemeral** horse-picker (buttons). Pick before time runs out.
3. If a player doesn't pick in time their bet is **automatically refunded**.
4. The race resolves in two frames: a mid-race snapshot, then the final result with payouts.

## Payout

Winners receive `bet × horse odds` (e.g. betting 100 on Blaze at 5:1 returns 500).  
This is **individual odds payout** — not pot-sharing.

## Horses

| # | Horse    | Emoji | Odds | Win Chance |
|---|----------|-------|------|------------|
| 1 | Thunder  | ⚡    | 2:1  | ~34%       |
| 2 | Splash   | 💧    | 3:1  | ~26%       |
| 3 | Blaze    | 🔥    | 5:1  | ~18%       |
| 4 | Lucky    | 🍀    | 7:1  | ~12%       |
| 5 | Midnight | 🌙    | 9:1  | ~7%        |
| 6 | Comet    | ⭐    | 14:1 | ~3%        |

Higher odds = higher payout but lower chance of winning.

## Configuration (`variables.py`)

The `HORSES` list in `variables.py` is the single source of truth — both the standalone `/horserace` game and the casino event use the same list. Edit names, emojis, odds, and chances there; both games update automatically.

## Variables (`variables.py`)

| Variable              | Default | Description                                          |
|-----------------------|---------|------------------------------------------------------|
| `MIN_BET`             | 10      | Minimum bet amount                                   |
| `MAX_BET`             | -1      | Maximum bet (-1 = no limit)                          |
| `JOIN_WINDOW`         | 45      | Seconds the lobby stays open for new riders          |
| `RACE_ANIMATION_DELAY`| 2.5     | Seconds between mid-race and final-result frames     |
| `TRACK_LENGTH`        | 12      | Number of segments in the progress bar               |
| `BUTTON_TIMEOUT`      | 60      | Seconds a player has to pick a horse (ephemeral UI)  |

## Casino Event integration

Horse Racing is also available as a casino event game via `/startevent` → `horseracing`.  
In event mode bets are placed via `/join` and the same individual-odds payout applies.
