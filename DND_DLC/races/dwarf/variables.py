from DND.DungeonMaster.effects import BonusAttack, Flag, Heal, Message, Modify, Status


def register(api):

    # ── Statuses ──────────────────────────────────────────────────────────────
    api.define_status("poison_resistant", label="Poison Resist", icon="☠️",
                      effects={"damage_mult": 0.5})

    # ── Passive handlers ──────────────────────────────────────────────────────

    def _poison_resistance(ctx):
        """Dwarven resilience: halve poison damage taken."""
        if ctx.player.race != "dwarf": return []
        if ctx.turn.damage_type != "poison": return []
        return [Status("poison_resistant", 1),
                Message("Dwarven Resilience: poison damage halved!")]

    def _stonecunning(ctx):
        """Stonecunning: advantage on History checks related to stonework (+4 to roll)."""
        if ctx.player.race != "dwarf": return []
        if ctx.turn.check_type not in ("history", "perception"): return []
        return [Modify("check_roll", add=4),
                Message("Stonecunning: +4 on stonework knowledge checks!")]

    def _dwarven_toughness(ctx):
        """Dwarven Toughness subrace: +1 HP per level gained."""
        if ctx.player.race != "dwarf": return []
        if ctx.player.subrace != "mountain": return []
        return [Heal(1), Message("Dwarven Toughness: +1 HP this level!")]

    def _battle_born(ctx):
        """Battle-born: advantage on first attack of combat (+3 to attack roll, once per combat)."""
        if ctx.player.race != "dwarf": return []
        if ctx.player.subrace != "mountain": return []
        if ctx.has_flag("battle_born_used"): return []
        return [Modify("attack_roll", add=3), Flag("battle_born_used", True),
                Message("Battle-Born: +3 to first attack of the fight!")]

    api.on("on_take_damage",  _poison_resistance)
    api.on("on_skill_check",  _stonecunning)
    api.on("on_level_up",     _dwarven_toughness)
    api.on("on_before_attack", _battle_born)

    # ── Race registration ─────────────────────────────────────────────────────

    api.add_race({
        "id":    "dwarf",
        "name":  "Dwarf",
        "emoji": "🪨",
        "stat_bonuses": {
            "constitution": 2,
            "strength":     1,
        },
        "traits": [
            {"name": "Dwarven Resilience",
             "desc": "Advantage on saving throws against poison; resistance to poison damage (halved)."},
            {"name": "Stonecunning",
             "desc": "+4 to History and Perception checks related to stonework and underground terrain."},
            {"name": "Darkvision",
             "desc": "See in dim light as bright light, and in darkness as dim light (60 ft)."},
            {"name": "Tool Proficiency",
             "desc": "Proficient with smith's tools, brewer's supplies, or mason's tools (your choice)."},
            {"name": "Combat Training",
             "desc": "Proficient with battleaxe, handaxe, light hammer, and warhammer."},
        ],
        "subraces": {
            "hill": {
                "stat_bonuses": {"wisdom": 1},
                "desc": "Hill Dwarf: +1 WIS, Dwarven Toughness (+1 max HP per level).",
            },
            "mountain": {
                "stat_bonuses": {"strength": 2},
                "desc": "Mountain Dwarf: +2 STR, armor proficiencies, Battle-Born combat advantage.",
            },
        },
        "level_choices": {
            ("dwarf", 1): {
                "key": "subrace", "prompt": "Choose your Dwarven subrace:",
                "options": [
                    {"id": "hill",     "label": "Hill Dwarf",     "desc": "+1 WIS and +1 max HP per level."},
                    {"id": "mountain", "label": "Mountain Dwarf", "desc": "+2 STR, light/medium armor proficiency, Battle-Born."},
                ],
            },
        },
    })
