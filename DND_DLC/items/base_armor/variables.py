def register(api):

    api.add_item({
        "id":          "leather_armor",
        "name":        "Leather Armor",
        "emoji":       "🥋",
        "slot":        "armor",
        "ac_bonus":    2,
        "tier":        "common",
        "sell":        10,
        "description": "Lightweight armor. +2 AC.",
    })
    api.add_shop_item({
        "id":          "leather_armor",
        "name":        "Leather Armor",
        "emoji":       "🥋",
        "description": "Lightweight armor that doesn't restrict movement. +2 AC.",
        "price":       30,
        "max_qty":     1,
        "tier":        "common",
    })

    api.add_item({
        "id":          "chain_mail",
        "name":        "Chain Mail",
        "emoji":       "⚙️",
        "slot":        "armor",
        "ac_bonus":    4,
        "tier":        "uncommon",
        "sell":        30,
        "description": "Interlocked rings of metal. +4 AC.",
    })
    api.add_shop_item({
        "id":          "chain_mail",
        "name":        "Chain Mail",
        "emoji":       "⚙️",
        "description": "Interlocked rings of metal. +4 AC.",
        "price":       90,
        "max_qty":     1,
        "tier":        "uncommon",
    })
