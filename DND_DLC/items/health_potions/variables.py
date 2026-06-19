def register(api):

    api.add_item({
        "id":          "small_health_potion",
        "name":        "Small Health Potion",
        "emoji":       "🧪",
        "slot":        "consumable",
        "heal_expr":   "1d4+1",
        "tier":        "common",
        "sell":        8,
        "description": "A modest healing draught. Restores 1d4+1 HP.",
    })
    api.add_shop_item({
        "id":          "small_health_potion",
        "name":        "Small Health Potion",
        "emoji":       "🧪",
        "description": "A modest healing draught. Restores 1d4+1 HP.",
        "price":       25,
        "max_qty":     10,
        "tier":        "common",
    })

    api.add_item({
        "id":          "health_potion",
        "name":        "Health Potion",
        "emoji":       "🧪",
        "slot":        "consumable",
        "heal_expr":   "2d4+2",
        "tier":        "uncommon",
        "sell":        20,
        "description": "A sturdy healing potion. Restores 2d4+2 HP.",
    })
    api.add_shop_item({
        "id":          "health_potion",
        "name":        "Health Potion",
        "emoji":       "🧪",
        "description": "A sturdy healing potion. Restores 2d4+2 HP.",
        "price":       50,
        "max_qty":     5,
        "tier":        "uncommon",
    })

    api.add_item({
        "id":          "large_health_potion",
        "name":        "Large Health Potion",
        "emoji":       "🧪",
        "slot":        "consumable",
        "heal_expr":   "4d4+4",
        "tier":        "rare",
        "sell":        45,
        "description": "An alchemical masterwork. Restores 4d4+4 HP.",
    })
    api.add_shop_item({
        "id":          "large_health_potion",
        "name":        "Large Health Potion",
        "emoji":       "🧪",
        "description": "An alchemical masterwork. Restores 4d4+4 HP.",
        "price":       100,
        "max_qty":     3,
        "tier":        "rare",
    })

    api.add_item({
        "id":          "recipe_hp_medium",
        "name":        "Recipe: Health Potion",
        "emoji":       "📜",
        "slot":        "recipe",
        "unlocks":     "health_potion",
        "tier":        "uncommon",
        "sell":        60,
        "description": "Unlocks the Health Potion crafting recipe (2d4+2 heal).",
    })
    api.add_shop_item({
        "id":          "recipe_hp_medium",
        "name":        "Recipe: Health Potion",
        "emoji":       "📜",
        "description": "Unlocks the Health Potion crafting recipe (2d4+2 heal).",
        "price":       150,
        "max_qty":     1,
        "tier":        "uncommon",
    })

    api.add_item({
        "id":          "recipe_hp_large",
        "name":        "Recipe: Large Health Potion",
        "emoji":       "📜",
        "slot":        "recipe",
        "unlocks":     "large_health_potion",
        "tier":        "rare",
        "sell":        150,
        "description": "Unlocks the Large Health Potion crafting recipe (4d4+4 heal).",
    })
    api.add_shop_item({
        "id":          "recipe_hp_large",
        "name":        "Recipe: Large Health Potion",
        "emoji":       "📜",
        "description": "Unlocks the Large Health Potion crafting recipe (4d4+4 heal).",
        "price":       400,
        "max_qty":     1,
        "tier":        "rare",
    })
