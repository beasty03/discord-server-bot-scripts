def register(api):

    api.add_item({
        "id":          "shortsword",
        "name":        "Shortsword",
        "emoji":       "🗡️",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "dexterity",
        "dmg":         "1d6",
        "handed":      1,
        "tier":        "common",
        "sell":        18,
        "description": "A light martial blade.",
    })
    api.add_shop_item({
        "id":          "shortsword",
        "name":        "Shortsword",
        "emoji":       "🗡️",
        "description": "A light martial blade. 1d6 slashing, DEX-based, one-handed.",
        "price":       50,
        "max_qty":     1,
        "tier":        "common",
    })

    api.add_item({
        "id":          "longsword",
        "name":        "Longsword",
        "emoji":       "⚔️",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "strength",
        "dmg":         "1d8",
        "handed":      1,
        "tier":        "uncommon",
        "sell":        27,
        "description": "A reliable martial sword.",
    })
    api.add_shop_item({
        "id":          "longsword",
        "name":        "Longsword",
        "emoji":       "⚔️",
        "description": "A reliable martial sword. 1d8 slashing, STR-based, one-handed.",
        "price":       75,
        "max_qty":     1,
        "tier":        "uncommon",
    })

    api.add_item({
        "id":          "rapier",
        "name":        "Rapier",
        "emoji":       "🤺",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "dexterity",
        "dmg":         "1d8",
        "handed":      1,
        "tier":        "uncommon",
        "sell":        28,
        "description": "A precise dueling blade.",
    })
    api.add_shop_item({
        "id":          "rapier",
        "name":        "Rapier",
        "emoji":       "🤺",
        "description": "A precise dueling blade. 1d8 piercing, DEX-based, one-handed.",
        "price":       80,
        "max_qty":     1,
        "tier":        "uncommon",
    })

    api.add_item({
        "id":          "greataxe",
        "name":        "Greataxe",
        "emoji":       "🪓",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "strength",
        "dmg":         "1d12",
        "handed":      2,
        "tier":        "rare",
        "sell":        50,
        "description": "A brutal two-handed axe.",
    })
    api.add_shop_item({
        "id":          "greataxe",
        "name":        "Greataxe",
        "emoji":       "🪓",
        "description": "A brutal two-handed axe. 1d12 slashing, STR-based.",
        "price":       150,
        "max_qty":     1,
        "tier":        "rare",
    })

    api.add_item({
        "id":          "greatsword",
        "name":        "Greatsword",
        "emoji":       "⚔️",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "strength",
        "dmg":         "2d6",
        "handed":      2,
        "tier":        "rare",
        "sell":        50,
        "description": "A massive two-handed sword.",
    })
    api.add_shop_item({
        "id":          "greatsword",
        "name":        "Greatsword",
        "emoji":       "⚔️",
        "description": "A massive two-handed sword. 2d6 slashing, STR-based.",
        "price":       150,
        "max_qty":     1,
        "tier":        "rare",
    })
