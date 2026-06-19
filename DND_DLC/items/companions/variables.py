def register(api):

    api.add_item({
        "id":           "wolf_companion",
        "name":         "Wolf Companion",
        "emoji":        "🐺",
        "slot":         "companion",
        "beast_name":   "Wolf",
        "beast_dmg":    "1d6+2",
        "beast_atk_mod": -2,
        "tier":         "common",
        "sell":         50,
        "description":  "A loyal wolf that fights at your side. (Beast Master only)",
    })
    api.add_shop_item({
        "id":          "wolf_companion",
        "name":        "Wolf Companion",
        "emoji":       "🐺",
        "description": "A loyal wolf that fights at your side — 1d6+2 dmg, ATK −2. (Beast Master only)",
        "price":       150,
        "max_qty":     1,
        "tier":        "common",
    })

    api.add_item({
        "id":           "eagle_companion",
        "name":         "Eagle Companion",
        "emoji":        "🦅",
        "slot":         "companion",
        "beast_name":   "Eagle",
        "beast_dmg":    "1d4+3",
        "beast_atk_mod": 0,
        "tier":         "uncommon",
        "sell":         110,
        "description":  "A keen eagle that strikes fast. (Beast Master only)",
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

    api.add_item({
        "id":           "bear_companion",
        "name":         "Bear Companion",
        "emoji":        "🐻",
        "slot":         "companion",
        "beast_name":   "Bear",
        "beast_dmg":    "1d8+3",
        "beast_atk_mod": -1,
        "tier":         "rare",
        "sell":         200,
        "description":  "A powerful bear that hits hard. (Beast Master only)",
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

    api.add_item({
        "id":           "baby_dragon_companion",
        "name":         "Baby Dragon Companion",
        "emoji":        "🐉",
        "slot":         "companion",
        "beast_name":   "Baby Dragon",
        "beast_dmg":    "2d6+4",
        "beast_atk_mod": 0,
        "tier":         "legendary",
        "sell":         750,
        "description":  "A fierce baby dragon with fiery breath. (Beast Master only)",
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
