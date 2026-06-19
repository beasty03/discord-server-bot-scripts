def register(api):

    api.add_item({
        "id":          "dagger",
        "name":        "Dagger",
        "emoji":       "🔪",
        "slot":        "weapon",
        "weapon_type": "simple",
        "ability":     "dexterity",
        "dmg":         "1d4",
        "handed":      1,
        "tier":        "common",
        "sell":        4,
        "description": "A small but quick blade.",
    })
    api.add_shop_item({
        "id":          "dagger",
        "name":        "Dagger",
        "emoji":       "🔪",
        "description": "A small but quick blade. 1d4 piercing, DEX-based, one-handed.",
        "price":       10,
        "max_qty":     1,
        "tier":        "common",
    })

    api.add_item({
        "id":          "handaxe",
        "name":        "Handaxe",
        "emoji":       "🪓",
        "slot":        "weapon",
        "weapon_type": "simple",
        "ability":     "strength",
        "dmg":         "1d6",
        "handed":      1,
        "tier":        "common",
        "sell":        5,
        "description": "A versatile one-handed axe.",
    })
    api.add_shop_item({
        "id":          "handaxe",
        "name":        "Handaxe",
        "emoji":       "🪓",
        "description": "A versatile one-handed axe. 1d6 slashing, STR-based.",
        "price":       15,
        "max_qty":     1,
        "tier":        "common",
    })

    api.add_item({
        "id":          "mace",
        "name":        "Mace",
        "emoji":       "🔨",
        "slot":        "weapon",
        "weapon_type": "simple",
        "ability":     "strength",
        "dmg":         "1d6",
        "handed":      1,
        "tier":        "common",
        "sell":        7,
        "description": "A blunt club favoured by clerics.",
    })
    api.add_shop_item({
        "id":          "mace",
        "name":        "Mace",
        "emoji":       "🔨",
        "description": "A blunt club favoured by clerics. 1d6 bludgeoning, STR-based, one-handed.",
        "price":       20,
        "max_qty":     1,
        "tier":        "common",
    })

    api.add_item({
        "id":          "quarterstaff",
        "name":        "Quarterstaff",
        "emoji":       "🪄",
        "slot":        "weapon",
        "weapon_type": "simple",
        "ability":     "strength",
        "dmg":         "1d8",
        "handed":      1,
        "tier":        "common",
        "sell":        5,
        "description": "A sturdy wooden staff.",
    })
    api.add_shop_item({
        "id":          "quarterstaff",
        "name":        "Quarterstaff",
        "emoji":       "🪄",
        "description": "A sturdy wooden staff. 1d8 bludgeoning, STR-based, one-handed.",
        "price":       15,
        "max_qty":     1,
        "tier":        "common",
    })
