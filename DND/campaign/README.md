# 🗺️ Campaign

Start solo or group adventures. Pick a campaign from a list gated by your level, survive the run, and earn gold and XP.

## Commands

| Command | Description |
|---------|-------------|
| `/wander` | Browse campaigns available for your level and launch an adventure. |

## How it works

1. `/wander` shows all campaigns your character is high enough level to attempt.
2. Pick one from the list.
3. **In a party** — a join window opens in the channel for `60s`. Party members click **⚔️ Join the quest** to opt in; the run starts automatically when the window closes.
4. **Solo** — the run starts immediately.
5. On success, gold is split equally among participants and XP is awarded to each individually.

## Campaign list

| Campaign | Min level | Difficulty | XP |
|----------|-----------|------------|-----|
| 👺 Goblin Scouts | 1 | Easy | 75 |
| ⚔️ Bandit Camp | 2 | Medium | 200 |
| 🌑 Dark Forest | 3 | Medium | 350 |
| 🏰 Ruined Keep | 5 | Hard | 600 |
| 🐉 Dragon's Lair | 10 | Deadly | 2000 |

Campaigns are repeatable — there is no completion lock.

## Rules

- A character (`/name`, `/race`, `/class`) is required.
- You can only be in one active run at a time.
- A party can only have one active run at a time.
- The campaign list is gated by **the initiator's level**, not the party's highest. A level-3 player only sees campaigns up to level 3. For harder content, the higher-level player must be the one to run `/wander`.
- If the party doesn't fill up before the join window closes, the run starts with whoever joined.

## Level-up

XP is added to your character after a successful run. If it crosses the next level threshold, your level updates automatically — visible on `/sheet` and `/level`.

## Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `WANDER_JOIN_TIMEOUT` | `60` | Seconds the party join window stays open |
| `WANDER_RESULT_DELAY` | `4` | Seconds between campaign intro and outcome reveal |

Add or edit campaigns by modifying the `CAMPAIGNS` list in `variables.py`.
