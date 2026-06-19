from DND.DungeonMaster.effects import BonusAttack, Flag, Heal, Message, Modify, Status


def register(api):

    # ── Statuses ──────────────────────────────────────────────────────────────
    api.define_status("ensnared",       label="Ensnared",       icon="🕸️",
                      effects={"enemy_ac_penalty": 2, "enemy_atk_penalty": 2, "clears_on_turn": True})
    api.define_status("hail_primed",    label="Hail Ready",     icon="🌧️",
                      effects={"clears_on_hit": True})
    api.define_status("vanished",       label="Vanished",       icon="👻",
                      effects={"damage_mult": 0.5, "clears_on_take_hit": True})
    api.define_status("beast_guarded",  label="Beast Guard",    icon="🐺",
                      effects={"damage_mult": 0.5, "clears_on_take_hit": True})

    # ── Damage types ──────────────────────────────────────────────────────────
    api.define_damage_type("piercing",  label="Piercing",  icon="🏹")
    api.define_damage_type("radiant",   label="Radiant",   icon="✨")

    # ── Helper ────────────────────────────────────────────────────────────────
    def _is(ctx, ability_id):
        return (ctx.player.char_class == "ranger"
                and ctx.turn.ability_id == ability_id)

    # ── Ability handlers ──────────────────────────────────────────────────────

    def _hunters_mark(ctx):
        if not _is(ctx, "hunters_mark"): return []
        return [Flag("hunters_mark_active", True),
                Message("Hunter's Mark activated — +1d6 on every hit!")]

    def _cure_wounds(ctx):
        if not _is(ctx, "cure_wounds"): return []
        lv = ctx.player.level
        slot = 1 + (lv >= 5) + (lv >= 9) + (lv >= 13) + (lv >= 17)
        n = sum(ctx.roll("1d8") for _ in range(slot))
        bonus = ctx.player.stats.get("mods", {}).get("wisdom", 0)
        total = n + bonus
        return [Heal(total), Message(f"Cure Wounds restores {total} HP!")]

    def _ensnaring_strike(ctx):
        if not _is(ctx, "ensnaring_strike"): return []
        return [Flag("ensnaring_primed", True),
                Message("Ensnaring Strike primed — next hit will restrain the enemy!")]

    def _hail_of_thorns(ctx):
        if not _is(ctx, "hail_of_thorns"): return []
        return [Flag("hail_primed", True),
                Message("Hail of Thorns primed — next hit explodes into a thorn burst!")]

    def _vanish(ctx):
        if not _is(ctx, "vanish"): return []
        return [Status("vanished", 1),
                Message("Vanish! You fade into shadow — next hit taken is halved.")]

    def _volley(ctx):
        if not (_is(ctx, "volley") and ctx.player.subclass == "hunter"): return []
        return [BonusAttack(), BonusAttack(),
                Message("Volley — you rain arrows in every direction!")]

    def _beast_protect(ctx):
        if not (_is(ctx, "beast_protect") and ctx.player.subclass == "beast_master"): return []
        return [Status("beast_guarded", 1),
                Message("Companion interception — your beast shields the next hit!")]

    # ── Passive hooks ─────────────────────────────────────────────────────────

    def _hunters_mark_dmg(ctx):
        """Add 1d6 on every hit while hunter's mark is active."""
        if ctx.player.char_class != "ranger": return []
        if not ctx.has_flag("hunters_mark_active"): return []
        n = ctx.roll("1d6")
        return [Modify("damage", add=n), Message(f"Hunter's Mark: +{n}!")]

    def _ensnaring_hit(ctx):
        """Apply ensnare on hit when the primed flag is up."""
        if ctx.player.char_class != "ranger": return []
        if not ctx.has_flag("ensnaring_primed"): return []
        return [Status("ensnared", 1), Flag("ensnaring_primed", False),
                Message("Ensnaring Strike — the enemy is restrained! AC & ATK -2 next round.")]

    def _hail_burst(ctx):
        """On hit when hail_primed: burst of piercing damage."""
        if ctx.player.char_class != "ranger": return []
        if not ctx.has_flag("hail_primed"): return []
        n = ctx.roll("1d10")
        return [Modify("damage", add=n, damage_type="piercing"),
                Flag("hail_primed", False),
                Message(f"Hail of Thorns explodes! +{n} piercing damage!")]

    def _extra_attack(ctx):
        if ctx.player.char_class != "ranger" or ctx.player.level < 5: return []
        return [BonusAttack()]

    def _colossus_slayer(ctx):
        """Hunter Lv 3: +1d8 when the enemy is wounded (below max HP)."""
        if ctx.player.char_class != "ranger" or ctx.player.subclass != "hunter": return []
        if ctx.player.level < 3: return []
        if ctx.enemy.hp >= ctx.enemy.max_hp: return []
        n = ctx.roll("1d8")
        return [Modify("damage", add=n), Message(f"Colossus Slayer: +{n} against the wounded foe!")]

    def _favored_enemy(ctx):
        """All rangers Lv 1: +2 damage against favored enemy type (always applies for simplicity)."""
        if ctx.player.char_class != "ranger" or ctx.player.level < 1: return []
        fav = getattr(ctx.player, "favored_enemy", None)
        if not fav: return []
        enemy_name = ctx.enemy.name.lower()
        if not any(kw in enemy_name for kw in FAVORED_ENEMY_KEYWORDS.get(fav, [])):
            return []
        return [Modify("damage", add=2), Message(f"Favored Enemy bonus: +2 vs {fav}!")]

    api.on("on_ability_use", _hunters_mark)
    api.on("on_ability_use", _cure_wounds)
    api.on("on_ability_use", _ensnaring_strike)
    api.on("on_ability_use", _hail_of_thorns)
    api.on("on_ability_use", _vanish)
    api.on("on_ability_use", _volley)
    api.on("on_ability_use", _beast_protect)
    api.on("on_damage_roll", _hunters_mark_dmg)
    api.on("on_damage_roll", _colossus_slayer)
    api.on("on_damage_roll", _favored_enemy)
    api.on("on_hit",         _ensnaring_hit)
    api.on("on_hit",         _hail_burst)
    api.on("on_turn_start",  _extra_attack)

    # ── Favored enemy keyword map ──────────────────────────────────────────────

    FAVORED_ENEMY_KEYWORDS = {
        "beasts":       ["bear", "wolf", "boar", "giant rat", "lion", "tiger"],
        "undead":       ["skeleton", "zombie", "ghoul", "vampire", "specter", "wraith"],
        "humanoids":    ["bandit", "goblin", "orc", "cultist", "thug", "pirate"],
        "monstrosities":["manticore", "minotaur", "medusa", "harpy", "basilisk"],
        "dragons":      ["dragon", "wyrm", "wyvern"],
        "fiends":       ["demon", "devil", "imp", "balor"],
    }

    # ── Class registration ────────────────────────────────────────────────────

    api.add_class({
        "id":           "ranger",
        "name":         "Ranger",
        "emoji":        "🏹",
        "hit_die":      10,
        "armor":        5,
        "primary_stat": "dexterity",
        "weapon_profs": ["simple", "martial"],
        "armor_profs":  ["light", "medium", "shields"],
        "saving_throws":["strength", "dexterity"],
        "start_items":  ["longbow", "shortsword"],
        "features": [
            {"level":  1, "name": "Favored Enemy",
             "desc": "Choose a creature type. +2 damage vs that type, advantage on tracking."},
            {"level":  1, "name": "Natural Explorer",
             "desc": "Double proficiency bonus on INT/WIS checks in favored terrain."},
            {"level":  2, "name": "Fighting Style",
             "desc": "Archery (+2 ranged ATK), Defense (+1 AC), or Two-Weapon Fighting."},
            {"level":  2, "name": "Spellcasting",
             "desc": "Spell slots unlock at Lv 2. Spell level scales with ranger level."},
            {"level":  3, "name": "Ranger Archetype",
             "desc": "Choose Hunter or Beast Master."},
            {"level":  3, "name": "Primeval Awareness",
             "desc": "Spend a spell slot to sense creature types within 1 mile."},
            {"level":  5, "name": "Extra Attack",
             "desc": "Attack twice whenever you take the Attack action."},
            {"level": 11, "name": "Hide in Plain Sight",
             "desc": "+10 to Stealth checks while motionless in natural terrain."},
        ],
        "abilities": [
            {"id": "hunters_mark",      "name": "Hunter's Mark",      "label": "🎯 Hunter's Mark",
             "action": "bonus", "level_req": 1, "once_per": None, "handler": _hunters_mark,
             "desc": "Mark a target — +1d6 damage on every hit until end of combat."},
            {"id": "cure_wounds",       "name": "Cure Wounds",        "label": "💚 Cure Wounds",
             "action": "action", "level_req": 2, "once_per": None, "handler": _cure_wounds,
             "desc": "Touch: heal 1d8 + WIS mod per spell slot level."},
            {"id": "ensnaring_strike",  "name": "Ensnaring Strike",   "label": "🕸️ Ensnaring Strike",
             "action": "bonus", "level_req": 2, "once_per": None, "handler": _ensnaring_strike,
             "desc": "Next hit: roots the enemy (AC & ATK -2 for one round)."},
            {"id": "hail_of_thorns",    "name": "Hail of Thorns",     "label": "🌧️ Hail of Thorns",
             "action": "bonus", "level_req": 2, "once_per": None, "handler": _hail_of_thorns,
             "desc": "Next ranged hit: deals +1d10 piercing in a burst."},
            {"id": "vanish",            "name": "Vanish",             "label": "👻 Vanish",
             "action": "bonus", "level_req": 14, "once_per": None, "handler": _vanish,
             "desc": "Halve the damage of the next hit you take."},
            {"id": "volley",            "name": "Volley",             "label": "🏹 Volley",
             "action": "action", "level_req": 11, "once_per": None, "handler": _volley,
             "desc": "Hunter: fire into a cluster — 2 bonus ranged attacks."},
            {"id": "beast_protect",     "name": "Beast Protect",      "label": "🐺 Beast Protect",
             "action": "bonus", "level_req": 7, "once_per": None, "handler": _beast_protect,
             "desc": "Beast Master: companion intercepts — halves the next hit you take."},
        ],
        "subclasses": {
            "hunter": {
                "abilities": ["volley"],
                "desc": "Colossus Slayer (+1d8 vs wounded), Volley (11+), Whirlwind Attack (11+).",
            },
            "beast_master": {
                "abilities": ["beast_protect"],
                "desc": "Ranger's Companion bonds with a beast; it acts and protects you in combat.",
            },
        },
        "level_choices": {
            ("ranger", 1): {
                "key": "favored_enemy", "prompt": "Choose your Favored Enemy type:",
                "options": [
                    {"id": "beasts",        "label": "Beasts",        "desc": "+2 dmg vs bears, wolves, boars, etc."},
                    {"id": "undead",        "label": "Undead",        "desc": "+2 dmg vs skeletons, zombies, vampires, etc."},
                    {"id": "humanoids",     "label": "Humanoids",     "desc": "+2 dmg vs bandits, goblins, orcs, etc."},
                    {"id": "monstrosities", "label": "Monstrosities", "desc": "+2 dmg vs manticores, minotaurs, etc."},
                ],
            },
            ("ranger", 2): {
                "key": "fighting_style", "prompt": "Choose your Fighting Style:",
                "options": [
                    {"id": "archery",             "label": "Archery",             "desc": "+2 to attack rolls with ranged weapons."},
                    {"id": "defense",             "label": "Defense",             "desc": "+1 AC while wearing armor."},
                    {"id": "two_weapon_fighting", "label": "Two-Weapon Fighting", "desc": "Add ability modifier to off-hand attack."},
                ],
            },
            ("ranger", 3): {
                "key": "subclass", "prompt": "Choose your Ranger Archetype:",
                "options": [
                    {"id": "hunter",      "label": "Hunter",      "desc": "Colossus Slayer, Volley — the relentless predator."},
                    {"id": "beast_master","label": "Beast Master","desc": "Ranger's Companion — fight alongside a bonded beast."},
                ],
            },
        },
        "favored_enemy_keywords": FAVORED_ENEMY_KEYWORDS,
    })
