from DND.DungeonMaster.effects import Flag, Message, Modify, Status


def register(api):

    api.define_damage_type("lightning", label="Lightning", icon="⚡")

    api.define_status(
        "storm_stunned",
        label="Storm Stunned",
        icon="⚡",
        effects={
            "enemy_atk_penalty": 4,
            "enemy_ac_penalty":  2,
            "clears_on_turn":    True,
        },
    )

    def _storm_breaker_on_hit(ctx):
        if ctx.has_flag("storm_breaker_lightning_used"):
            return []
        n    = ctx.roll("1d4")
        save = ctx.roll("1d20")
        out  = [
            Modify("damage", add=n, damage_type="lightning"),
            Flag("storm_breaker_lightning_used", True),
            Message(f"⚡ Storm Breaker crackles — +{n} lightning damage!"),
        ]
        if save < 12:
            out += [
                Status("storm_stunned", 1),
                Message(f"⚡ The enemy fails their DEX save ({save}) — stunned! (−4 ATK, −2 AC this round)"),
            ]
        else:
            out.append(Message(f"The enemy weathers the shock (save {save})."))
        return out

    api.add_item({
        "id":          "storm_breaker",
        "name":        "Storm Breaker",
        "emoji":       "🔨",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "strength",
        "dmg":         "2d6",
        "handed":      2,
        "sell":        400,
        "tier":        "epic",
        "description": "A hammer as mighty as the god of thunder, wield it with worthiness.",
        "on_hit":      _storm_breaker_on_hit,
    })

    api.add_shop_item({
        "id":          "storm_breaker",
        "name":        "Storm Breaker",
        "emoji":       "🔨",
        "description": "A hammer as mighty as the god of thunder. Once per combat: +1d4 ⚡ lightning + stun chance (DEX DC 12).",
        "price":       800,
        "max_qty":     1,
        "tier":        "epic",
    })

    def _chain_lightning(ctx):
        if ctx.player.char_class != "wizard" or ctx.turn.ability_id != "chain_lightning": return []
        lv   = ctx.player.level
        dice = 6 + (lv >= 7)
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

    # Registered as a DLC spell — wizard picks this up automatically via api.add_spell().
    # No need to edit wizard/variables.py when adding new campaign spells.
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

    # Campaign-only drop — not sold in the shop.
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
