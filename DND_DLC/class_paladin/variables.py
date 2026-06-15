from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

CLASS = {
    "id":          "paladin",
    "name":        "Paladin",
    "emoji":       "⚡",
    "hit_die":     10,
    "armor":       6,
    "primary":     "strength",
    "start_items": ["longsword", "shield", "holy_symbol"],
    "weapon_profs": ["simple", "martial"],
    "features": [
        {"level":  1, "name": "Divine Sense",            "desc": "Detect celestials, fiends, and undead within 60 ft. Uses = 1 + CHA mod per day."},
        {"level":  1, "name": "Lay on Hands",            "desc": "Healing pool = 5 × paladin level. Restore HP as an action; or cure one disease/poison for 5 HP."},
        {"level":  2, "name": "Fighting Style",          "desc": "Pick a style: Defence (+1 AC in armor), Dueling (+2 dmg one-handed), Great Weapon (reroll 1s/2s), Protection (impose disadv on attacks vs. ally)."},
        {"level":  2, "name": "Spellcasting",            "desc": "CHA-based spellcasting. Prepare CHA mod + half paladin level spells per day."},
        {"level":  2, "name": "Divine Smite",            "desc": "Expend a spell slot on a melee hit: 2d8 radiant (+1d8 per slot level above 1st, max 5d8). +1d8 vs. undead/fiends."},
        {"level":  3, "name": "Divine Health",           "desc": "Immune to disease."},
        {"level":  3, "name": "Sacred Oath",             "desc": "Choose a subclass: Devotion, Ancients, Vengeance, or Conquest."},
        {"level":  4, "name": "Ability Score Improvement", "desc": "+2 to one ability, or +1 to two."},
        {"level":  5, "name": "Extra Attack",            "desc": "Attack twice when you take the Attack action."},
        {"level":  5, "name": "Aura of Protection",     "desc": "Allies within 10 ft (including you) add CHA mod (min +1) to all saving throws while you are conscious."},
        {"level":  6, "name": "Aura of Courage",        "desc": "Allies within 10 ft can't be frightened while you are conscious."},
        {"level":  7, "name": "Sacred Oath Feature",    "desc": "Gain your subclass's Lv 7 feature."},
        {"level":  8, "name": "Ability Score Improvement", "desc": "+2 to one ability, or +1 to two."},
        {"level":  9, "name": "Improved Divine Smite",  "desc": "All melee weapon hits deal an extra 1d8 radiant damage."},
        {"level": 10, "name": "Aura of Protection (30 ft)", "desc": "Aura of Protection extends to 30 ft."},
        {"level": 11, "name": "Sacred Oath Feature",    "desc": "Gain your subclass's Lv 11 feature."},
        {"level": 12, "name": "Ability Score Improvement", "desc": "+2 to one ability, or +1 to two."},
        {"level": 14, "name": "Cleansing Touch",        "desc": "End one spell on yourself or a willing ally as an action. Uses = CHA mod per day."},
        {"level": 15, "name": "Sacred Oath Feature",    "desc": "Gain your subclass's Lv 15 feature."},
        {"level": 16, "name": "Ability Score Improvement", "desc": "+2 to one ability, or +1 to two."},
        {"level": 17, "name": "Sacred Oath Feature",    "desc": "Gain your subclass's Lv 17 feature."},
        {"level": 18, "name": "Aura Improvements",      "desc": "Aura of Protection and Aura of Courage both extend to 30 ft."},
        {"level": 19, "name": "Ability Score Improvement", "desc": "+2 to one ability, or +1 to two."},
        {"level": 20, "name": "Sacred Oath Capstone",   "desc": "Gain your Sacred Oath's ultimate feature."},
    ],
}
