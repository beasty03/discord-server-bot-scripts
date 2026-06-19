def register(api):

    api.add_item({
        "id":          "scroll_misty_step",
        "name":        "Scroll of Misty Step",
        "emoji":       "📜",
        "slot":        "spell_scroll",
        "teaches":     "misty_step",
        "tier":        "rare",
        "sell":        140,
        "description": "Permanently teaches a Wizard Misty Step. Wizard Lv 3+.",
    })
    api.add_shop_item({
        "id":          "scroll_misty_step",
        "name":        "Scroll of Misty Step",
        "emoji":       "📜",
        "description": "Permanently teaches a Wizard Misty Step (teleport, half damage from next hit). Wizard Lv 3+.",
        "price":       400,
        "max_qty":     1,
        "tier":        "rare",
    })

    api.add_item({
        "id":          "scroll_scorching_ray",
        "name":        "Scroll of Scorching Ray",
        "emoji":       "📜",
        "slot":        "spell_scroll",
        "teaches":     "scorching_ray",
        "tier":        "rare",
        "sell":        110,
        "description": "Permanently teaches a Wizard Scorching Ray. Wizard Lv 3+.",
    })
    api.add_shop_item({
        "id":          "scroll_scorching_ray",
        "name":        "Scroll of Scorching Ray",
        "emoji":       "📜",
        "description": "Permanently teaches a Wizard Scorching Ray (3 fire rays, 2d6 each). Wizard Lv 3+.",
        "price":       300,
        "max_qty":     1,
        "tier":        "rare",
    })
