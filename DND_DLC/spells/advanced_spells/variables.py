def register(api):
    from DND.DungeonMaster.effects import Message, Status

    api.define_status("misty_stepped", label="Misty Step", icon="💨",
                      effects={"damage_mult": 0.5, "clears_on_take_hit": True})

    def _misty_step(ctx):
        if ctx.player.char_class != "wizard" or ctx.turn.ability_id != "misty_step": return []
        if ctx.player.level < 3: return []
        return [Status("misty_stepped", 1),
                Message("💨 Misty Step — you vanish in silver mist! Half damage from the next hit.")]

    api.add_spell({
        "id":        "misty_step",
        "name":      "Misty Step",
        "emoji":     "💨",
        "label":     "💨 Misty Step",
        "action":    "bonus",
        "level_req": 3,
        "once_per":  "combat",
        "class":     "wizard",
        "handler":   _misty_step,
        "desc":      "Teleport in a flash of silver mist — half damage from the next hit taken.",
    })

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
