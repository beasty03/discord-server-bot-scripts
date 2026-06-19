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
