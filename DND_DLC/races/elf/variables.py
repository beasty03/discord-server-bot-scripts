def register(api):
    from DND.DungeonMaster.effects import BonusAttack, Flag, Heal, Message, Modify, Status

    # ── Statuses ──────────────────────────────────────────────────────────────
    api.define_status("charmed_resistant", label="Fey Ancestry", icon="🌿",
                      effects={"enemy_atk_penalty": 1})

    # ── Passive handlers ──────────────────────────────────────────────────────

    def _keen_senses_perception(ctx):
        """Keen Senses: +3 bonus on Perception skill checks."""
        if ctx.player.race != "elf": return []
        if ctx.turn.check_type not in ("perception", "insight"): return []
        return [Modify("check_roll", add=3),
                Message("Keen Senses: +3 on perception/insight!")]

    def _fey_ancestry(ctx):
        """Fey Ancestry: advantage vs charm effects — enemy ATK slightly reduced."""
        if ctx.player.race != "elf": return []
        if ctx.turn.damage_type != "psychic": return []
        return [Status("charmed_resistant", 1),
                Message("Fey Ancestry: you resist the charm!")]

    def _trance(ctx):
        """Trance: elves need only 4h of meditation — functionally, +1 HP on rest actions."""
        if ctx.player.race != "elf": return []
        return [Heal(1), Message("Elven Trance: you awaken fully refreshed, +1 HP recovered.")]

    def _high_elf_cantrip(ctx):
        """High Elf Lv 1 passive: +1 to all magical damage rolls (arcane affinity)."""
        if ctx.player.race != "elf" or ctx.player.subrace != "high_elf": return []
        spell_ids = {"fire_bolt","ray_of_frost","acid_splash","magic_missile",
                     "burning_hands","thunderwave","scorching_ray","lightning_bolt","blight"}
        if ctx.turn.ability_id not in spell_ids: return []
        return [Modify("damage", add=1), Message("Arcane Affinity: +1 spell damage!")]

    def _wood_elf_fleet(ctx):
        """Wood Elf: Fleet of Foot — in combat, always acts first (modelled as +2 ATK on first turn)."""
        if ctx.player.race != "elf" or ctx.player.subrace != "wood_elf": return []
        if ctx.has_flag("fleet_used"): return []
        return [Modify("attack_roll", add=2), Flag("fleet_used", True),
                Message("Fleet of Foot: +2 to first attack — swift as the wood!")]

    api.on("on_skill_check",  _keen_senses_perception)
    api.on("on_take_damage",  _fey_ancestry)
    api.on("on_ability_use",  _high_elf_cantrip)
    api.on("on_before_attack", _wood_elf_fleet)

    # ── Race registration ─────────────────────────────────────────────────────

    api.add_race({
        "id":    "elf",
        "name":  "Elf",
        "emoji": "🧝",
        "stat_bonuses": {
            "dexterity":    2,
            "intelligence": 1,
        },
        "traits": [
            {"name": "Keen Senses",
             "desc": "+3 to Perception and Insight checks — elves notice everything."},
            {"name": "Fey Ancestry",
             "desc": "Advantage on saving throws against being charmed; immune to magical sleep."},
            {"name": "Trance",
             "desc": "You meditate 4 hours instead of sleeping 8 — gain the same benefits."},
            {"name": "Darkvision",
             "desc": "See in dim light as bright light, and darkness as dim light (60 ft)."},
        ],
        "subraces": {
            "high_elf": {
                "stat_bonuses": {"intelligence": 1},
                "desc": "High Elf: +1 INT, one wizard cantrip, Arcane Affinity (+1 spell damage).",
            },
            "wood_elf": {
                "stat_bonuses": {"wisdom": 1},
                "desc": "Wood Elf: +1 WIS, Fleet of Foot (+2 ATK on first combat turn), Mask of the Wild.",
            },
            "dark_elf": {
                "stat_bonuses": {"charisma": 1},
                "desc": "Dark Elf (Drow): +1 CHA, superior darkvision (120 ft), Sunlight Sensitivity.",
            },
        },
        "level_choices": {
            ("elf", 1): {
                "key": "subrace", "prompt": "Choose your Elven subrace:",
                "options": [
                    {"id": "high_elf",  "label": "High Elf",  "desc": "+1 INT, arcane cantrip, +1 spell damage passive."},
                    {"id": "wood_elf",  "label": "Wood Elf",  "desc": "+1 WIS, +2 ATK on first turn each combat."},
                    {"id": "dark_elf",  "label": "Dark Elf",  "desc": "+1 CHA, superior darkvision (120 ft)."},
                ],
            },
        },
    })
