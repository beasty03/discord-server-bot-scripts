from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ============================================================================
# CURRENCY  (shared coins — same balance the casino/bank cogs use via ForgeDB)
# ============================================================================

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ============================================================================
# ABILITY SCORES
# ============================================================================

# The six D&D ability scores, in display order.
ABILITIES = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]

# Short labels shown on the character sheet.
ABILITY_ABBR = {
    "strength":     "STR",
    "dexterity":    "DEX",
    "constitution": "CON",
    "intelligence": "INT",
    "wisdom":       "WIS",
    "charisma":     "CHA",
}

# Scores are rolled 4d6-drop-lowest at creation. Set ROLL_METHOD = "array" to
# hand out the standard array instead (no randomness).
ROLL_METHOD    = "roll"                       # "roll" | "array"
STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]      # used only when ROLL_METHOD == "array"

# ============================================================================
# RACES — racial ability modifiers are added at read time, never baked into
# the stored base scores (so re-picking a race never double-applies).
# Add more races in a content pack later; these are the standalone defaults.
# ============================================================================

RACES = [
    {"id": "human",    "name": "Human",     "emoji": "🧑",
     "mods": {"strength": 1, "dexterity": 1, "constitution": 1, "intelligence": 1, "wisdom": 1, "charisma": 1}},
    {"id": "elf",      "name": "Elf",       "emoji": "🧝",
     "mods": {"dexterity": 2, "intelligence": 1}},
    {"id": "dwarf",    "name": "Dwarf",     "emoji": "🧔",
     "mods": {"constitution": 2, "strength": 1}},
    {"id": "halfling", "name": "Halfling",  "emoji": "🧒",
     "mods": {"dexterity": 2, "charisma": 1}},
    {"id": "half_orc", "name": "Half-Orc",  "emoji": "👹",
     "mods": {"strength": 2, "constitution": 1}},
    {"id": "tiefling", "name": "Tiefling",  "emoji": "😈",
     "mods": {"charisma": 2, "intelligence": 1}},
]

# ============================================================================
# CLASSES
#   hit_die     = die size for HP / hit dice (6, 8, 10, 12)
#   armor       = flat AC bonus from starting armor (AC = 10 + DEX mod + armor)
#   primary     = key ability (used later for attack/skill checks)
#   start_items = item ids granted the first time this class is set
# ============================================================================

CLASSES = [
    {"id": "fighter",   "name": "Fighter",   "emoji": "⚔️", "hit_die": 10, "armor": 6, "primary": "strength",     "start_items": ["longsword", "shield"],        "weapon_profs": ["simple", "martial"]},
    {"id": "barbarian", "name": "Barbarian", "emoji": "🪓", "hit_die": 12, "armor": 2, "primary": "strength",     "start_items": ["greataxe"],                   "weapon_profs": ["simple", "martial"]},
    {"id": "rogue",     "name": "Rogue",     "emoji": "🗡️", "hit_die": 8,  "armor": 1, "primary": "dexterity",    "start_items": ["dagger", "leather_armor"],    "weapon_profs": ["simple", "longsword", "shortsword", "rapier"]},
    {"id": "ranger",    "name": "Ranger",    "emoji": "🏹", "hit_die": 10, "armor": 1, "primary": "dexterity",    "start_items": ["shortbow", "leather_armor"],  "weapon_profs": ["simple", "martial"]},
    {"id": "wizard",    "name": "Wizard",    "emoji": "🪄", "hit_die": 6,  "armor": 0, "primary": "intelligence", "start_items": ["quarterstaff", "spellbook"],  "weapon_profs": ["dagger", "quarterstaff"]},
    {"id": "cleric",    "name": "Cleric",    "emoji": "✨", "hit_die": 8,  "armor": 4, "primary": "wisdom",       "start_items": ["mace", "shield"],             "weapon_profs": ["simple"]},
]

# ============================================================================
# ITEMS — minimal starter catalogue so the backpack has names to show.
# Loot/weapon packs will extend this registry later.
# ============================================================================

ITEMS = [
    # weapon_type: "simple" or "martial" — used for proficiency checks.
    # ability: which ability score drives the attack roll.
    {"id": "longsword",     "name": "Longsword",     "slot": "weapon",  "weapon_type": "martial", "ability": "strength"},
    {"id": "greataxe",      "name": "Greataxe",      "slot": "weapon",  "weapon_type": "martial", "ability": "strength"},
    {"id": "dagger",        "name": "Dagger",        "slot": "weapon",  "weapon_type": "simple",  "ability": "dexterity"},
    {"id": "shortbow",      "name": "Shortbow",      "slot": "weapon",  "weapon_type": "simple",  "ability": "dexterity"},
    {"id": "quarterstaff",  "name": "Quarterstaff",  "slot": "weapon",  "weapon_type": "simple",  "ability": "strength"},
    {"id": "mace",          "name": "Mace",          "slot": "weapon",  "weapon_type": "simple",  "ability": "strength"},
    {"id": "shield",        "name": "Shield",        "slot": "offhand"},
    {"id": "leather_armor", "name": "Leather Armor", "slot": "armor"},
    {"id": "spellbook",     "name": "Spellbook",     "slot": "misc"},
]

# ============================================================================
# LEVELING — XP needed to *be* a given level (5e thresholds). Index = level.
# Level-ups happen later through campaigns; for now /level just shows progress.
# ============================================================================

XP_THRESHOLDS = [
    0, 0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000,
    85000, 100000, 120000, 140000, 165000, 195000, 225000, 265000, 305000, 355000,
]
MAX_LEVEL = 20

# ============================================================================
# CLASS FEATURES — keyed by class id, sorted by level.
# ============================================================================

CLASS_FEATURES = {
    "fighter": [
        {"level":  1, "name": "Fighting Style",          "desc": "Pick a weapon-style bonus (archery, defence, dueling, etc.)"},
        {"level":  1, "name": "Second Wind",              "desc": "Bonus action: regain 1d10+level HP once per short rest"},
        {"level":  2, "name": "Action Surge",             "desc": "Take one extra action on your turn, once per short rest"},
        {"level":  3, "name": "Martial Archetype",        "desc": "Choose a subclass: Champion, Battle Master, Eldritch Knight"},
        {"level":  4, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level":  5, "name": "Extra Attack",             "desc": "Attack twice when you take the Attack action"},
        {"level":  6, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level":  7, "name": "Archetype Feature",        "desc": "Gain your subclass's Lv 7 feature"},
        {"level":  8, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level":  9, "name": "Indomitable",              "desc": "Reroll one failed saving throw, once per long rest"},
        {"level": 10, "name": "Archetype Feature",        "desc": "Gain your subclass's Lv 10 feature"},
        {"level": 11, "name": "Extra Attack (2)",         "desc": "Attack three times with the Attack action"},
        {"level": 12, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 13, "name": "Indomitable (2×)",         "desc": "Use Indomitable twice per long rest"},
        {"level": 14, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 15, "name": "Archetype Feature",        "desc": "Gain your subclass's Lv 15 feature"},
        {"level": 16, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 17, "name": "Action Surge (2×)",        "desc": "Two extra actions per short rest; Indomitable 3× per long rest"},
        {"level": 18, "name": "Archetype Feature",        "desc": "Gain your subclass's Lv 18 feature"},
        {"level": 19, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 20, "name": "Extra Attack (3)",         "desc": "Attack four times with the Attack action"},
    ],
    "barbarian": [
        {"level":  1, "name": "Rage",                    "desc": "Bonus action: STR adv, bonus STR dmg, resistance to B/P/S damage"},
        {"level":  1, "name": "Unarmored Defense",       "desc": "AC = 10 + DEX mod + CON mod when wearing no armor"},
        {"level":  2, "name": "Reckless Attack",         "desc": "Attack with adv; attackers also gain adv against you until next turn"},
        {"level":  2, "name": "Danger Sense",            "desc": "Advantage on DEX saves against visible effects"},
        {"level":  3, "name": "Primal Path",             "desc": "Choose a subclass: Berserker, Totem Warrior"},
        {"level":  4, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level":  5, "name": "Extra Attack",            "desc": "Attack twice with the Attack action"},
        {"level":  5, "name": "Fast Movement",           "desc": "+10 ft movement speed when not in heavy armor"},
        {"level":  6, "name": "Path Feature",            "desc": "Gain your subclass's Lv 6 feature"},
        {"level":  7, "name": "Feral Instinct",          "desc": "Advantage on initiative; act normally if surprised while raging"},
        {"level":  8, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level":  9, "name": "Brutal Critical",         "desc": "+1 weapon damage die on melee crits"},
        {"level": 10, "name": "Path Feature",            "desc": "Gain your subclass's Lv 10 feature"},
        {"level": 11, "name": "Relentless Rage",         "desc": "CON save to drop to 1 HP instead of 0 while raging"},
        {"level": 12, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 13, "name": "Brutal Critical (2)",     "desc": "+2 weapon damage dice on melee crits"},
        {"level": 14, "name": "Path Feature",            "desc": "Gain your subclass's Lv 14 feature"},
        {"level": 15, "name": "Persistent Rage",         "desc": "Rage no longer ends early if you haven't attacked or taken damage"},
        {"level": 16, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 17, "name": "Brutal Critical (3)",     "desc": "+3 weapon damage dice on melee crits"},
        {"level": 18, "name": "Indomitable Might",       "desc": "Use your STR score (not roll) for STR checks if the roll is lower"},
        {"level": 19, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 20, "name": "Primal Champion",         "desc": "+4 STR, +4 CON; unlimited Rage uses"},
    ],
    "rogue": [
        {"level":  1, "name": "Expertise",               "desc": "Double proficiency on two skills or one skill + thieves' tools"},
        {"level":  1, "name": "Sneak Attack",            "desc": "1d6 extra damage when you have adv or an ally flanks the target"},
        {"level":  1, "name": "Thieves' Cant",           "desc": "Secret language and signs shared among rogues"},
        {"level":  2, "name": "Cunning Action",          "desc": "Bonus action: Dash, Disengage, or Hide"},
        {"level":  3, "name": "Roguish Archetype",       "desc": "Choose a subclass: Thief, Assassin, Arcane Trickster"},
        {"level":  4, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level":  5, "name": "Uncanny Dodge",           "desc": "Reaction: halve damage from one visible attacker's hit"},
        {"level":  6, "name": "Expertise",               "desc": "Double proficiency on two more skills"},
        {"level":  7, "name": "Evasion",                 "desc": "No damage on successful DEX saves; half on failed ones"},
        {"level":  8, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level":  9, "name": "Archetype Feature",       "desc": "Gain your subclass's Lv 9 feature"},
        {"level": 10, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 11, "name": "Reliable Talent",         "desc": "Treat any roll below 10 as a 10 for proficient skill checks"},
        {"level": 12, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 13, "name": "Archetype Feature",       "desc": "Gain your subclass's Lv 13 feature"},
        {"level": 14, "name": "Blindsense",              "desc": "Detect hidden creatures within 10 ft if you can hear"},
        {"level": 15, "name": "Slippery Mind",           "desc": "Gain proficiency in WIS saving throws"},
        {"level": 16, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 17, "name": "Archetype Feature",       "desc": "Gain your subclass's Lv 17 feature"},
        {"level": 18, "name": "Elusive",                 "desc": "Attackers never have advantage on rolls against you"},
        {"level": 19, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 20, "name": "Stroke of Luck",          "desc": "Once per long rest: turn a miss into a hit, or treat a roll as 20"},
    ],
    "ranger": [
        {"level":  1, "name": "Favored Enemy",           "desc": "+2 dmg and adv on tracking vs. a chosen creature type"},
        {"level":  1, "name": "Natural Explorer",        "desc": "Choose a terrain: ignore difficult terrain, double prof on related skills"},
        {"level":  2, "name": "Fighting Style",          "desc": "Pick a weapon-style bonus (archery, defence, two-weapon, etc.)"},
        {"level":  2, "name": "Spellcasting",            "desc": "WIS-based spellcasting; learn 2 ranger spells"},
        {"level":  3, "name": "Ranger Archetype",        "desc": "Choose a subclass: Hunter, Beast Master"},
        {"level":  3, "name": "Primeval Awareness",      "desc": "Spend a spell slot to sense creature types within 1–6 miles"},
        {"level":  4, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level":  5, "name": "Extra Attack",            "desc": "Attack twice with the Attack action"},
        {"level":  6, "name": "Favored Enemy (2)",       "desc": "Choose a second favored enemy; learn 2 extra languages"},
        {"level":  7, "name": "Archetype Feature",       "desc": "Gain your subclass's Lv 7 feature"},
        {"level":  8, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level":  8, "name": "Land's Stride",           "desc": "Ignore nonmagical difficult terrain; adv vs. impeding plants"},
        {"level": 10, "name": "Natural Explorer (2)",    "desc": "Choose a second favored terrain; Hide in Plain Sight"},
        {"level": 10, "name": "Hide in Plain Sight",     "desc": "Spend 1 min to camouflage: +10 Stealth while stationary"},
        {"level": 11, "name": "Archetype Feature",       "desc": "Gain your subclass's Lv 11 feature"},
        {"level": 12, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 13, "name": "Favored Enemy (3)",       "desc": "Choose a third favored enemy"},
        {"level": 14, "name": "Vanish",                  "desc": "Hide as a bonus action; can't be tracked by non-magical means"},
        {"level": 15, "name": "Archetype Feature",       "desc": "Gain your subclass's Lv 15 feature"},
        {"level": 16, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 18, "name": "Feral Senses",            "desc": "No disadv attacking invisible creatures; sense hidden within 30 ft"},
        {"level": 19, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 20, "name": "Foe Slayer",              "desc": "Once per turn: add WIS mod to attack or dmg roll vs. favored enemy"},
    ],
    "wizard": [
        {"level":  1, "name": "Spellcasting",            "desc": "INT-based spellcasting; copy spells into your spellbook"},
        {"level":  1, "name": "Arcane Recovery",         "desc": "Once per day (short rest): recover spell slots ≤ half wizard level"},
        {"level":  2, "name": "Arcane Tradition",        "desc": "Choose a school subclass: Evocation, Abjuration, Illusion, etc."},
        {"level":  4, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level":  6, "name": "Arcane Tradition Feature","desc": "Gain your school's Lv 6 feature"},
        {"level":  8, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 10, "name": "Arcane Tradition Feature","desc": "Gain your school's Lv 10 feature"},
        {"level": 12, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 14, "name": "Arcane Tradition Feature","desc": "Gain your school's Lv 14 feature"},
        {"level": 16, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 18, "name": "Spell Mastery",           "desc": "Choose one Lv 1 and one Lv 2 spell: cast them without slots"},
        {"level": 19, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 20, "name": "Signature Spell",         "desc": "Two Lv 3 spells castable once per short rest without a slot"},
    ],
    "cleric": [
        {"level":  1, "name": "Spellcasting",            "desc": "WIS-based spellcasting; domain spells always prepared"},
        {"level":  1, "name": "Divine Domain",           "desc": "Choose a domain subclass: Life, Light, Knowledge, War, etc."},
        {"level":  2, "name": "Channel Divinity (1×)",   "desc": "Turn Undead + domain option, once per short rest"},
        {"level":  2, "name": "Domain Feature",          "desc": "Gain your domain's Lv 2 feature"},
        {"level":  4, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level":  5, "name": "Destroy Undead (CR ½)",   "desc": "Turn Undead instantly destroys undead of CR ½ or lower"},
        {"level":  6, "name": "Channel Divinity (2×)",   "desc": "Use Channel Divinity twice per short rest"},
        {"level":  6, "name": "Domain Feature",          "desc": "Gain your domain's Lv 6 feature"},
        {"level":  8, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level":  8, "name": "Destroy Undead (CR 1)",   "desc": "Turn Undead destroys undead of CR 1 or lower"},
        {"level":  8, "name": "Domain Feature",          "desc": "Gain your domain's Lv 8 feature"},
        {"level": 10, "name": "Divine Intervention",     "desc": "Call on your deity; success chance = cleric level %"},
        {"level": 11, "name": "Destroy Undead (CR 2)",   "desc": "Turn Undead destroys undead of CR 2 or lower"},
        {"level": 12, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 14, "name": "Destroy Undead (CR 3)",   "desc": "Turn Undead destroys undead of CR 3 or lower"},
        {"level": 16, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 17, "name": "Destroy Undead (CR 4)",   "desc": "Turn Undead destroys undead of CR 4 or lower"},
        {"level": 17, "name": "Domain Feature",          "desc": "Gain your domain's Lv 17 feature"},
        {"level": 18, "name": "Channel Divinity (3×)",   "desc": "Use Channel Divinity three times per short rest"},
        {"level": 19, "name": "Ability Score Improvement","desc": "+2 to one ability, or +1 to two"},
        {"level": 20, "name": "Divine Intervention",     "desc": "Divine Intervention automatically succeeds"},
    ],
}

# ============================================================================
# RACE TRAITS — passive racial abilities (separate from ability score bonuses).
# ============================================================================

RACE_TRAITS = {
    "human": [
        {"name": "Versatile",          "desc": "+1 to all six ability scores at character creation."},
        {"name": "Extra Language",     "desc": "Know one additional language of your choice."},
        {"name": "Adaptable",          "desc": "One additional skill proficiency of your choice."},
    ],
    "elf": [
        {"name": "Darkvision",         "desc": "See in dim light as bright light; in darkness as dim light, within 60 ft."},
        {"name": "Keen Senses",        "desc": "Proficiency in the Perception skill."},
        {"name": "Fey Ancestry",       "desc": "Advantage on saves vs. charm; immune to magical sleep effects."},
        {"name": "Trance",             "desc": "4 hours of meditation replaces 8 hours of sleep for a long rest."},
    ],
    "dwarf": [
        {"name": "Darkvision",         "desc": "See in dim light as bright light; in darkness as dim light, within 60 ft."},
        {"name": "Dwarven Resilience", "desc": "Advantage on saves vs. poison; resistance to poison damage."},
        {"name": "Stonecunning",       "desc": "Double proficiency bonus on History checks related to stonework."},
        {"name": "Tool Proficiency",   "desc": "Proficiency with one artisan tool (smith's, brewer's, or mason's tools)."},
    ],
    "halfling": [
        {"name": "Lucky",              "desc": "Reroll 1s on attack rolls, ability checks, and saving throws."},
        {"name": "Brave",              "desc": "Advantage on saving throws against being frightened."},
        {"name": "Halfling Nimbleness","desc": "Move through the space of any creature larger than you."},
    ],
    "half_orc": [
        {"name": "Darkvision",         "desc": "See in dim light as bright light; in darkness as dim light, within 60 ft."},
        {"name": "Menacing",           "desc": "Proficiency in the Intimidation skill."},
        {"name": "Relentless Endurance","desc": "Drop to 1 HP instead of 0 once per long rest (not while already at 0)."},
        {"name": "Savage Attacks",     "desc": "On a melee critical hit, roll one additional weapon damage die."},
    ],
    "tiefling": [
        {"name": "Darkvision",         "desc": "See in dim light as bright light; in darkness as dim light, within 60 ft."},
        {"name": "Hellish Resistance", "desc": "Resistance to fire damage."},
        {"name": "Infernal Legacy",    "desc": "Thaumaturgy cantrip; Hellish Rebuke 1×/day at Lv 3; Darkness 1×/day at Lv 5."},
    ],
}

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_DND   = 0x8E44AD  # purple — D&D theme
COLOR_INFO  = 0x5865F2  # blurple
COLOR_WIN   = 0x57F287  # green
COLOR_ERROR = 0xED4245  # red
