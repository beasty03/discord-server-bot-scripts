def register(api):

    api.add_item({
        "id":          "shortbow",
        "name":        "Shortbow",
        "emoji":       "🏹",
        "slot":        "weapon",
        "weapon_type": "simple",
        "ability":     "dexterity",
        "dmg":         "1d6",
        "handed":      2,
        "ranged":      True,
        "tier":        "common",
        "sell":        10,
        "description": "A nimble simple bow.",
    })
    api.add_shop_item({
        "id":          "shortbow",
        "name":        "Shortbow",
        "emoji":       "🏹",
        "description": "A nimble simple bow. 1d6 piercing, DEX-based, two-handed.",
        "price":       30,
        "max_qty":     1,
        "tier":        "common",
    })

    api.add_item({
        "id":          "longbow",
        "name":        "Longbow",
        "emoji":       "🏹",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "dexterity",
        "dmg":         "1d8",
        "handed":      2,
        "ranged":      True,
        "tier":        "uncommon",
        "sell":        35,
        "description": "A powerful martial bow.",
    })
    api.add_shop_item({
        "id":          "longbow",
        "name":        "Longbow",
        "emoji":       "🏹",
        "description": "A powerful martial bow. 1d8 piercing, DEX-based, two-handed.",
        "price":       100,
        "max_qty":     1,
        "tier":        "uncommon",
    })
