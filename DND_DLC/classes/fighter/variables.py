from DND.DungeonMaster.effects import BonusAttack, Flag, Heal, Message, Modify, Status


def register(api):

    # ── Damage types ──────────────────────────────────────────────────────────
    api.define_damage_type("fire",   label="Fire",   icon="🔥")
    api.define_damage_type("force",  label="Force",  icon="✨")

    # ── Statuses (carry their mechanical effects for the engine to apply) ─────
    api.define_status("tripped",      label="Tripped",      icon="🦵",
                      effects={"enemy_ac_penalty": 2, "clears_on_turn": True})
    api.define_status("disarmed",     label="Disarmed",     icon="🔓",
                      effects={"enemy_atk_penalty": 2, "clears_on_turn": True})
    api.define_status("menaced",      label="Menaced",      icon="😤",
                      effects={"enemy_atk_penalty": 2, "clears_on_turn": True})
    api.define_status("ek_shielded",  label="EK Shield",    icon="🛡️",
                      effects={"player_ac_bonus": 5, "clears_on_take_hit": True})
    api.define_status("riposte_ready", label="Riposte",     icon="🔄",
                      effects={"clears_on_turn": True})

    # ── Ability handlers ──────────────────────────────────────────────────────

    def _is(ctx, ability_id):
        return (ctx.player.char_class == "fighter"
                and ctx.turn.ability_id == ability_id)

    def _second_wind(ctx):
        if not _is(ctx, "second_wind"): return []
        n = ctx.roll("1d10") + ctx.player.level
        return [Heal(n), Message(f"Second Wind restores {n} HP!")]

    def _action_surge(ctx):
        if not _is(ctx, "action_surge"): return []
        return [BonusAttack(), BonusAttack(), Message("Action Surge — extra attacks!")]

    # Battle Master maneuvers
    def _bm_precision(ctx):
        if not _is(ctx, "bm_precision"): return []
        n = ctx.roll("1d8")
        return [Modify("attack_roll", add=n), Message(f"Precision Attack: +{n} to hit!")]

    def _bm_trip(ctx):
        if not _is(ctx, "bm_trip"): return []
        n = ctx.roll("1d8")
        return [Modify("damage", add=n), Status("tripped", 1),
                Message(f"Trip Attack: +{n} dmg, enemy AC -2 next round!")]

    def _bm_disarm(ctx):
        if not _is(ctx, "bm_disarm"): return []
        n = ctx.roll("1d8")
        return [Modify("damage", add=n), Status("disarmed", 1),
                Message(f"Disarming Strike: +{n} dmg, enemy ATK -2 next round!")]

    def _bm_riposte(ctx):
        if not _is(ctx, "bm_riposte"): return []
        return [Status("riposte_ready", 1),
                Message("Riposte primed — counter-attack on the next enemy miss!")]

    def _bm_menacing(ctx):
        if not _is(ctx, "bm_menacing"): return []
        n = ctx.roll("1d8")
        return [Modify("damage", add=n), Status("menaced", 1),
                Message(f"Menacing Attack: +{n} dmg, enemy ATK -2 next round!")]

    # Eldritch Knight abilities
    def _fire_bolt(ctx):
        if not _is(ctx, "fire_bolt"): return []
        lv = ctx.player.level
        dice = 1 + (lv >= 5) + (lv >= 11) + (lv >= 17)
        dmg  = sum(ctx.roll("1d10") for _ in range(dice))
        return [Modify("damage", add=dmg, damage_type="fire"),
                Message(f"Fire Bolt: {dmg} fire damage!")]

    def _ek_shield(ctx):
        if not _is(ctx, "ek_shield"): return []
        return [Status("ek_shielded", 1), Message("Shield: +5 AC vs the next hit!")]

    def _war_magic_atk(ctx):
        if not _is(ctx, "war_magic_atk"): return []
        return [BonusAttack(), Message("War Magic: bonus weapon attack!")]

    # ── Passive hooks ─────────────────────────────────────────────────────────

    def _extra_attack(ctx):
        if ctx.player.char_class != "fighter" or ctx.player.level < 5:
            return []
        return [BonusAttack()]

    api.on("on_ability_use", _second_wind)
    api.on("on_ability_use", _action_surge)
    api.on("on_ability_use", _bm_precision)
    api.on("on_ability_use", _bm_trip)
    api.on("on_ability_use", _bm_disarm)
    api.on("on_ability_use", _bm_riposte)
    api.on("on_ability_use", _bm_menacing)
    api.on("on_ability_use", _fire_bolt)
    api.on("on_ability_use", _ek_shield)
    api.on("on_ability_use", _war_magic_atk)
    api.on("on_turn_start",  _extra_attack)

    # ── Class registration ────────────────────────────────────────────────────

    api.add_class({
        "id":            "fighter",
        "name":          "Fighter",
        "emoji":         "⚔️",
        "hit_die":       10,
        "armor":         6,
        "primary_stat":  "strength",
        "weapon_profs":  ["simple", "martial"],
        "armor_profs":   ["light", "medium", "heavy", "shields"],
        "saving_throws": ["strength", "constitution"],
        "start_items":   ["longsword", "shield"],
        "features": [
            {"level":  1, "name": "Fighting Style",
             "desc": "Choose a combat specialty: Archery (+2 ranged ATK), Defense (+1 AC), Dueling (+2 melee dmg), Great Weapon Fighting (reroll 1s & 2s), Two-Weapon Fighting (offhand bonus attack), Protection (shield ally)."},
            {"level":  1, "name": "Second Wind",
             "desc": "Bonus action: regain 1d10 + level HP (once per combat)."},
            {"level":  2, "name": "Action Surge",
             "desc": "Take one extra attack action on your turn (once per combat; twice at Lv 17)."},
            {"level":  3, "name": "Martial Archetype",
             "desc": "Choose your subclass: Champion, Battle Master, or Eldritch Knight."},
            {"level":  4, "name": "Ability Score Improvement", "desc": "+2 to one ability, or +1 to two."},
            {"level":  5, "name": "Extra Attack",   "desc": "Attack twice whenever you take the Attack action."},
            {"level":  9, "name": "Indomitable",    "desc": "When reduced to 0 HP, roll CON save — on success, survive at 1 HP (1× per combat)."},
            {"level": 11, "name": "Extra Attack (2)", "desc": "Attack three times whenever you take the Attack action."},
            {"level": 20, "name": "Extra Attack (3)", "desc": "Attack four times whenever you take the Attack action."},
        ],
        "abilities": [
            {"id": "second_wind",  "name": "Second Wind",  "label": "🌬️ Second Wind",
             "action": "bonus",  "level_req": 1,  "once_per": "combat",
             "handler": _second_wind,
             "desc": "Heal 1d10 + fighter level HP (bonus action, once per combat)."},
            {"id": "action_surge", "name": "Action Surge", "label": "⚡ Action Surge",
             "action": "action", "level_req": 2,  "once_per": "combat",
             "handler": _action_surge,
             "desc": "Extra attacks this round (once per combat)."},
            # Battle Master
            {"id": "bm_precision", "name": "Precision Attack",  "label": "🎯 Precision Attack",
             "action": "bonus",  "level_req": 3,  "once_per": None,
             "handler": _bm_precision,
             "desc": "Spend 1 Superiority Die — add the result to your next attack roll."},
            {"id": "bm_trip",      "name": "Trip Attack",       "label": "🦵 Trip Attack",
             "action": "bonus",  "level_req": 3,  "once_per": None,
             "handler": _bm_trip,
             "desc": "Spend 1 Superiority Die — +die damage and enemy AC -2 next round."},
            {"id": "bm_disarm",    "name": "Disarming Strike",  "label": "🔓 Disarming Strike",
             "action": "bonus",  "level_req": 3,  "once_per": None,
             "handler": _bm_disarm,
             "desc": "Spend 1 Superiority Die — +die damage and enemy ATK -2 next round."},
            {"id": "bm_riposte",   "name": "Riposte",           "label": "🔄 Riposte",
             "action": "bonus",  "level_req": 3,  "once_per": None,
             "handler": _bm_riposte,
             "desc": "Spend 1 Superiority Die — counter-attack when the enemy misses you."},
            {"id": "bm_menacing",  "name": "Menacing Attack",   "label": "😤 Menacing Attack",
             "action": "bonus",  "level_req": 3,  "once_per": None,
             "handler": _bm_menacing,
             "desc": "Spend 1 Superiority Die — +die damage and enemy ATK -2 next round."},
            # Eldritch Knight
            {"id": "fire_bolt",    "name": "Fire Bolt",         "label": "🔥 Fire Bolt",
             "action": "action", "level_req": 3,  "once_per": None,
             "handler": _fire_bolt,
             "desc": "Auto-hit cantrip — 1d10 fire; scales to 4d10 at Lv 17."},
            {"id": "ek_shield",    "name": "Shield",            "label": "🛡️ Shield",
             "action": "bonus",  "level_req": 3,  "once_per": "combat",
             "handler": _ek_shield,
             "desc": "+5 AC vs the next hit (bonus action, once per combat)."},
            {"id": "war_magic_atk","name": "War Magic Strike",  "label": "⚔️ War Magic Strike",
             "action": "bonus",  "level_req": 7,  "once_per": None,
             "handler": _war_magic_atk,
             "desc": "After Fire Bolt, make one bonus weapon attack (Lv 7+)."},
        ],
        "subclasses": {
            "champion":       {"abilities": [], "desc": "Expanded crit range (19–20 at Lv 3, 18–20 at Lv 15)."},
            "battle_master":  {"abilities": ["bm_precision","bm_trip","bm_disarm","bm_riposte","bm_menacing"],
                               "desc": "4–6 Superiority Dice (d8→d12) and five tactical maneuvers."},
            "eldritch_knight":{"abilities": ["fire_bolt","ek_shield","war_magic_atk"],
                               "desc": "Fire Bolt cantrip, Shield spell, War Magic bonus attack at Lv 7."},
        },
        "level_choices": {
            ("fighter", 1): {
                "key": "fighting_style", "prompt": "Choose your Fighting Style:",
                "options": [
                    {"id": "archery",               "label": "Archery",               "desc": "+2 to attack rolls with ranged weapons."},
                    {"id": "defense",               "label": "Defense",               "desc": "+1 AC while wearing armor."},
                    {"id": "dueling",               "label": "Dueling",               "desc": "+2 damage wielding a one-handed melee weapon."},
                    {"id": "great_weapon_fighting", "label": "Great Weapon Fighting", "desc": "Reroll 1s and 2s on weapon damage dice."},
                    {"id": "two_weapon_fighting",   "label": "Two-Weapon Fighting",   "desc": "Add ability modifier to off-hand bonus attack."},
                    {"id": "protection",            "label": "Protection",            "desc": "Reduce damage to an adjacent ally by up to 3 (requires shield)."},
                ],
            },
            ("fighter", 3): {
                "key": "subclass", "prompt": "Choose your Martial Archetype:",
                "options": [
                    {"id": "champion",        "label": "Champion",        "desc": "Improved Critical (19–20); Superior Critical at Lv 15 (18–20)."},
                    {"id": "battle_master",   "label": "Battle Master",   "desc": "Superiority Dice + five tactical maneuvers."},
                    {"id": "eldritch_knight", "label": "Eldritch Knight", "desc": "Fire Bolt cantrip, Shield spell, War Magic bonus attack."},
                ],
            },
        },
        "favored_enemy_keywords": None,
    })
