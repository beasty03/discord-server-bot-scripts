def register(api):

    api.add_item({
        "id":          "shield",
        "name":        "Shield",
        "emoji":       "🛡️",
        "slot":        "offhand",
        "ac_bonus":    2,
        "tier":        "common",
        "sell":        10,
        "description": "A sturdy wooden shield. +2 AC.",
    })
    api.add_shop_item({
        "id":          "shield",
        "name":        "Shield",
        "emoji":       "🛡️",
        "description": "A sturdy wooden shield. +2 AC.",
        "price":       30,
        "max_qty":     1,
        "tier":        "common",
    })
