CLASS = {
    "id":            "ranger",
    "name":          "Ranger",
    "emoji":         "🏹",
    "hit_die":       10,
    "armor":         2,   # studded leather equivalent
    "primary":       "dexterity",
    "start_items":   ["longbow", "shortsword"],
    "weapon_profs":  ["simple", "martial"],
    "armor_profs":   ["light", "medium", "shields"],
    "saving_throws": ["strength", "dexterity"],
}

# ── Lv 1-20 narrative features (shown in /class_upgrade and level-up embeds) ──

CLASS_FEATURES = [
    {"level":  1, "name": "Favored Enemy",
     "desc": "Choose a creature type — +2 damage and advantage on tracking checks against them"},
    {"level":  1, "name": "Natural Explorer",
     "desc": "Choose a favored terrain — ignore difficult terrain and double proficiency on terrain-related checks"},
    {"level":  2, "name": "Fighting Style",
     "desc": "Choose a combat specialty: Archery (+2 ranged ATK), Defense (+1 AC), Dueling (+2 one-hand melee dmg), Two-Weapon Fighting (offhand bonus attack)"},
    {"level":  2, "name": "Spellcasting",
     "desc": "WIS-based casting — learn Hunter's Mark, Cure Wounds, Ensnaring Strike, Hail of Thorns"},
    {"level":  3, "name": "Ranger Archetype",
     "desc": "Choose your subclass: Hunter (Colossus Slayer, Volley) or Beast Master (companion attacks with you)"},
    {"level":  3, "name": "Primeval Awareness",
     "desc": "Spend a spell slot to sense creature types within 1–6 miles"},
    {"level":  4, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level":  5, "name": "Extra Attack",
     "desc": "Attack twice whenever you take the Attack action"},
    {"level":  6, "name": "Favored Enemy (2)",
     "desc": "Choose a second favored enemy; learn two additional languages"},
    {"level":  7, "name": "Archetype Feature",
     "desc": "Hunter: Defensive Tactics (+4 AC after being hit, or evasion) · Beast Master: Beast gains additional HP equal to your level"},
    {"level":  8, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level":  8, "name": "Land's Stride",
     "desc": "Move through nonmagical difficult terrain without cost; advantage vs. impeding plants"},
    {"level":  9, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level": 10, "name": "Natural Explorer (2)",
     "desc": "Choose a second favored terrain; you can hide in plain sight by spending 1 minute"},
    {"level": 11, "name": "Archetype Feature",
     "desc": "Hunter: Volley — loose arrows at all nearby foes (splash) · Beast Master: Beast gets an extra attack each round"},
    {"level": 12, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level": 13, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level": 14, "name": "Vanish",
     "desc": "Hide as a bonus action once per combat; you can't be tracked by non-magical means"},
    {"level": 15, "name": "Archetype Feature",
     "desc": "Hunter: Evasion (no damage on DEX save success) · Beast Master: Beast shares your saving throw proficiencies"},
    {"level": 16, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level": 17, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level": 18, "name": "Feral Senses",
     "desc": "No disadvantage attacking invisible creatures; sense hidden enemies within 30 ft"},
    {"level": 19, "name": "Ability Score Improvement",
     "desc": "+2 to one ability score, or +1 to two different scores"},
    {"level": 20, "name": "Foe Slayer",
     "desc": "Once per turn: add WIS mod to one attack roll or damage roll vs. your favored enemy"},
]

# ── Active combat abilities ───────────────────────────────────────────────────

COMBAT_FEATURES = [
    {"id": "hunters_mark",     "name": "Hunter's Mark",    "label": "🎯 Hunter's Mark",
     "action_type": "bonus",  "level_req": 1, "once_per": "combat",
     "desc": "Mark a target — all your attacks deal +1d6 extra damage for the rest of combat"},
    {"id": "cure_wounds_rng",  "name": "Cure Wounds",      "label": "💚 Cure Wounds",
     "action_type": "action", "level_req": 2, "once_per": "combat",
     "desc": "Spend a spell slot — heal yourself 1d8 + WIS mod HP (once per combat)"},
    {"id": "ensnaring_strike", "name": "Ensnaring Strike", "label": "🌿 Ensnaring Strike",
     "action_type": "bonus",  "level_req": 2, "once_per": "combat",
     "desc": "Prime thorns — your next ranged hit restrains the target (enemy ATK −2 next round, once per combat)"},
    {"id": "hail_of_thorns",   "name": "Hail of Thorns",  "label": "🌪️ Hail of Thorns",
     "action_type": "bonus",  "level_req": 2, "once_per": "combat",
     "desc": "Prime a thorn burst — your next ranged hit also deals +1d10 piercing (once per combat)"},
    {"id": "vanish",           "name": "Vanish",           "label": "👁️ Vanish",
     "action_type": "bonus",  "level_req": 14, "once_per": "combat",
     "desc": "Lv 14+: Melt into shadow — take half damage from the next enemy attack (once per combat)"},
]

# ── Subclass combat features ─────────────────────────────────────────────────

SUBCLASS_COMBAT_FEATURES = {
    # Colossus Slayer fires automatically in the attack loop (passive, once per turn).
    # Volley is active: player chooses it as their main action.
    "hunter": [
        {"id": "volley", "name": "Volley", "label": "🏹 Volley",
         "action_type": "action", "level_req": 11, "once_per": "combat",
         "desc": "Lv 11+: Rain of arrows — make 2 extra attacks this round (once per combat)"},
    ],

    # Beast auto-attacks alongside the ranger (passive, handled in attack loop).
    # Beast Guard is the active panic button — intercept the next hit.
    "beast_master": [
        {"id": "beast_protect", "name": "Beast Guard", "label": "🛡️ Beast Guard",
         "action_type": "bonus", "level_req": 7, "once_per": "combat",
         "desc": "Lv 7+: Your beast intercepts — take half damage from the next enemy attack (once per combat)"},
    ],
}

# ── Level-up interactive choices ─────────────────────────────────────────────

# Favored enemy keywords used by the engine to match campaign enemy names:
# humanoid → goblin, bandit, guard, scout, lieutenant, chief
# undead   → skeleton, ghost, spirit, lich, restless
# beast    → spider, hound, wolf, bear, rat, serpent
# dragon   → dragon, drake, wyrm
# fiend    → devil, demon, imp, fiend

FAVORED_ENEMY_KEYWORDS: dict[str, list[str]] = {
    "humanoid": ["goblin", "bandit", "guard", "scout", "lieutenant", "chief", "soldier", "cultist"],
    "undead":   ["skeleton", "ghost", "spirit", "lich", "restless", "zombie", "wraith", "vampire"],
    "beast":    ["spider", "hound", "wolf", "bear", "rat", "serpent", "shadow hound"],
    "dragon":   ["dragon", "drake", "wyrm", "wyvern"],
    "fiend":    ["devil", "demon", "imp", "fiend", "infernal"],
}

LEVEL_UP_CHOICES = {
    ("ranger", 1): {
        "key":    "favored_enemy",
        "prompt": "Choose your Favored Enemy:",
        "options": [
            {"id": "humanoid",
             "label": "Humanoids",
             "desc": "Goblins, bandits, soldiers — +2 damage and tracking expertise"},
            {"id": "undead",
             "label": "Undead",
             "desc": "Skeletons, ghosts, liches — +2 damage and monster lore"},
            {"id": "beast",
             "label": "Beasts",
             "desc": "Spiders, hounds, wild creatures — +2 damage and survival tracking"},
            {"id": "dragon",
             "label": "Dragons",
             "desc": "Dragons and dragonkin — +2 damage and arcane insight"},
            {"id": "fiend",
             "label": "Fiends",
             "desc": "Demons, devils, fiendish entities — +2 damage and planar lore"},
        ],
    },
    ("ranger", 2): {
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
             "desc": "+2 damage when wielding a one-handed melee weapon with no other weapons"},
            {"id": "two_weapon_fighting",
             "label": "Two-Weapon Fighting",
             "desc": "Add your ability modifier to the off-hand bonus attack each round"},
        ],
    },
    ("ranger", 3): {
        "key":    "subclass",
        "prompt": "Choose your Ranger Archetype:",
        "options": [
            {"id": "hunter",
             "label": "Hunter",
             "desc": "Colossus Slayer (+1d8 vs wounded enemies, passive); Volley (2 bonus arrows) at Lv 11"},
            {"id": "beast_master",
             "label": "Beast Master",
             "desc": "Beast companion auto-attacks with you; Beast Guard (half damage) at Lv 7"},
        ],
    },
}
