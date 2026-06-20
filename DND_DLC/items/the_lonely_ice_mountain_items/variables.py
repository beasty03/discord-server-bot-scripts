def register(api):
    from DND.DungeonMaster.effects import Message, Modify

    # ── Shop listing for campaign drop ────────────────────────────────────────
    # storm_breaker is registered in campaigns/the_lonely_ice_mountain/variables.py

    api.add_shop_item({
        "id":          "storm_breaker",
        "name":        "Storm Breaker",
        "emoji":       "🔨",
        "description": "A hammer as mighty as the god of thunder. Once per combat: +1d4 ⚡ lightning + stun chance (DEX DC 12).",
        "price":       800,
        "max_qty":     1,
        "tier":        "epic",
    })

    # ── Chain Lightning spell (wizard content, not a campaign drop) ───────────

    api.define_damage_type("lightning", label="Lightning", icon="⚡")

    def _chain_lightning(ctx):
        if ctx.player.char_class != "wizard" or ctx.turn.ability_id != "chain_lightning":
            return []
        lv      = ctx.player.level
        dice    = 6 + (lv >= 7)
        primary = sum(ctx.roll("1d6") for _ in range(dice))
        out = [
            Modify("damage", add=primary, damage_type="lightning"),
            Message(f"⚡ Chain Lightning — {primary} lightning damage!"),
        ]
        save = ctx.roll("1d20")
        if save < 13:
            chain = sum(ctx.roll("1d6") for _ in range(3))
            out += [
                Modify("damage", add=chain, damage_type="lightning"),
                Message(f"⚡ The bolt chains! +{chain} lightning (DEX save {save} < 13)!"),
            ]
        else:
            out.append(Message(f"The chain fizzles (DEX save {save})."))
        return out

    api.add_spell({
        "id":        "chain_lightning",
        "name":      "Chain Lightning",
        "emoji":     "⚡",
        "label":     "⚡ Chain Lightning",
        "action":    "action",
        "level_req": 5,
        "once_per":  None,
        "class":     "wizard",
        "handler":   _chain_lightning,
        "desc":      "6d6 lightning — chains for +3d6 if enemy fails DC 13 DEX save. Scales at Lv 7.",
    })

    api.add_item({
        "id":          "scroll_chain_lightning",
        "name":        "Scroll of Chain Lightning",
        "emoji":       "📜",
        "slot":        "spell_scroll",
        "teaches":     "chain_lightning",
        "tier":        "epic",
        "sell":        300,
        "description": "Permanently teaches a Wizard Chain Lightning (6d6 lightning, chains on fail). Wizard Lv 5+.",
    })
