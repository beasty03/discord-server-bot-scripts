from DND.DungeonMaster.effects import Message, Modify, Status


def register(api):

    api.define_damage_type("fire", label="Fire", icon="🔥")

    api.define_status("counterspelled", label="Counterspelled", icon="🚫",
                      effects={"enemy_atk_penalty": 20, "clears_on_turn": True})

    def _fireball(ctx):
        if ctx.player.char_class != "wizard" or ctx.turn.ability_id != "fireball": return []
        lv   = ctx.player.level
        dice = 8 + 2 * (lv >= 7) + 2 * (lv >= 9)
        dmg  = sum(ctx.roll("1d6") for _ in range(dice))
        return [Modify("damage", add=dmg, damage_type="fire"),
                Message(f"🔥 Fireball — {dice}d6 = {dmg} fire damage!")]

    def _counterspell(ctx):
        if ctx.player.char_class != "wizard" or ctx.turn.ability_id != "counterspell": return []
        return [Status("counterspelled", 1),
                Message("🚫 Counterspell — the enemy's next action is disrupted! (−20 ATK this round)")]

    api.add_spell({
        "id":        "fireball",
        "name":      "Fireball",
        "emoji":     "🔥",
        "label":     "🔥 Fireball",
        "action":    "action",
        "level_req": 5,
        "once_per":  None,
        "class":     "wizard",
        "handler":   _fireball,
        "desc":      "8d6 fire in a roaring blast — scales to 10d6 at Lv 7, 12d6 at Lv 9.",
    })

    api.add_spell({
        "id":        "counterspell",
        "name":      "Counterspell",
        "emoji":     "🚫",
        "label":     "🚫 Counterspell",
        "action":    "bonus",
        "level_req": 5,
        "once_per":  "combat",
        "class":     "wizard",
        "handler":   _counterspell,
        "desc":      "Interrupt the enemy — −20 ATK on their next action (virtually guaranteed miss).",
    })

    api.add_item({
        "id":          "scroll_fireball",
        "name":        "Scroll of Fireball",
        "emoji":       "📜",
        "slot":        "spell_scroll",
        "teaches":     "fireball",
        "tier":        "epic",
        "sell":        280,
        "description": "Permanently teaches a Wizard the iconic Fireball spell. Wizard Lv 5+.",
    })
    api.add_shop_item({
        "id":          "scroll_fireball",
        "name":        "Scroll of Fireball",
        "emoji":       "📜",
        "description": "Permanently teaches a Wizard the iconic Fireball spell (8d6 fire). Wizard Lv 5+.",
        "price":       750,
        "max_qty":     1,
        "tier":        "epic",
    })

    api.add_item({
        "id":          "scroll_counterspell",
        "name":        "Scroll of Counterspell",
        "emoji":       "📜",
        "slot":        "spell_scroll",
        "teaches":     "counterspell",
        "tier":        "epic",
        "sell":        220,
        "description": "Permanently teaches a Wizard Counterspell. Wizard Lv 5+.",
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
