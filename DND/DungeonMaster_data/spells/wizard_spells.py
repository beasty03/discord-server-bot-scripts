# Wizard spell registry
# CANTRIPS are always prepared; all others require /prepare_spells selection.
# STARTING_SPELLS are auto-given when a wizard first prepares spells.

CANTRIPS = {"magic_missile"}

STARTING_SPELLS = ["magic_missile", "shield_spell", "burning_hands", "thunderwave"]

SPELLS = [
    # ── Cantrips (no preparation needed) ────────────────────────────────────
    {"id": "magic_missile",  "name": "Magic Missile",  "emoji": "✨",
     "school": "evocation",   "level": 0,
     "action_type": "action", "level_req": 1, "once_per": None,
     "desc": "Auto-hit — 1d4+1 bolts; scales to 6 bolts at Lv 16 (cantrip, always available)"},

    # ── Lv 1 spells (available from wizard Lv 1) ────────────────────────────
    {"id": "shield_spell",   "name": "Shield",          "emoji": "🛡️",
     "school": "abjuration",  "level": 1,
     "action_type": "bonus",  "level_req": 1, "once_per": "combat",
     "desc": "+5 AC vs the next attack targeting you this round (bonus action, once per combat)"},

    {"id": "burning_hands",  "name": "Burning Hands",   "emoji": "🔥",
     "school": "evocation",   "level": 1,
     "action_type": "action", "level_req": 1, "once_per": "combat",
     "desc": "Cone of fire — 3d6 auto-hit; scales +1d6 per 4 levels (once per combat)"},

    {"id": "thunderwave",    "name": "Thunderwave",      "emoji": "🌊",
     "school": "evocation",   "level": 1,
     "action_type": "action", "level_req": 1, "once_per": "combat",
     "desc": "2d8 + INT thunder auto-hit; enemy ATK −2 next round (once per combat)"},

    # ── Lv 2 spells (available from wizard Lv 3) ────────────────────────────
    {"id": "misty_step",     "name": "Misty Step",       "emoji": "💨",
     "school": "conjuration", "level": 2,
     "action_type": "bonus",  "level_req": 3, "once_per": "combat",
     "desc": "Teleport away — half damage from the next hit against you (bonus action, Lv 3+, once per combat)"},

    {"id": "scorching_ray",  "name": "Scorching Ray",    "emoji": "☀️",
     "school": "evocation",   "level": 2,
     "action_type": "action", "level_req": 3, "once_per": "combat",
     "desc": "Three fire rays — each needs an attack roll, 2d6 fire each hit (Lv 3+, once per combat)"},

    # ── Lv 3 spells (available from wizard Lv 5) ────────────────────────────
    {"id": "fireball",       "name": "Fireball",         "emoji": "💥",
     "school": "evocation",   "level": 3,
     "action_type": "action", "level_req": 5, "once_per": "combat",
     "desc": "8d6 fire explosion auto-hit; Evocation adds INT mod bonus dmg (Lv 5+, once per combat)"},

    {"id": "counterspell",   "name": "Counterspell",     "emoji": "🚫",
     "school": "abjuration",  "level": 3,
     "action_type": "bonus",  "level_req": 5, "once_per": "combat",
     "desc": "Disrupt the enemy — they skip their attack this round (bonus action, Lv 5+, once per combat)"},
]
