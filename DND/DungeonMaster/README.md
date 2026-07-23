# ⚔️ DungeonMaster

Turn-based D&D combat engine — runs campaigns, processes DLC events, and exposes all combat slash commands.

---

Commands: 21

## Commands

| Command | Description |
|---|---|
| `/wander` | Start a solo campaign from the available list. |
| `/party` | Form a party for a multi-player campaign. |
| `/attack [target]` | Roll a weapon attack on your turn. |
| `/ability <ability>` | Use a class ability (auto-completes with your available abilities). |
| `/bonus` | Open the bonus action menu for your class. |
| `/item <item>` | Use a consumable from your inventory on your turn. |
| `/endturn` | Confirm all queued actions and end your turn. |
| `/flee` | Attempt to flee the current encounter. |
| `/support` | Help an ally — grants +4 to their next skill check roll. |
| `/set_level <level>` | Set your character level (dev/admin use). |

---

## Module layout

| File | Role |
|---|---|
| `combat.py` | Discord cog — all slash commands, turn loop, round processing |
| `engine.py` | Event bus — `engine.fire(event, ctx)` dispatches to DLC handlers |
| `api.py` | DLC registration surface — `add_class`, `add_race`, `add_item`, `add_spell`, `on` |
| `context.py` | `CombatContext` — read-only snapshot passed to every handler |
| `effects.py` | Effect types returned by handlers: `Heal`, `Modify`, `Status`, `Flag`, `BonusAttack`, `Message` |
| `registry.py` | Runtime store for all registered classes, races, items, campaigns, spells |
| `loader.py` | Scans `DND_DLC/` at startup and calls `register(api)` on each `variables.py` |
| `dispatcher.py` | Collects handler results and merges them into `ResolvedEffects` |
| `resolver.py` | Converts raw effect lists into typed `ResolvedEffects` structs |
| `dice.py` | Dice expression parser and roller (e.g. `"2d8+3"`) |
| `variables.py` | Bot configuration: colours, emoji, channel IDs |

---

## Combat flow

1. Player runs `/wander` (solo) or `/party` + `/wander` (group) — engine picks a campaign and builds a run state
2. Each round: engine waits for all active players to queue a main action and optional bonus action (30 s timeout)
3. Bonus actions resolve first, then main actions in initiative order
4. For each ability action the engine fires `on_ability_use`; for attacks it fires `on_before_attack`, `on_damage_roll`, `on_hit` or `on_take_damage`
5. DLC handlers return `Effect` lists; the engine accumulates them into `ResolvedEffects` and applies the changes to the run state
6. A round-summary embed is posted; combat loops until all enemies or all players are down

---

## DLC integration

All content is external. Drop a `variables.py` in any `DND_DLC/*/` folder — it is loaded automatically at startup. No engine edits needed.

See [`DND_DLC/_template/variables.py`](../../DND_DLC/_template/variables.py) for a fully commented starter with all API methods documented.
