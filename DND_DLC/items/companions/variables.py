def register(api):

    api.add_shop_item({
        "id":          "wolf_companion",
        "name":        "Wolf Companion",
        "emoji":       "🐺",
        "description": "A loyal wolf that fights at your side — 1d6+2 dmg, ATK −2. (Beast Master only)",
        "price":       150,
        "max_qty":     1,
        "tier":        "common",
    })

    api.add_shop_item({
        "id":          "eagle_companion",
        "name":        "Eagle Companion",
        "emoji":       "🦅",
        "description": "A keen eagle that strikes fast — 1d4+3 dmg, no ATK penalty. (Beast Master only)",
        "price":       350,
        "max_qty":     1,
        "tier":        "uncommon",
    })

    api.add_shop_item({
        "id":          "bear_companion",
        "name":        "Bear Companion",
        "emoji":       "🐻",
        "description": "A powerful bear that hits hard — 1d8+3 dmg, ATK −1. (Beast Master only)",
        "price":       650,
        "max_qty":     1,
        "tier":        "rare",
    })

    api.add_shop_item({
        "id":          "baby_dragon_companion",
        "name":        "Baby Dragon Companion",
        "emoji":       "🐉",
        "description": "A fierce baby dragon with fiery breath — 2d6+4 dmg, no ATK penalty. (Beast Master only)",
        "price":       2500,
        "max_qty":     1,
        "tier":        "legendary",
    })
