# ⚗️ Recipes DLC

Crafting recipes registered via `api.add_recipe()`. Players craft items using the `/craft` command by combining materials from their inventory.

---

## Folders

| Folder | Contents |
|---|---|
| [`base_healing_recipies/`](base_healing_recipies/) | Bandage and Herbal Tea |

---

## Adding a recipe

```python
api.add_recipe({
    "id":          "my_recipe",
    "name":        "My Crafted Item",
    "emoji":       "⚗️",
    "tier":        "common",
    "unlock":      None,           # None = always known; or a scroll item id
    "inputs":      [("herb", 2), ("leather_scrap", 1)],
    "output":      ("my_crafted_item", 1),
    "description": "Craft description shown to the player.",
})
```

The output item must also be registered with `api.add_item()` so the inventory system can find it by id.
