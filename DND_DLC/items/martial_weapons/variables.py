def register(api):

    api.add_shop_item({
        "id":          "shortsword",
        "name":        "Shortsword",
        "emoji":       "🗡️",
        "description": "A light martial blade. 1d6 slashing, DEX-based, one-handed.",
        "price":       50,
        "max_qty":     1,
        "tier":        "common",
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

    api.add_shop_item({
        "id":          "rapier",
        "name":        "Rapier",
        "emoji":       "🤺",
        "description": "A precise dueling blade. 1d8 piercing, DEX-based, one-handed.",
        "price":       80,
        "max_qty":     1,
        "tier":        "uncommon",
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

    api.add_shop_item({
        "id":          "greatsword",
        "name":        "Greatsword",
        "emoji":       "⚔️",
        "description": "A massive two-handed sword. 2d6 slashing, STR-based.",
        "price":       150,
        "max_qty":     1,
        "tier":        "rare",
    })
