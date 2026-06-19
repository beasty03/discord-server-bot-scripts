def register(api):

    api.add_shop_item({
        "id":          "dagger",
        "name":        "Dagger",
        "emoji":       "🔪",
        "description": "A small but quick blade. 1d4 piercing, DEX-based, one-handed.",
        "price":       10,
        "max_qty":     1,
        "tier":        "common",
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

    api.add_shop_item({
        "id":          "mace",
        "name":        "Mace",
        "emoji":       "🔨",
        "description": "A blunt club favoured by clerics. 1d6 bludgeoning, STR-based, one-handed.",
        "price":       20,
        "max_qty":     1,
        "tier":        "common",
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
