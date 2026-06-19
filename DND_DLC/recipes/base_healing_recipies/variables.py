# New crafted items — picked up by CharacterCog._scan_dlc_items() so the whole
# item system (inventory, recipes cog, combat) can find them by id.
CHAR_ITEMS = [
    {
        "id":          "bandage",
        "name":        "Bandage",
        "emoji":       "🩹",
        "slot":        "consumable",
        "heal_expr":   "1d4",
        "tier":        "common",
        "sell":        5,
        "description": "A quick field dressing. Restores 1d4 HP.",
    },
    {
        "id":          "herbal_tea",
        "name":        "Herbal Tea",
        "emoji":       "🫖",
        "slot":        "consumable",
        "heal_expr":   "2",
        "tier":        "common",
        "sell":        2,
        "description": "A soothing brew. Restores a flat 2 HP.",
    },
]


def register(api):
    for item in CHAR_ITEMS:
        api.add_item(item)

    api.add_shop_item({
        "id":          "bandage",
        "name":        "Bandage",
        "emoji":       "🩹",
        "description": "A quick field dressing. Restores 1d4 HP.",
        "price":       15,
        "max_qty":     10,
        "tier":        "common",
    })

    api.add_shop_item({
        "id":          "herbal_tea",
        "name":        "Herbal Tea",
        "emoji":       "🫖",
        "description": "A soothing brew. Restores a flat 2 HP.",
        "price":       5,
        "max_qty":     10,
        "tier":        "common",
    })

    # ── Base recipes (always known, no unlock needed) ─────────────────────────

    api.add_recipe({
        "id":          "herbal_tea",
        "name":        "Herbal Tea",
        "emoji":       "🫖",
        "tier":        "common",
        "unlock":      None,
        "inputs":      [("herb", 1)],
        "output":      ("herbal_tea", 1),
        "description": "A soothing brew. Restores a flat 2 HP.",
    })

    api.add_recipe({
        "id":          "bandage",
        "name":        "Bandage",
        "emoji":       "🩹",
        "tier":        "common",
        "unlock":      None,
        "inputs":      [("leather_scrap", 2)],
        "output":      ("bandage", 1),
        "description": "A quick field dressing. Restores 1d4 HP.",
    })

    api.add_recipe({
        "id":          "small_health_potion",
        "name":        "Small Health Potion",
        "emoji":       "🧪",
        "tier":        "common",
        "unlock":      None,
        "inputs":      [("herb", 2)],
        "output":      ("small_health_potion", 1),
        "description": "A modest healing draught. Restores 1d4+1 HP.",
    })

    # ── Uncommon recipes (require a recipe scroll to unlock) ──────────────────

    api.add_recipe({
        "id":          "health_potion",
        "name":        "Health Potion",
        "emoji":       "🧪",
        "tier":        "uncommon",
        "unlock":      "recipe_hp_medium",
        "inputs":      [("herb", 3), ("leather_scrap", 1)],
        "output":      ("health_potion", 1),
        "description": "A sturdy potion brewed with tanned hide. Restores 2d4+2 HP.",
    })

    # ── Rare recipes (require a recipe scroll to unlock) ──────────────────────

    api.add_recipe({
        "id":          "large_health_potion",
        "name":        "Large Health Potion",
        "emoji":       "🧪",
        "tier":        "rare",
        "unlock":      "recipe_hp_large",
        "inputs":      [("herb", 5), ("leather_scrap", 2), ("arcane_shard", 1)],
        "output":      ("large_health_potion", 1),
        "description": "An alchemical masterwork. Restores 4d4+4 HP.",
    })
