# 🗡️ DungeonMaster

The core D&D engine. Runs the quest board, manages round-based combat, handles skill checks, and exposes the dice system. All DLC content registers here.

---

## Commands

| Command | Description |
|---|---|
| `/wander` | Browse the quest board and launch a campaign (solo or with your party). |
| `/roll <dice>` | Roll dice anywhere. Supports `d20`, `2d6`, `1d8+3` etc. |

---

## How campaigns work

1. `/wander` shows campaigns your character's level can attempt (up to 5, rotated daily when more exist).
2. Pick one from the list.
3. **Party** — a 60-second join window opens. Party members click **⚔️ Join the quest**. Run starts when the window closes.
4. **Solo** — starts immediately.

### Encounters

Each campaign is a sequence of encounters:

**Combat** — round-based. Each round:
- All active participants click **⚔️ Attack**, **🛡️ Dodge**, or **🏃 Flee** (30-second window; no action = auto-dodge).
- Attackers roll `d20 + ATK bonus` vs enemy AC. Hit → damage. Crit (nat 20) → double dice.
- Dodging adds +2 AC and halves damage if hit.
- Enemy retaliates against a random non-fled player.
- When an enemy hits 0 HP, the killing player gets a button to describe the killing blow (optional, non-blocking).

**Interaction** — one skill check:
- The encounter shows a skill button (e.g. 🗣️ Persuade) and optionally ⚔️ Fight Instead.
- Clicking the skill button opens a modal — players can type what they do or say (optional flavor text).
- Rolls `d20 + ability mod` vs DC. Success → narrative reward. Failure → fallback combat or narrative consequence only.

### Combat stats used

| Stat | Source |
|---|---|
| Attack bonus | max(STR, DEX) mod + proficiency, or weapon ability if equipped |
| Damage | Equipped weapon damage die + ability mod; unarmed = `1d4` |
| AC | 10 + DEX mod + class armor bonus |
| Skill checks | Ability modifier matching the encounter's `skill` field |

---

## DLC integration

DLC cogs in `DND_DLC/` call these methods in their `setup()`:

```python
async def setup(bot):
    dm = bot.get_cog("DungeonMasterCog")
    if dm:
        dm.register_campaign(MY_CAMPAIGN)   # adds to quest board
        dm.register_race(MY_RACE)           # registers a playable race
        dm.register_class(MY_CLASS)         # registers a playable class
```

Campaigns must follow the same structure as entries in `CAMPAIGNS` in `variables.py`.

---

## Configuration (`variables.py`)

| Variable | Default | Description |
|---|---|---|
| `WANDER_JOIN_TIMEOUT` | `60` | Seconds the party join window stays open |
| `ROUND_TIMEOUT` | `30` | Seconds per combat round |
| `INTERACTION_TIMEOUT` | `45` | Seconds for skill check decisions |
| `KILL_MODAL_TIMEOUT` | `120` | Seconds to describe the killing blow |
| `RESULT_DELAY` | `3` | Pause between rounds (seconds) |
| `MAX_SHOWN_CAMPAIGNS` | `5` | Quest board size; rotates daily when exceeded |

Add or edit campaigns by modifying the `CAMPAIGNS` list in `variables.py`.
