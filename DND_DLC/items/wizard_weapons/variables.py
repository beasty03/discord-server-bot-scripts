from DND.DungeonMaster.effects import Message, Modify

# All wizard ability IDs — keeps the hook from firing on normal attacks
_WIZARD_ABILITY_IDS = frozenset({
    "fire_bolt", "ray_of_frost", "acid_splash",
    "magic_missile", "burning_hands", "thunderwave", "mirror_image",
    "scorching_ray", "lightning_bolt", "blight",
})
_CANTRIP_ABILITY_IDS = frozenset({"fire_bolt", "ray_of_frost", "acid_splash", "magic_missile"})
_FIRE_SPELL_IDS      = frozenset({"fire_bolt", "burning_hands", "scorching_ray"})


def register(api):

    def _wizard_weapon_passive(ctx):
        if ctx.player.char_class != "wizard": return []
        if ctx.turn.ability_id not in _WIZARD_ABILITY_IDS: return []
        equipped_ids = {i.get("id") for i in ctx.player.equipped}
        lv = ctx.player.level

        if "archmage_staff" in equipped_ids and lv >= 10:
            n = ctx.roll("1d6")
            return [Modify("damage", add=n, damage_type="force"),
                    Message(f"🔮 Archmage Staff: +{n} force!")]

        if "staff_of_power" in equipped_ids and lv >= 6:
            n = ctx.roll("1d4")
            return [Modify("damage", add=n, damage_type="force"),
                    Message(f"⚡ Staff of Power: +{n} force!")]

        if "wand_of_flames" in equipped_ids and lv >= 3:
            if ctx.turn.ability_id in _FIRE_SPELL_IDS:
                n = ctx.roll("1d4")
                return [Modify("damage", add=n, damage_type="fire"),
                        Message(f"🔥 Wand of Flames: +{n} fire!")]
            return []

        if "wand_of_cantrips" in equipped_ids and lv >= 3:
            if ctx.turn.ability_id in _CANTRIP_ABILITY_IDS:
                n = ctx.roll("1d4")
                return [Modify("damage", add=n, damage_type="force"),
                        Message(f"✨ Wand of Cantrips: +{n}!")]
            return []

        if "oak_wand" in equipped_ids:
            return [Modify("damage", add=1, damage_type="force"),
                    Message("🪄 Oak Wand: +1 force!")]

        return []

    api.on("on_damage_roll", _wizard_weapon_passive)

    # ── Spellbooks (offhand) ──────────────────────────────────────────────────
    api.add_item({
        "id":                 "spellbook",
        "name":               "Spellbook",
        "emoji":              "📖",
        "slot":               "offhand",
        "wizard_spell_slots": 4,
        "tier":               "uncommon",
        "sell":               50,
        "description":        "A leather-bound book for recording magical formulae. Prepare up to 4 spells.",
    })
    api.add_item({
        "id":                 "tome_of_many_spells",
        "name":               "Tome of Many Spells",
        "emoji":              "📚",
        "slot":               "offhand",
        "wizard_spell_slots": 6,
        "tier":               "rare",
        "sell":               150,
        "description":        "A thick grimoire brimming with arcane knowledge. Prepare up to 6 spells.",
    })
    api.add_item({
        "id":                 "grand_grimoire",
        "name":               "Grand Grimoire",
        "emoji":              "🔮",
        "slot":               "offhand",
        "wizard_spell_slots": 8,
        "tier":               "epic",
        "sell":               400,
        "description":        "An ancient tome of immense power. Prepare up to 8 spells.",
    })

    # ── Wizard weapons (main hand) ────────────────────────────────────────────
    api.add_item({
        "id":          "oak_wand",
        "name":        "Oak Wand",
        "emoji":       "🪄",
        "slot":        "weapon",
        "weapon_type": "simple",
        "ability":     "intelligence",
        "dmg":         "1d4",
        "handed":      1,
        "tier":        "common",
        "sell":        10,
        "description": "A simple wand carved from oak. +1 force damage on any spell.",
    })
    api.add_item({
        "id":          "wand_of_flames",
        "name":        "Wand of Flames",
        "emoji":       "🔥",
        "slot":        "weapon",
        "weapon_type": "simple",
        "ability":     "intelligence",
        "dmg":         "1d4",
        "handed":      1,
        "tier":        "uncommon",
        "sell":        60,
        "description": "A wand imbued with fire. +1d4 fire damage on fire spells (Lv 3+).",
    })
    api.add_item({
        "id":          "wand_of_cantrips",
        "name":        "Wand of Cantrips",
        "emoji":       "✨",
        "slot":        "weapon",
        "weapon_type": "simple",
        "ability":     "intelligence",
        "dmg":         "1d4",
        "handed":      1,
        "tier":        "uncommon",
        "sell":        60,
        "description": "A wand that amplifies cantrip energy. +1d4 damage on cantrips (Lv 3+).",
    })
    api.add_item({
        "id":          "staff_of_power",
        "name":        "Staff of Power",
        "emoji":       "⚡",
        "slot":        "weapon",
        "weapon_type": "simple",
        "ability":     "intelligence",
        "dmg":         "1d6",
        "handed":      1,
        "tier":        "rare",
        "sell":        200,
        "description": "A crackling staff of arcane energy. +1d4 force damage on any spell (Lv 6+).",
    })
    api.add_item({
        "id":          "archmage_staff",
        "name":        "Archmage Staff",
        "emoji":       "🔮",
        "slot":        "weapon",
        "weapon_type": "simple",
        "ability":     "intelligence",
        "dmg":         "1d8",
        "handed":      1,
        "tier":        "epic",
        "sell":        500,
        "description": "The staff of a master archmage. +1d6 force damage on any spell (Lv 10+).",
    })
