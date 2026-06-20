# ⚔️ Classes DLC

Playable character classes registered through the DLC engine. Each class defines abilities, subclasses, level choices, saving throw proficiencies, and starting equipment.

---

## Registered classes

| Folder | Class | Subclasses |
|---|---|---|
| [`fighter/`](fighter/) | ⚔️ Fighter | Champion, Battle Master, Eldritch Knight |
| [`ranger/`](ranger/) | 🏹 Ranger | Hunter, Beast Master |
| [`wizard/`](wizard/) | 🪄 Wizard | Evocation, Divination, Abjuration |

---

## Adding a new class

Create `DND_DLC/classes/{id}/variables.py` and call `api.add_class(data)` inside `register(api)`.

Minimum required fields:

```python
api.add_class({
    "id":            "my_class",
    "name":          "My Class",
    "emoji":         "⚔️",
    "hit_die":       10,
    "armor":         6,           # base AC (unarmored)
    "primary_stat":  "strength",
    "weapon_profs":  ["simple", "martial"],
    "armor_profs":   ["light", "medium", "heavy", "shields"],
    "saving_throws": ["strength", "constitution"],
    "start_items":   ["longsword"],
    "features":      [...],
    "abilities":     [...],
    "subclasses":    {},
    "level_choices": {},
})
```

See [`DND_DLC/_template/variables.py`](../_template/variables.py) for a fully commented example.
