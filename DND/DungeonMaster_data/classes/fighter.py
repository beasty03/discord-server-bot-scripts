CLASS = {
    "id":          "fighter",
    "name":        "Fighter",
    "emoji":       "⚔️",
    "hit_die":     10,
    "armor":       6,
    "primary":     "strength",
    "start_items": ["longsword", "shield"],
    "weapon_profs": ["simple", "martial"],
    "armor_profs":  ["light", "medium", "heavy", "shields"],
    "saving_throws": ["strength", "constitution"],
}

# ── Lv 1-20 narrative features (shown in /class_upgrade and level-up embeds) ──

CLASS_FEATURES = [
    {"level":  1, "name": "Fighting Style",
     "desc": "Choose a combat specialty: Archery (+2 ranged ATK), Defense (+1 AC), Dueling (+2 melee dmg), Great Weapon Fighting (reroll 1s & 2s on dmg), Two-Weapon Fighting (offhand bonus attack), Protection (shield ally from hits)"},
    {"level":  1, "name": "Second Wind",
     "desc": "Bonus action: regain 1d10 + level HP (once per combat)"},
    {"level":  2, "name": "Action Surge",
     "desc": "Take one extra attack action on your turn (once per combat; twice at Lv 17)"},
    {"level":  3, "name": "Martial Archetype",
     "desc": "Choose your subclass: Champion (expanded crits), Battle Master (Superiority Dice maneuvers), or Eldritch Knight (arcane spells)"},
    {"level":  4, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level":  5, "name": "Extra Attack",
     "desc": "Attack twice whenever you take the Attack action"},
    {"level":  6, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level":  7, "name": "Archetype Feature",
     "desc": "Champion: Remarkable Athlete (+half prof to ATK/init) · Battle Master: Know Your Enemy (learn enemy stats) · Eldritch Knight: War Magic (bonus weapon attack after casting a cantrip)"},
    {"level":  8, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level":  9, "name": "Indomitable",
     "desc": "When reduced to 0 HP, roll CON save — on success, survive at 1 HP instead (1× per combat)"},
    {"level": 10, "name": "Archetype Feature",
     "desc": "Champion: Additional Fighting Style · Battle Master: 6 Superiority Dice, d10 die size · Eldritch Knight: Eldritch Strike (enemy −2 ATK after a hit)"},
    {"level": 11, "name": "Extra Attack (2)",
     "desc": "Attack three times whenever you take the Attack action"},
    {"level": 12, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level": 13, "name": "Indomitable (2×)",
     "desc": "Indomitable can now be used twice per combat"},
    {"level": 14, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level": 15, "name": "Archetype Feature",
     "desc": "Champion: Superior Critical (crit on 18–20) · Battle Master: d12 Superiority Dice · Eldritch Knight: Arcane Charge (+1d6 force per Action Surge attack)"},
    {"level": 16, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level": 17, "name": "Action Surge (2×)",
     "desc": "Action Surge can now be used twice per combat; Indomitable usable 3× per combat"},
    {"level": 18, "name": "Archetype Feature",
     "desc": "Champion: Survivor (regain 5+CON HP at start of each round when ≤ half HP) · Battle Master: additional maneuver known · Eldritch Knight: Improved War Magic (bonus weapon attack after any spell)"},
    {"level": 19, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level": 20, "name": "Extra Attack (3)",
     "desc": "Attack four times whenever you take the Attack action"},
]

# ── Active combat abilities (main action or bonus action, shown in UI) ──────

COMBAT_FEATURES = [
    {"id": "second_wind",  "name": "Second Wind",  "label": "🌬️ Second Wind",
     "action_type": "bonus",  "level_req": 1,  "once_per": "combat",
     "desc": "Heal 1d10 + fighter level HP (bonus action, once per combat)"},
    {"id": "action_surge", "name": "Action Surge", "label": "⚡ Action Surge",
     "action_type": "action", "level_req": 2,  "once_per": "combat",
     "desc": "Extra attacks this round — uses your Action Surge charge"},
]

# ── Subclass combat features ─────────────────────────────────────────────────
# Battle Master maneuvers each cost 1 Superiority Die.
# once_per = None so the CombatView shows them regardless; dice-count gate is
# handled at runtime by checking run["sup_dice"][uid] > 0.

SUBCLASS_COMBAT_FEATURES = {
    "champion": [],         # champion effects are all passive (crit range, survivor)

    "battle_master": [
        {"id": "bm_precision",  "name": "Precision Attack",  "label": "🎯 Precision Attack",
         "action_type": "bonus", "level_req": 3, "once_per": None,
         "desc": "Spend 1 Superiority Die — add the result to your next attack roll this round"},
        {"id": "bm_trip",       "name": "Trip Attack",        "label": "🦵 Trip Attack",
         "action_type": "bonus", "level_req": 3, "once_per": None,
         "desc": "Spend 1 Superiority Die — on next hit: +die damage and enemy AC −2 next round"},
        {"id": "bm_disarm",     "name": "Disarming Strike",   "label": "🔓 Disarming Strike",
         "action_type": "bonus", "level_req": 3, "once_per": None,
         "desc": "Spend 1 Superiority Die — on next hit: +die damage and enemy ATK −2 next round"},
        {"id": "bm_riposte",    "name": "Riposte",            "label": "🔄 Riposte",
         "action_type": "bonus", "level_req": 3, "once_per": None,
         "desc": "Spend 1 Superiority Die — counter-attack when the enemy misses you this round (+die damage)"},
        {"id": "bm_menacing",   "name": "Menacing Attack",    "label": "😤 Menacing Attack",
         "action_type": "bonus", "level_req": 3, "once_per": None,
         "desc": "Spend 1 Superiority Die — on next hit: +die damage and enemy must target you next round"},
    ],

    "eldritch_knight": [
        {"id": "fire_bolt",     "name": "Fire Bolt",          "label": "🔥 Fire Bolt",
         "action_type": "action", "level_req": 3, "once_per": None,
         "desc": "Ranged cantrip — 1d10 fire (auto-hit); scales: 2d10 at Lv 5, 3d10 at Lv 11, 4d10 at Lv 17"},
        {"id": "ek_shield",     "name": "Shield Spell",       "label": "🛡️ Shield",
         "action_type": "bonus", "level_req": 3, "once_per": "combat",
         "desc": "+5 AC until the start of your next turn (once per combat)"},
        {"id": "war_magic_atk", "name": "War Magic Strike",   "label": "⚔️ War Magic Strike",
         "action_type": "bonus", "level_req": 7, "once_per": None,
         "desc": "After casting Fire Bolt, make one weapon attack as a bonus action (Lv 7+)"},
    ],
}

# ── Level-up interactive choices ─────────────────────────────────────────────

LEVEL_UP_CHOICES = {
    ("fighter", 1): {
        "key":    "fighting_style",
        "prompt": "Choose your Fighting Style:",
        "options": [
            {"id": "archery",
             "label": "Archery",
             "desc": "+2 to attack rolls with ranged weapons"},
            {"id": "defense",
             "label": "Defense",
             "desc": "+1 AC while wearing armor"},
            {"id": "dueling",
             "label": "Dueling",
             "desc": "+2 damage when wielding a melee weapon in one hand and no other weapons (shield is fine)"},
            {"id": "great_weapon_fighting",
             "label": "Great Weapon Fighting",
             "desc": "Reroll 1s and 2s on weapon damage dice — keep the new result"},
            {"id": "two_weapon_fighting",
             "label": "Two-Weapon Fighting",
             "desc": "Add your ability modifier to the off-hand bonus attack each round"},
            {"id": "protection",
             "label": "Protection",
             "desc": "Reaction: when an ally is hit, they take 3 less damage (requires a shield)"},
        ],
    },
    ("fighter", 3): {
        "key":    "subclass",
        "prompt": "Choose your Martial Archetype:",
        "options": [
            {"id": "champion",
             "label": "Champion",
             "desc": "Improved Critical (19–20); Superior Critical at Lv 15 (18–20); Survivor HP regen at Lv 18"},
            {"id": "battle_master",
             "label": "Battle Master",
             "desc": "Superiority Dice (4→6 dice, d8→d12) + five tactical maneuvers"},
            {"id": "eldritch_knight",
             "label": "Eldritch Knight",
             "desc": "Fire Bolt cantrip; Shield spell; War Magic bonus attack at Lv 7"},
        ],
    },
}
