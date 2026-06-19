from DND.DungeonMaster.effects import BonusAttack, Flag, Heal, Message, Modify, Status


def register(api):

    # ── Statuses ──────────────────────────────────────────────────────────────
    api.define_status("gwm_primed",   label="Great Weapon",  icon="⚔️",
                      effects={"damage_mult": 1.0, "clears_on_hit": True})

    # ── Passive feat handlers ─────────────────────────────────────────────────

    def _alert(ctx):
        """Alert feat: +5 to initiative (modelled as +5 to first attack roll of combat)."""
        if ctx.player.race != "human": return []
        feat = ctx.player.stats.get("feat")
        if feat != "alert": return []
        if ctx.has_flag("alert_used"): return []
        return [Modify("attack_roll", add=5), Flag("alert_used", True),
                Message("Alert! +5 initiative — you strike first!")]

    def _tough(ctx):
        """Tough feat: +2 max HP per level (represented as heal on level-up)."""
        if ctx.player.race != "human": return []
        feat = ctx.player.stats.get("feat")
        if feat != "tough": return []
        bonus = ctx.player.level * 2
        return [Heal(bonus), Message(f"Tough: {bonus} extra HP from this feat!")]

    def _sharpshooter(ctx):
        """Sharpshooter feat: ranged attacks ignore cover (+2 damage on ranged hits)."""
        if ctx.player.race != "human": return []
        feat = ctx.player.stats.get("feat")
        if feat != "sharpshooter": return []
        if ctx.player.stats.get("weapon_type") not in ("ranged", None): return []
        return [Modify("damage", add=2), Message("Sharpshooter: +2 ranged damage!")]

    def _gwm(ctx):
        """Great Weapon Master: on a crit or kill, bonus attack."""
        if ctx.player.race != "human": return []
        feat = ctx.player.stats.get("feat")
        if feat != "great_weapon_master": return []
        if not (ctx.turn.is_crit or ctx.has_flag("enemy_killed")): return []
        return [BonusAttack(), Message("Great Weapon Master: bonus attack after crit!")]

    api.on("on_combat_start", _alert,       priority=10)
    api.on("on_damage_roll",  _sharpshooter)
    api.on("on_hit",          _gwm)
    api.on("on_level_up",     _tough)

    # ── Race registration ─────────────────────────────────────────────────────

    api.add_race({
        "id":    "human",
        "name":  "Human",
        "emoji": "🧑",
        "stat_bonuses": {
            "strength":     1,
            "dexterity":    1,
            "constitution": 1,
            "intelligence": 1,
            "wisdom":       1,
            "charisma":     1,
        },
        "traits": [
            {"name": "Versatile",
             "desc": "+1 to every ability score, reflecting humanity's adaptability."},
            {"name": "Extra Language",
             "desc": "You can speak, read, and write one extra language of your choice."},
            {"name": "Feat",
             "desc": "Choose one feat at character creation: Alert, Tough, Sharpshooter, or Great Weapon Master."},
        ],
        "level_choices": {
            ("human", 1): {
                "key": "feat", "prompt": "Choose your starting Human Feat:",
                "options": [
                    {"id": "alert",               "label": "Alert",
                     "desc": "+5 to initiative — you are never surprised and can't be flanked."},
                    {"id": "tough",               "label": "Tough",
                     "desc": "+2 max HP per level (retroactive), making you much hardier."},
                    {"id": "sharpshooter",        "label": "Sharpshooter",
                     "desc": "+2 damage on ranged attacks; ignore half and three-quarters cover."},
                    {"id": "great_weapon_master", "label": "Great Weapon Master",
                     "desc": "On a crit or when you drop a foe, make one bonus melee attack."},
                ],
            },
        },
    })
