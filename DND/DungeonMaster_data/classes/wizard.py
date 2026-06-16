CLASS = {
    "id":            "wizard",
    "name":          "Wizard",
    "emoji":         "🪄",
    "hit_die":       6,
    "armor":         0,
    "primary":       "intelligence",
    "start_items":   ["quarterstaff", "spellbook"],
    "weapon_profs":  ["dagger", "quarterstaff"],
    "armor_profs":   [],
    "saving_throws": ["intelligence", "wisdom"],
}

# ── Lv 1-20 narrative features ───────────────────────────────────────────────

CLASS_FEATURES = [
    {"level":  1, "name": "Spellcasting",
     "desc": "INT-based casting — prepare spells from your spellbook with /prepare_spells; cast them in combat"},
    {"level":  1, "name": "Arcane Recovery",
     "desc": "Once per day (short rest): recover spell slots equal to half your wizard level"},
    {"level":  2, "name": "Arcane Tradition",
     "desc": "Choose a school subclass: Evocation, Abjuration, Illusion, or Divination"},
    {"level":  4, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level":  5, "name": "Lv 3 Spells",
     "desc": "Access Fireball and Counterspell — prepare them with /prepare_spells"},
    {"level":  6, "name": "Arcane Tradition Feature",
     "desc": "Gain your school's Lv 6 feature"},
    {"level":  8, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level": 10, "name": "Arcane Tradition Feature",
     "desc": "Gain your school's Lv 10 feature"},
    {"level": 12, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level": 14, "name": "Arcane Tradition Feature",
     "desc": "Gain your school's Lv 14 feature"},
    {"level": 16, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level": 18, "name": "Spell Mastery",
     "desc": "Choose one Lv 1 and one Lv 2 spell: cast them without slots"},
    {"level": 19, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level": 20, "name": "Signature Spell",
     "desc": "Two Lv 3 spells castable once per short rest without a slot"},
]

# ── Active combat abilities ───────────────────────────────────────────────────
# magic_missile is a cantrip (once_per=None, always shown).
# All others require preparation via /prepare_spells and are shown only if prepared.

COMBAT_FEATURES = [
    # Cantrip — always available, no preparation needed
    {"id": "magic_missile",  "name": "Magic Missile",  "label": "✨ Magic Missile",
     "action_type": "action", "level_req": 1, "once_per": None,
     "desc": "Auto-hit — 1d4+1 bolts scales from 3→6 bolts by Lv 16 (cantrip, free)"},

    # Lv 1 spells — available from wizard Lv 1, must be prepared
    {"id": "burning_hands",  "name": "Burning Hands",  "label": "🔥 Burning Hands",
     "action_type": "action", "level_req": 1, "once_per": "combat",
     "desc": "Cone of fire — 3d6 auto-hit; +1d6 per 4 levels (once per combat)"},
    {"id": "thunderwave",    "name": "Thunderwave",     "label": "🌊 Thunderwave",
     "action_type": "action", "level_req": 1, "once_per": "combat",
     "desc": "2d8 + INT thunder auto-hit; enemy ATK −2 next round (once per combat)"},
    {"id": "shield_spell",   "name": "Shield",          "label": "🛡️ Shield",
     "action_type": "bonus",  "level_req": 1, "once_per": "combat",
     "desc": "+5 AC vs the next hit this round (bonus action, once per combat)"},

    # Lv 2 spells — available from wizard Lv 3, must be prepared
    {"id": "scorching_ray",  "name": "Scorching Ray",   "label": "☀️ Scorching Ray",
     "action_type": "action", "level_req": 3, "once_per": "combat",
     "desc": "Three fire rays — each needs attack roll, 2d6 fire each hit (Lv 3+, once per combat)"},
    {"id": "misty_step",     "name": "Misty Step",      "label": "💨 Misty Step",
     "action_type": "bonus",  "level_req": 3, "once_per": "combat",
     "desc": "Teleport away — half damage from the next hit against you (Lv 3+, bonus action, once per combat)"},

    # Lv 3 spells — available from wizard Lv 5, must be prepared
    {"id": "fireball",       "name": "Fireball",        "label": "💥 Fireball",
     "action_type": "action", "level_req": 5, "once_per": "combat",
     "desc": "8d6 fire explosion auto-hit; Evocation adds +INT mod bonus dmg (Lv 5+, once per combat)"},
    {"id": "counterspell",   "name": "Counterspell",    "label": "🚫 Counterspell",
     "action_type": "bonus",  "level_req": 5, "once_per": "combat",
     "desc": "Enemy skips their attack this round (Lv 5+, bonus action, once per combat)"},
]

# ── Subclass combat features ─────────────────────────────────────────────────
# All school effects are passive — handled in the attack/retaliation loops.
# evocation   → Sculpt Spells (Magic Missile +1d4 bonus, Fireball +INT dmg)
# abjuration  → Arcane Ward (ward_hp mechanic)
# illusion    → Illusory Self (+4 ATK first round)
# divination  → Portent (roll twice, take better on first ATK)
# knowledge   → +2 to all ATK rolls (from wider combat knowledge)

SUBCLASS_COMBAT_FEATURES = {
    "evocation":  [],
    "abjuration": [],
    "illusion":   [],
    "divination": [],
    "knowledge":  [],
}

# ── Level-up interactive choices ─────────────────────────────────────────────

LEVEL_UP_CHOICES = {
    ("wizard", 2): {
        "key":    "subclass",
        "prompt": "Choose your Arcane Tradition:",
        "options": [
            {"id": "evocation",  "label": "Evocation",
             "desc": "Sculpt Spells — +1d4 to Magic Missile; Fireball gains +INT mod bonus damage"},
            {"id": "abjuration", "label": "Abjuration",
             "desc": "Arcane Ward — absorb damage with a shield of magical force (INT mod + level HP)"},
            {"id": "illusion",   "label": "Illusion",
             "desc": "Illusory Self — +4 to attack rolls on the first round of combat"},
            {"id": "divination", "label": "Divination",
             "desc": "Portent — roll twice for your first attack each combat, take the better result"},
            {"id": "knowledge",  "label": "School of Knowledge",
             "desc": "Broad Study — +2 to all spell attack rolls from accumulated arcane insight"},
        ],
    },
}
