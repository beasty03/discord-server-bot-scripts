# 🧬 Races DLC

Playable character races registered through the DLC engine. Each race defines ability score bonuses, passive traits, and optional subraces.

---

## Registered races

| Folder | Race | Stat bonuses | Subraces |
|---|---|---|---|
| [`elf/`](elf/) | 🧝 Elf | +2 DEX, +1 INT | High Elf, Wood Elf |
| [`dwarf/`](dwarf/) | 🪨 Dwarf | +2 CON, +1 STR | Hill Dwarf, Mountain Dwarf |
| [`human/`](human/) | 🧑 Human | +1 to all six stats | — (feat at Lv 1) |

---

## Adding a new race

Create `DND_DLC/races/{id}/variables.py` and call `api.add_race(data)` inside `register(api)`.

Minimum required fields:

```python
api.add_race({
    "id":           "my_race",
    "name":         "My Race",
    "emoji":        "🧝",
    "stat_bonuses": {"dexterity": 2, "intelligence": 1},
    "traits": [
        {"name": "Trait Name", "desc": "What it does."},
    ],
})
```

Subscribe passive handlers with `api.on(event, fn)` to wire up combat effects.
