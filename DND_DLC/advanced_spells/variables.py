def register(api):

    api.add_shop_item({
        "id":          "scroll_misty_step",
        "name":        "Scroll of Misty Step",
        "emoji":       "📜",
        "description": "Permanently teaches a Wizard Misty Step (teleport, half damage from next hit). Wizard Lv 3+.",
        "price":       400,
        "max_qty":     1,
        "tier":        "rare",
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
