from pathlib import Path
from utils.config_loader import get_bot_token, load_config
import importlib.util as _ilu

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ── Load structured game data from DungeonMaster_data/ ──────────────────────
def _load(name: str, path: Path):
    spec = _ilu.spec_from_file_location(name, path)
    mod  = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_data_root = Path(__file__).parent.parent / "DungeonMaster_data"
_dm_data   = _load("dm_data", _data_root / "data.py")

# ============================================================================
# ABILITY SCORES
# ============================================================================

ABILITIES = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]

ABILITY_ABBR = {
    "strength":     "STR",
    "dexterity":    "DEX",
    "constitution": "CON",
    "intelligence": "INT",
    "wisdom":       "WIS",
    "charisma":     "CHA",
}

ROLL_METHOD    = "roll"
STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

# ============================================================================
# RACES — Fighter/Human come from DungeonMaster_data; others stay inline until
# they get their own data files.
# ============================================================================

# _OTHER_RACES = [
#     {"id": "halfling", "name": "Halfling", "emoji": "🧒",
#      "mods": {"dexterity": 2, "charisma": 1}},
#     {"id": "half_orc", "name": "Half-Orc", "emoji": "👹",
#      "mods": {"strength": 2, "constitution": 1}},
#     {"id": "tiefling", "name": "Tiefling", "emoji": "😈",
#      "mods": {"charisma": 2, "intelligence": 1}},
# ]

RACES = _dm_data.RACES

# ============================================================================
# CLASSES — Fighter, Ranger, Wizard come from DungeonMaster_data.
# ============================================================================

# _OTHER_CLASSES = [
#     {"id": "barbarian", "name": "Barbarian", "emoji": "🪓", "hit_die": 12, "armor": 2,
#      "primary": "strength",  "start_items": ["greataxe"],               "weapon_profs": ["simple", "martial"]},
#     {"id": "rogue",     "name": "Rogue",     "emoji": "🗡️", "hit_die": 8,  "armor": 1,
#      "primary": "dexterity", "start_items": ["dagger", "leather_armor"],"weapon_profs": ["simple", "longsword", "shortsword", "rapier"]},
#     {"id": "cleric",    "name": "Cleric",    "emoji": "✨", "hit_die": 8,  "armor": 4,
#      "primary": "wisdom",    "start_items": ["mace", "shield"],          "weapon_profs": ["simple"]},
# ]

CLASSES = _dm_data.CLASSES

# ============================================================================
# ITEMS — unchanged; shop, recipes, and scribe depend on this list.
# ============================================================================

ITEMS = [
    {"id": "longsword",     "name": "Longsword",     "slot": "weapon",     "weapon_type": "martial", "ability": "strength",     "dmg": "1d8",  "handed": 1},
    {"id": "shortsword",    "name": "Shortsword",    "slot": "weapon",     "weapon_type": "martial", "ability": "dexterity",    "dmg": "1d6",  "handed": 1},
    {"id": "greataxe",      "name": "Greataxe",      "slot": "weapon",     "weapon_type": "martial", "ability": "strength",     "dmg": "1d12", "handed": 2},
    {"id": "greatsword",    "name": "Greatsword",    "slot": "weapon",     "weapon_type": "martial", "ability": "strength",     "dmg": "2d6",  "handed": 2},
    {"id": "handaxe",       "name": "Handaxe",       "slot": "weapon",     "weapon_type": "simple",  "ability": "strength",     "dmg": "1d6",  "handed": 1},
    {"id": "dagger",        "name": "Dagger",        "slot": "weapon",     "weapon_type": "simple",  "ability": "dexterity",    "dmg": "1d4",  "handed": 1},
    {"id": "shortbow",      "name": "Shortbow",      "slot": "weapon",     "weapon_type": "simple",  "ability": "dexterity",    "dmg": "1d6",  "handed": 2, "ranged": True},
    {"id": "longbow",       "name": "Longbow",       "slot": "weapon",     "weapon_type": "martial", "ability": "dexterity",    "dmg": "1d8",  "handed": 2, "ranged": True},
    {"id": "quarterstaff",  "name": "Quarterstaff",  "slot": "weapon",     "weapon_type": "simple",  "ability": "strength",     "dmg": "1d8",  "handed": 1},
    {"id": "mace",          "name": "Mace",          "slot": "weapon",     "weapon_type": "simple",  "ability": "strength",     "dmg": "1d6",  "handed": 1},
    {"id": "rapier",        "name": "Rapier",        "slot": "weapon",     "weapon_type": "martial", "ability": "dexterity",    "dmg": "1d8",  "handed": 1},
    {"id": "shield",        "name": "Shield",        "slot": "offhand",    "ac_bonus": 2},
    {"id": "leather_armor", "name": "Leather Armor", "slot": "armor"},
    {"id": "chain_mail",    "name": "Chain Mail",    "slot": "armor",      "ac_bonus": 4},
    {"id": "spellbook",     "name": "Spellbook",     "slot": "misc"},
    {"id": "small_health_potion", "name": "Small Health Potion", "emoji": "🧪",
     "slot": "consumable", "heal_expr": "1d4+1",  "tier": "common",   "sell": 8},
    {"id": "health_potion",       "name": "Health Potion",       "emoji": "🧪",
     "slot": "consumable", "heal_expr": "2d4+2",  "tier": "uncommon", "sell": 20},
    {"id": "large_health_potion", "name": "Large Health Potion", "emoji": "🧪",
     "slot": "consumable", "heal_expr": "4d4+4",  "tier": "rare",     "sell": 45},
    {"id": "herb",          "name": "Herb",          "emoji": "🌿", "slot": "material", "tier": "common",   "sell": 3},
    {"id": "leather_scrap", "name": "Leather Scrap", "emoji": "🪶", "slot": "material", "tier": "uncommon", "sell": 5},
    {"id": "arcane_shard",  "name": "Arcane Shard",  "emoji": "💎", "slot": "material", "tier": "rare",     "sell": 15},
    {"id": "recipe_hp_medium", "name": "Recipe: Health Potion",       "emoji": "📜",
     "slot": "recipe", "unlocks": "health_potion",       "sell": 60},
    {"id": "recipe_hp_large",  "name": "Recipe: Large Health Potion", "emoji": "📜",
     "slot": "recipe", "unlocks": "large_health_potion",  "sell": 150},
    {"id": "reroll_token",      "name": "Character Reroll Token", "slot": "misc"},
    {"id": "boar_tusk_charm",   "name": "Boar Tusk Charm",        "slot": "misc"},
    # Beast Master companions — bought from shop, auto-used by Beast Master rangers.
    # best-to-worst checked at combat init; wolf fallback is free (no item needed).
    {"id": "wolf_companion",         "name": "Wolf Companion",         "emoji": "🐺",
     "slot": "companion", "beast_name": "Wolf",        "beast_dmg": "1d6+2", "beast_atk_mod": -2,
     "tier": "common",    "sell": 50},
    {"id": "eagle_companion",        "name": "Eagle Companion",        "emoji": "🦅",
     "slot": "companion", "beast_name": "Eagle",       "beast_dmg": "1d4+3", "beast_atk_mod":  0,
     "tier": "uncommon",  "sell": 110},
    {"id": "bear_companion",         "name": "Bear Companion",         "emoji": "🐻",
     "slot": "companion", "beast_name": "Bear",        "beast_dmg": "1d8+3", "beast_atk_mod": -1,
     "tier": "rare",      "sell": 200},
    {"id": "baby_dragon_companion",  "name": "Baby Dragon Companion",  "emoji": "🐉",
     "slot": "companion", "beast_name": "Baby Dragon", "beast_dmg": "2d6+4", "beast_atk_mod":  0,
     "tier": "legendary", "sell": 750},
    # Wizard spell scrolls — consumed by /learn_spell to permanently teach the spell.
    {"id": "scroll_misty_step",    "name": "Scroll of Misty Step",    "emoji": "📜",
     "slot": "spell_scroll", "teaches": "misty_step",    "tier": "rare",  "sell": 140},
    {"id": "scroll_scorching_ray", "name": "Scroll of Scorching Ray",  "emoji": "📜",
     "slot": "spell_scroll", "teaches": "scorching_ray",  "tier": "rare",  "sell": 110},
    {"id": "scroll_fireball",      "name": "Scroll of Fireball",       "emoji": "📜",
     "slot": "spell_scroll", "teaches": "fireball",        "tier": "epic",  "sell": 280},
    {"id": "scroll_counterspell",  "name": "Scroll of Counterspell",   "emoji": "📜",
     "slot": "spell_scroll", "teaches": "counterspell",    "tier": "epic",  "sell": 220},
]

# ============================================================================
# LEVELING
# ============================================================================

REST_COST = 10

XP_THRESHOLDS = [
    0, 0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000,
    85000, 100000, 120000, 140000, 165000, 195000, 225000, 265000, 305000, 355000,
]
MAX_LEVEL = 20

# ============================================================================
# CLASS FEATURES — Fighter from data file; others stay inline.
# ============================================================================

CLASS_FEATURES = {
    **_dm_data.CLASS_FEATURES,
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
# RACE TRAITS — Human from data file; others stay inline.
# ============================================================================

RACE_TRAITS = {
    **_dm_data.RACE_TRAITS,
    "halfling": [
        {"name": "Lucky",              "desc": "Reroll 1s on attack rolls, ability checks, and saving throws."},
        {"name": "Brave",              "desc": "Advantage on saving throws against being frightened."},
        {"name": "Halfling Nimbleness","desc": "Move through the space of any creature larger than you."},
    ],
    "half_orc": [
        {"name": "Darkvision",          "desc": "See in dim light as bright light; in darkness as dim light, within 60 ft."},
        {"name": "Menacing",            "desc": "Proficiency in the Intimidation skill."},
        {"name": "Relentless Endurance","desc": "Drop to 1 HP instead of 0 once per long rest (not while already at 0)."},
        {"name": "Savage Attacks",      "desc": "On a melee critical hit, roll one additional weapon damage die."},
    ],
    "tiefling": [
        {"name": "Darkvision",       "desc": "See in dim light as bright light; in darkness as dim light, within 60 ft."},
        {"name": "Hellish Resistance","desc": "Resistance to fire damage."},
        {"name": "Infernal Legacy",  "desc": "Thaumaturgy cantrip; Hellish Rebuke 1×/day at Lv 3; Darkness 1×/day at Lv 5."},
    ],
}

# ============================================================================
# COMBAT FEATURES — Fighter from data file; others stay inline.
# ============================================================================

COMBAT_FEATURES = {
    **_dm_data.COMBAT_FEATURES,
    "barbarian": [
        {"id": "rage", "name": "Rage", "label": "💢 Rage",
         "action_type": "bonus", "level_req": 1, "once_per": "combat",
         "desc": "Enter rage — ×2 damage all combat (bonus action)"},
    ],
    "rogue": [
        {"id": "sneak_attack",   "name": "Sneak Attack",   "label": "🗡️ Sneak Attack",
         "action_type": "action", "level_req": 1, "once_per": None,
         "desc": "Attack + 1d6 per 2 levels bonus damage (main action)"},
        {"id": "cunning_action", "name": "Cunning Action", "label": "🕵️ Cunning Action",
         "action_type": "bonus",  "level_req": 2, "once_per": None,
         "desc": "Dodge as a bonus action — halve enemy damage this round"},
    ],
    "cleric": [
        {"id": "sacred_flame", "name": "Sacred Flame", "label": "🔥 Sacred Flame",
         "action_type": "action", "level_req": 1, "once_per": None,
         "desc": "Radiant blast — 1d8 + WIS, auto-hit (main action)"},
        {"id": "lay_on_hands", "name": "Lay on Hands", "label": "✨ Lay on Hands",
         "action_type": "bonus",  "level_req": 1, "once_per": "combat",
         "desc": "Restore 1d8 + WIS HP to yourself or an ally (bonus action)"},
        {"id": "healing_word", "name": "Healing Word",  "label": "🙏 Healing Word",
         "action_type": "bonus",  "level_req": 2, "once_per": None,
         "desc": "Heal yourself or an ally 1d4 + WIS HP (bonus action)"},
    ],
    "paladin": [
        {"id": "lay_on_hands", "name": "Lay on Hands", "label": "✨ Lay on Hands",
         "action_type": "bonus",  "level_req": 1, "once_per": "combat",
         "desc": "Restore 1d8 + CHA HP to yourself or an ally (bonus action)"},
        {"id": "divine_smite", "name": "Divine Smite",  "label": "⚡ Divine Smite",
         "action_type": "action", "level_req": 2, "once_per": None,
         "desc": "Attack + 2d8 radiant damage; crits deal 4d8 (main action)"},
    ],
}

# ============================================================================
# SUBCLASS COMBAT FEATURES — Fighter subclasses from data file; others inline.
# ============================================================================

SUBCLASS_COMBAT_FEATURES = {
    **_dm_data.SUBCLASS_COMBAT_FEATURES,
    "berserker": [
        {"id": "frenzy_attack", "name": "Frenzy", "label": "🔥 Frenzy",
         "action_type": "bonus", "level_req": 3, "once_per": "combat",
         "desc": "Extra melee attack while raging — rage damage applies (once per combat)"},
    ],
    "totem_warrior":    [],
    "thief":            [],
    "assassin":         [],
    "arcane_trickster": [
        {"id": "mage_hand", "name": "Mage Hand", "label": "🎩 Mage Hand",
         "action_type": "bonus", "level_req": 3, "once_per": "combat",
         "desc": "Distract the enemy — they attack with disadvantage next hit (once per combat)"},
    ],
    "life":         [],
    "light":        [],
    "knowledge":    [],
    "war": [
        {"id": "guided_strike", "name": "Guided Strike", "label": "✝️ Guided Strike",
         "action_type": "bonus", "level_req": 1, "once_per": "combat",
         "desc": "+10 to your next attack roll (once per combat)"},
    ],
    "devotion": [
        {"id": "sacred_weapon", "name": "Sacred Weapon", "label": "✨ Sacred Weapon",
         "action_type": "bonus", "level_req": 3, "once_per": "combat",
         "desc": "Add CHA mod to all attack rolls for the rest of combat (once per combat)"},
    ],
    "ancients": [
        {"id": "natures_wrath", "name": "Nature's Wrath", "label": "🌿 Nature's Wrath",
         "action_type": "bonus", "level_req": 3, "once_per": "combat",
         "desc": "Restrain the enemy — they attack at −2 next round (once per combat)"},
    ],
    "vengeance": [
        {"id": "vow_of_enmity", "name": "Vow of Enmity", "label": "⚡ Vow of Enmity",
         "action_type": "bonus", "level_req": 3, "once_per": "combat",
         "desc": "Advantage on all attacks this combat (once per combat)"},
    ],
}

# ============================================================================
# LEVEL-UP CHOICES — Fighter+Human from data file; others inline.
# ============================================================================

LEVEL_UP_CHOICES = {
    **_dm_data.LEVEL_UP_CHOICES,
    ("barbarian", 3): {
        "key": "subclass", "prompt": "Choose your Primal Path:",
        "options": [
            {"id": "berserker",    "label": "Berserker",    "desc": "Frenzy — extra melee attack as bonus action while raging"},
            {"id": "totem_warrior","label": "Totem Warrior","desc": "Spirit totems — Bear (resistance), Eagle (mobility), Wolf (pack)"},
        ],
    },
    ("rogue", 3): {
        "key": "subclass", "prompt": "Choose your Roguish Archetype:",
        "options": [
            {"id": "thief",           "label": "Thief",           "desc": "Fast Hands — bonus-action item use and object interaction"},
            {"id": "assassin",        "label": "Assassin",        "desc": "Crit on surprised creatures; create convincing false identities"},
            {"id": "arcane_trickster","label": "Arcane Trickster","desc": "INT-based wizard spells; Mage Hand Legerdemain pickpocket"},
        ],
    },
    ("cleric", 1): {
        "key": "subclass", "prompt": "Choose your Divine Domain:",
        "options": [
            {"id": "life",     "label": "Life",     "desc": "Heals restore extra HP — Disciple of Life"},
            {"id": "light",    "label": "Light",    "desc": "Warding Flare — impose disadvantage on an incoming attack"},
            {"id": "knowledge","label": "Knowledge","desc": "Extra languages, tool proficiencies, and arcane insight"},
            {"id": "war",      "label": "War",      "desc": "Guided Strike +10 to hit; War God's Blessing reaction"},
        ],
    },
    ("paladin", 3): {
        "key": "subclass", "prompt": "Choose your Sacred Oath:",
        "options": [
            {"id": "devotion", "label": "Oath of Devotion",    "desc": "Sacred Weapon; Turn the Unholy — channel radiant energy"},
            {"id": "ancients", "label": "Oath of the Ancients","desc": "Nature's Wrath; Turn the Faithless — preserve the ancient light"},
            {"id": "vengeance","label": "Oath of Vengeance",   "desc": "Vow of Enmity — advantage on attacks against one chosen foe"},
        ],
    },
}

# ============================================================================
# SHEET DELETION 
# ============================================================================

DELETION_COOLDOWN_DAYS = 0

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_DND   = 0x8E44AD
COLOR_INFO  = 0x5865F2
COLOR_WIN   = 0x57F287
COLOR_ERROR = 0xED4245

# ── Wizard spell data (re-exported from data.py for engine access) ────────────
WIZARD_CANTRIPS:        set[str]   = _dm_data.WIZARD_CANTRIPS
WIZARD_STARTING_SPELLS: list[str]  = _dm_data.WIZARD_STARTING_SPELLS
WIZARD_SPELLS:          list[dict] = _dm_data.WIZARD_SPELLS
