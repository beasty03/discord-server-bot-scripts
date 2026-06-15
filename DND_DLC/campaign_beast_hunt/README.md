# 🐗 The Prowling Beast

**DLC Campaign — test script for the DungeonMaster engine.**

A low-level beast-slaying campaign designed to exercise both encounter types.

---

## Campaign info

| Field | Value |
|---|---|
| Min level | 1 |
| Difficulty | Easy |
| Reward | 20–50 coins · 50 XP |

## Encounters

| # | Type | Name | Notes |
|---|---|---|---|
| 1 | Interaction | Track the Beast | Wisdom DC 8 · no fallback combat — failure is flavor only |
| 2 | Combat | Wild Boar | HP 11 · AC 11 · tests attack rolls, dodge, kill modal |

## What this tests

- DLC registration via `dm.register_campaign()` in `setup()`
- Interaction encounter with skill flavor modal (DC 8 — easy pass)
- Round-based combat with a low-HP enemy (boar dies fast → kill modal fires quickly)
- `/story` output from the Scribe after the run completes

## Load order note

`DND/DungeonMaster` must load before `DND_DLC/campaign_beast_hunt`. If the cogloader processes categories alphabetically, `DND` comes before `DND_DLC` — this is correct. If your loader uses a different order, ensure DungeonMaster is loaded first.
