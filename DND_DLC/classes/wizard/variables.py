from DND.DungeonMaster.effects import BonusAttack, Flag, Heal, Message, Modify, Status


def register(api):

    # ── Damage types ──────────────────────────────────────────────────────────
    api.define_damage_type("fire",      label="Fire",      icon="🔥")
    api.define_damage_type("cold",      label="Cold",      icon="❄️")
    api.define_damage_type("lightning", label="Lightning", icon="⚡")
    api.define_damage_type("acid",      label="Acid",      icon="🧪")
    api.define_damage_type("force",     label="Force",     icon="✨")
    api.define_damage_type("necrotic",  label="Necrotic",  icon="💀")
    api.define_damage_type("radiant",   label="Radiant",   icon="🌟")
    api.define_damage_type("thunder",   label="Thunder",   icon="🌩️")

    # ── Statuses ──────────────────────────────────────────────────────────────
    api.define_status("blinded",        label="Blinded",     icon="😵",
                      effects={"enemy_atk_penalty": 4, "clears_on_turn": True})
    api.define_status("slowed",         label="Slowed",      icon="🐢",
                      effects={"enemy_ac_penalty": 2, "enemy_atk_penalty": 2, "clears_on_turn": True})
    api.define_status("arcane_warded",  label="Arcane Ward", icon="🔮",
                      effects={"player_ac_bonus": 3, "clears_on_take_hit": True})
    api.define_status("arcane_charged", label="Arcane Surge",icon="⚡",
                      effects={"damage_mult": 1.25, "clears_on_hit": True})

    # ── Helper ────────────────────────────────────────────────────────────────
    def _is(ctx, ability_id):
        return (ctx.player.char_class == "wizard"
                and ctx.turn.ability_id == ability_id)

    def _lv(ctx):
        return ctx.player.level

    def _spell_dice(ctx, die, base_count=1, scale_every=4):
        """Roll base_count dice, adding one extra die every scale_every levels."""
        extra = _lv(ctx) // scale_every
        n = base_count + extra
        return sum(ctx.roll(die) for _ in range(n)), n

    # ── Cantrips ──────────────────────────────────────────────────────────────

    def _fire_bolt(ctx):
        if not _is(ctx, "fire_bolt"): return []
        lv = _lv(ctx)
        dice = 1 + (lv >= 5) + (lv >= 11) + (lv >= 17)
        dmg  = sum(ctx.roll("1d10") for _ in range(dice))
        return [Modify("damage", add=dmg, damage_type="fire"),
                Message(f"Fire Bolt: {dmg} fire damage!")]

    def _ray_of_frost(ctx):
        if not _is(ctx, "ray_of_frost"): return []
        lv = _lv(ctx)
        dice = 1 + (lv >= 5) + (lv >= 11) + (lv >= 17)
        dmg  = sum(ctx.roll("1d8") for _ in range(dice))
        return [Modify("damage", add=dmg, damage_type="cold"), Status("slowed", 1),
                Message(f"Ray of Frost: {dmg} cold damage, enemy slowed!")]

    def _acid_splash(ctx):
        if not _is(ctx, "acid_splash"): return []
        lv = _lv(ctx)
        dice = 1 + (lv >= 5) + (lv >= 11) + (lv >= 17)
        dmg  = sum(ctx.roll("1d6") for _ in range(dice))
        return [Modify("damage", add=dmg, damage_type="acid"),
                Message(f"Acid Splash: {dmg} acid damage!")]

    # ── Spells ────────────────────────────────────────────────────────────────

    def _magic_missile(ctx):
        if not _is(ctx, "magic_missile"): return []
        lv = _lv(ctx)
        darts = 3 + (lv >= 3) + (lv >= 5) + (lv >= 7)
        dmg   = sum(ctx.roll("1d4") + 1 for _ in range(darts))
        return [Modify("damage", add=dmg, damage_type="force"),
                Message(f"Magic Missile: {darts} darts — {dmg} force damage (auto-hit)!")]

    def _burning_hands(ctx):
        if not _is(ctx, "burning_hands"): return []
        lv = _lv(ctx)
        dice = 3 + (lv >= 3) + (lv >= 5)
        dmg  = sum(ctx.roll("1d6") for _ in range(dice))
        return [Modify("damage", add=dmg, damage_type="fire"),
                Message(f"Burning Hands: {dmg} fire damage in a cone!")]

    def _thunderwave(ctx):
        if not _is(ctx, "thunderwave"): return []
        lv = _lv(ctx)
        dice = 2 + (lv >= 3) + (lv >= 5)
        dmg  = sum(ctx.roll("1d8") for _ in range(dice))
        return [Modify("damage", add=dmg, damage_type="thunder"),
                Message(f"Thunderwave: {dmg} thunder damage and pushed back!")]

    def _mirror_image(ctx):
        if not _is(ctx, "mirror_image"): return []
        return [Status("arcane_warded", 1),
                Message("Mirror Image: 3 duplicates — +3 AC vs the next hit!")]

    def _scorching_ray(ctx):
        if not _is(ctx, "scorching_ray"): return []
        lv = _lv(ctx)
        rays = 3 + (lv >= 5) + (lv >= 7)
        dmg  = sum(ctx.roll("2d6") for _ in range(rays))
        return [Modify("damage", add=dmg, damage_type="fire"),
                Message(f"Scorching Ray: {rays} rays — {dmg} total fire damage!")]

    def _lightning_bolt(ctx):
        if not _is(ctx, "lightning_bolt"): return []
        lv = _lv(ctx)
        dice = 8 + (lv >= 7) + (lv >= 9)
        dmg  = sum(ctx.roll("1d6") for _ in range(dice))
        return [Modify("damage", add=dmg, damage_type="lightning"),
                Message(f"Lightning Bolt: {dmg} lightning damage in a line!")]

    def _blight(ctx):
        if not _is(ctx, "blight"): return []
        dmg = sum(ctx.roll("1d8") for _ in range(8))
        return [Modify("damage", add=dmg, damage_type="necrotic"),
                Message(f"Blight: {dmg} necrotic damage — life force drained!")]

    # ── Subclass passives ─────────────────────────────────────────────────────

    def _evocation_potency(ctx):
        """Evocation Lv 2 (Sculpt Spells): passive +2 damage on evocation spells."""
        if ctx.player.char_class != "wizard" or ctx.player.subclass != "evocation": return []
        if ctx.player.level < 2: return []
        spell_abilities = {"fire_bolt","ray_of_frost","acid_splash",
                           "magic_missile","burning_hands","thunderwave",
                           "scorching_ray","lightning_bolt","blight"}
        if ctx.turn.ability_id not in spell_abilities: return []
        return [Modify("damage", add=2), Message("Empowered Evocation: +2 damage!")]

    def _divination_foresight(ctx):
        """Divination Lv 2 (Portent): once per turn, add +3 to attack or skill check."""
        if ctx.player.char_class != "wizard" or ctx.player.subclass != "divination": return []
        if ctx.player.level < 2: return []
        return [Modify("attack_roll", add=3), Message("Portent: +3 from your prophetic vision!")]

    def _arcane_surge(ctx):
        """Abjuration Lv 2 (Arcane Ward): 25% damage boost vs warded enemies."""
        if ctx.player.char_class != "wizard" or ctx.player.subclass != "abjuration": return []
        if ctx.player.level < 2: return []
        if not ctx.has_flag("arcane_charged"): return []
        return [Flag("arcane_charged", False), Message("Arcane Surge: 1.25× damage!")]

    api.on("on_ability_use", _fire_bolt)
    api.on("on_ability_use", _ray_of_frost)
    api.on("on_ability_use", _acid_splash)
    api.on("on_ability_use", _magic_missile)
    api.on("on_ability_use", _burning_hands)
    api.on("on_ability_use", _thunderwave)
    api.on("on_ability_use", _mirror_image)
    api.on("on_ability_use", _scorching_ray)
    api.on("on_ability_use", _lightning_bolt)
    api.on("on_ability_use", _blight)
    api.on("on_damage_roll", _evocation_potency)
    api.on("on_before_attack", _divination_foresight)

    # ── Spells data (used by character sheet / level-up UI) ──────────────────

    CANTRIPS = [
        {"id": "fire_bolt",    "name": "Fire Bolt",    "emoji": "🔥", "type": "cantrip",
         "desc": "Auto-hit ranged attack — 1d10 fire (scales: 2d10 at 5, 3d10 at 11, 4d10 at 17)."},
        {"id": "ray_of_frost", "name": "Ray of Frost", "emoji": "❄️", "type": "cantrip",
         "desc": "Auto-hit — 1d8 cold + slow (scales with level)."},
        {"id": "acid_splash",  "name": "Acid Splash",  "emoji": "🧪", "type": "cantrip",
         "desc": "Auto-hit — 1d6 acid (scales with level)."},
    ]

    SPELLS = [
        {"id": "magic_missile",  "name": "Magic Missile",  "emoji": "✨", "level": 1,
         "desc": "3+ force darts — always hit, 1d4+1 each."},
        {"id": "burning_hands",  "name": "Burning Hands",  "emoji": "🔥", "level": 1,
         "desc": "Cone of fire — 3d6 (scales to 5d6 at Lv 5)."},
        {"id": "thunderwave",    "name": "Thunderwave",    "emoji": "🌩️", "level": 1,
         "desc": "Pushes enemies back — 2d8 thunder (scales to 4d8 at Lv 5)."},
        {"id": "mirror_image",   "name": "Mirror Image",   "emoji": "🪞", "level": 2,
         "desc": "Create 3 duplicates — +3 AC vs the next hit taken."},
        {"id": "scorching_ray",  "name": "Scorching Ray",  "emoji": "🔥", "level": 2,
         "desc": "3+ rays — 2d6 fire each (scales with level)."},
        {"id": "lightning_bolt", "name": "Lightning Bolt", "emoji": "⚡", "level": 3,
         "desc": "Line of lightning — 8d6 (scales to 10d6 at Lv 9)."},
        {"id": "blight",         "name": "Blight",         "emoji": "💀", "level": 4,
         "desc": "Drains life — 8d8 necrotic."},
    ]

    # ── Class registration ────────────────────────────────────────────────────

    api.add_class({
        "id":           "wizard",
        "name":         "Wizard",
        "emoji":        "🧙",
        "hit_die":      6,
        "armor":        2,
        "primary_stat": "intelligence",
        "weapon_profs": ["simple"],
        "armor_profs":  [],
        "saving_throws":["intelligence", "wisdom"],
        "start_items":  ["quarterstaff", "spellbook"],
        "features": [
            {"level":  1, "name": "Spellcasting",
             "desc": "You wield arcane magic. Use INT for spell attacks and saving throw DCs."},
            {"level":  1, "name": "Arcane Recovery",
             "desc": "Once per day, regain expended spell slots equal to half your wizard level."},
            {"level":  2, "name": "Arcane Tradition",
             "desc": "Choose your subclass: Evocation, Divination, or Abjuration."},
            {"level":  4, "name": "Ability Score Improvement", "desc": "+2 to one ability, or +1 to two."},
            {"level": 18, "name": "Spell Mastery",
             "desc": "Cast one chosen 1st-level spell without expending a slot."},
            {"level": 20, "name": "Signature Spells",
             "desc": "Choose two 3rd-level spells — cast each once per short rest for free."},
        ],
        "abilities": [
            # Cantrips
            {"id": "fire_bolt",    "name": "Fire Bolt",    "label": "🔥 Fire Bolt",
             "action": "action", "level_req": 1, "once_per": None, "handler": _fire_bolt,
             "desc": "1d10 fire damage (auto-hit), scales to 4d10 at Lv 17."},
            {"id": "ray_of_frost", "name": "Ray of Frost", "label": "❄️ Ray of Frost",
             "action": "action", "level_req": 1, "once_per": None, "handler": _ray_of_frost,
             "desc": "1d8 cold + slow, scales with level."},
            {"id": "acid_splash",  "name": "Acid Splash",  "label": "🧪 Acid Splash",
             "action": "action", "level_req": 1, "once_per": None, "handler": _acid_splash,
             "desc": "1d6 acid, scales with level."},
            # Spells
            {"id": "magic_missile",  "name": "Magic Missile",  "label": "✨ Magic Missile",
             "action": "action", "level_req": 1, "once_per": None, "handler": _magic_missile,
             "desc": "3 darts, 1d4+1 each, always hits. More darts at higher level."},
            {"id": "burning_hands",  "name": "Burning Hands",  "label": "🔥 Burning Hands",
             "action": "action", "level_req": 1, "once_per": None, "handler": _burning_hands,
             "desc": "Cone of fire — 3d6 damage (scales to 5d6 at Lv 5)."},
            {"id": "thunderwave",    "name": "Thunderwave",    "label": "🌩️ Thunderwave",
             "action": "action", "level_req": 1, "once_per": None, "handler": _thunderwave,
             "desc": "2d8 thunder + push back, scales with level."},
            {"id": "mirror_image",   "name": "Mirror Image",   "label": "🪞 Mirror Image",
             "action": "bonus",  "level_req": 3, "once_per": "combat", "handler": _mirror_image,
             "desc": "+3 AC vs the next hit (duplicates absorb it)."},
            {"id": "scorching_ray",  "name": "Scorching Ray",  "label": "🔥 Scorching Ray",
             "action": "action", "level_req": 3, "once_per": None, "handler": _scorching_ray,
             "desc": "3+ rays, 2d6 fire each."},
            {"id": "lightning_bolt", "name": "Lightning Bolt", "label": "⚡ Lightning Bolt",
             "action": "action", "level_req": 5, "once_per": None, "handler": _lightning_bolt,
             "desc": "8d6 lightning in a line, scales at Lv 7 and 9."},
            {"id": "blight",         "name": "Blight",         "label": "💀 Blight",
             "action": "action", "level_req": 7, "once_per": None, "handler": _blight,
             "desc": "8d8 necrotic — drain the life from your enemy."},
        ],
        "subclasses": {
            "evocation":  {
                "abilities": [],
                "desc": "Sculpt Spells (exclude allies from AoE) + Empowered Evocation (+INT mod to damage).",
            },
            "divination": {
                "abilities": [],
                "desc": "Portent: roll 2d20 on long rest, use them to replace any roll.",
            },
            "abjuration": {
                "abilities": [],
                "desc": "Arcane Ward: absorb damage with a magical shield (INT + wizard level HP).",
            },
        },
        "level_choices": {
            ("wizard", 1): {
                "key": "cantrip", "prompt": "Choose your starting cantrips (pick 2):",
                "options": [
                    {"id": "fire_bolt",    "label": "Fire Bolt",    "desc": "1d10 fire, scales to 4d10."},
                    {"id": "ray_of_frost", "label": "Ray of Frost", "desc": "1d8 cold + slow enemy."},
                    {"id": "acid_splash",  "label": "Acid Splash",  "desc": "1d6 acid."},
                ],
            },
            ("wizard", 2): {
                "key": "subclass", "prompt": "Choose your Arcane Tradition:",
                "options": [
                    {"id": "evocation",  "label": "School of Evocation",  "desc": "Maximize spell damage; sculpt AoE to protect allies."},
                    {"id": "divination", "label": "School of Divination", "desc": "Portent dice — predict and rewrite fate."},
                    {"id": "abjuration", "label": "School of Abjuration", "desc": "Arcane Ward — absorb damage with a magical barrier."},
                ],
            },
        },
        "spells": {
            "cantrips": CANTRIPS,
            "spells":   SPELLS,
        },
        "favored_enemy_keywords": None,
    })
