def register(api):

    api.add_item({
        "id":          "scroll_burning_hands",
        "name":        "Scroll of Burning Hands",
        "emoji":       "📜",
        "slot":        "spell_scroll",
        "teaches":     "burning_hands",
        "tier":        "common",
        "sell":        25,
        "description": "Teaches a Wizard the Burning Hands spell (3d6 fire cone).",
    })

    api.add_item({
        "id":          "scroll_thunderwave",
        "name":        "Scroll of Thunderwave",
        "emoji":       "📜",
        "slot":        "spell_scroll",
        "teaches":     "thunderwave",
        "tier":        "common",
        "sell":        25,
        "description": "Teaches a Wizard the Thunderwave spell (2d8+INT thunder, ATK debuff).",
    })

    api.add_item({
        "id":          "scroll_shield_spell",
        "name":        "Scroll of Shield",
        "emoji":       "📜",
        "slot":        "spell_scroll",
        "teaches":     "shield_spell",
        "tier":        "common",
        "sell":        25,
        "description": "Teaches a Wizard the Shield spell (+5 AC vs the next hit, bonus action).",
    })

    api.add_shop_item({
        "id":          "scroll_burning_hands",
        "name":        "Scroll of Burning Hands",
        "emoji":       "📜",
        "description": "Permanently teaches a Wizard Burning Hands (3d6 fire cone).",
        "price":       75,
        "max_qty":     1,
        "tier":        "common",
    })

    api.add_shop_item({
        "id":          "scroll_thunderwave",
        "name":        "Scroll of Thunderwave",
        "emoji":       "📜",
        "description": "Permanently teaches a Wizard Thunderwave (2d8+INT thunder, ATK debuff).",
        "price":       75,
        "max_qty":     1,
        "tier":        "common",
    })

    api.add_shop_item({
        "id":          "scroll_shield_spell",
        "name":        "Scroll of Shield",
        "emoji":       "📜",
        "description": "Permanently teaches a Wizard Shield (+5 AC vs the next hit, bonus action).",
        "price":       75,
        "max_qty":     1,
        "tier":        "common",
    })
