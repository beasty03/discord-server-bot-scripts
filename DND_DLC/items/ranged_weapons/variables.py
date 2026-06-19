def register(api):

    api.add_shop_item({
        "id":          "shortbow",
        "name":        "Shortbow",
        "emoji":       "🏹",
        "description": "A nimble simple bow. 1d6 piercing, DEX-based, two-handed.",
        "price":       30,
        "max_qty":     1,
        "tier":        "common",
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
