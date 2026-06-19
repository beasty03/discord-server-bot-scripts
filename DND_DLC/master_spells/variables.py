def register(api):

    api.add_shop_item({
        "id":          "scroll_fireball",
        "name":        "Scroll of Fireball",
        "emoji":       "📜",
        "description": "Permanently teaches a Wizard the iconic Fireball spell (8d6 fire). Wizard Lv 5+.",
        "price":       750,
        "max_qty":     1,
        "tier":        "epic",
    })

    api.add_shop_item({
        "id":          "scroll_counterspell",
        "name":        "Scroll of Counterspell",
        "emoji":       "📜",
        "description": "Permanently teaches a Wizard Counterspell — cancel the enemy's attack. Wizard Lv 5+.",
        "price":       600,
        "max_qty":     1,
        "tier":        "epic",
    })
