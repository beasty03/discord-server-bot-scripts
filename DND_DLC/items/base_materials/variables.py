def register(api):

    api.add_item({
        "id":          "herb",
        "name":        "Herb",
        "emoji":       "🌿",
        "slot":        "material",
        "tier":        "common",
        "sell":        3,
        "description": "A useful herb for crafting healing items.",
    })

    api.add_item({
        "id":          "leather_scrap",
        "name":        "Leather Scrap",
        "emoji":       "🪶",
        "slot":        "material",
        "tier":        "uncommon",
        "sell":        5,
        "description": "A piece of tough leather, useful for crafting.",
    })

    api.add_item({
        "id":          "arcane_shard",
        "name":        "Arcane Shard",
        "emoji":       "💎",
        "slot":        "material",
        "tier":        "rare",
        "sell":        15,
        "description": "A fragment of crystallized magical energy. Used in advanced crafting.",
    })
