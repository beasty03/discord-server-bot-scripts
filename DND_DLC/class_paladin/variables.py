from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ── Class definition ──────────────────────────────────────────────────────────

CLASS = {
    "id":            "paladin",
    "name":          "Paladin",
    "emoji":         "⚔️",
    "hit_die":       10,
    "armor":         6,
    "primary":       "charisma",
    "start_items":   ["longsword", "shield"],
    "weapon_profs":  ["simple", "martial"],
    "armor_profs":   ["light", "medium", "heavy", "shields"],
    "saving_throws": ["wisdom", "charisma"],
}

# ── Lv 1-20 narrative features (shown in /class_upgrade and level-up embeds) ─

CLASS_FEATURES = [
    {"level":  1, "name": "Divine Sense",
     "desc": "Detect celestials, fiends, and undead within 60 ft (1 + CHA mod uses/day)."},
    {"level":  1, "name": "Lay on Hands",
     "desc": "Bonus action: restore HP from a healing pool (5 × level). Once per combat."},
    {"level":  2, "name": "Fighting Style",
     "desc": "Choose a style: Defense (+1 AC), Dueling (+2 dmg 1-handed), Great Weapon (reroll 1s/2s), Protection (shield ally)."},
    {"level":  2, "name": "Spellcasting",
     "desc": "CHA-based. Prepare CHA mod + half paladin level spells per day. Slots: 2 at Lv 2, 3 at Lv 3, etc."},
    {"level":  2, "name": "Divine Smite",
     "desc": "Main action: weapon attack + 2d8 radiant damage; crits deal 4d8."},
    {"level":  3, "name": "Divine Health",
     "desc": "You are immune to disease."},
    {"level":  3, "name": "Sacred Oath",
     "desc": "Choose a subclass: Devotion, Ancients, or Vengeance."},
    {"level":  4, "name": "Ability Score Improvement",
     "desc": "+2 to one ability, or +1 to two."},
    {"level":  5, "name": "Extra Attack",
     "desc": "Attack twice when you take the Attack action."},
    {"level":  5, "name": "Aura of Protection",
     "desc": "You and allies within 10 ft add your CHA mod (min +1) to all saving throws while you are conscious."},
    {"level":  6, "name": "Aura of Courage",
     "desc": "Allies within 10 ft cannot be frightened while you are conscious."},
    {"level":  7, "name": "Sacred Oath Feature",
     "desc": "Gain your subclass's Lv 7 feature."},
    {"level":  8, "name": "Ability Score Improvement",
     "desc": "+2 to one ability, or +1 to two."},
    {"level":  9, "name": "Improved Divine Smite",
     "desc": "All your melee weapon hits deal an extra 1d8 radiant damage automatically."},
    {"level": 10, "name": "Aura of Protection (30 ft)",
     "desc": "Your Aura of Protection now extends to 30 ft."},
    {"level": 11, "name": "Sacred Oath Feature",
     "desc": "Gain your subclass's Lv 11 feature."},
    {"level": 12, "name": "Ability Score Improvement",
     "desc": "+2 to one ability, or +1 to two."},
    {"level": 14, "name": "Cleansing Touch",
     "desc": "End one spell on yourself or a willing ally as an action (CHA mod uses/day)."},
    {"level": 15, "name": "Sacred Oath Feature",
     "desc": "Gain your subclass's Lv 15 feature."},
    {"level": 16, "name": "Ability Score Improvement",
     "desc": "+2 to one ability, or +1 to two."},
    {"level": 17, "name": "Sacred Oath Feature",
     "desc": "Gain your subclass's Lv 17 feature."},
    {"level": 18, "name": "Aura Improvements",
     "desc": "Both Aura of Protection and Aura of Courage now extend to 30 ft."},
    {"level": 19, "name": "Ability Score Improvement",
     "desc": "+2 to one ability, or +1 to two."},
    {"level": 20, "name": "Sacred Oath Capstone",
     "desc": "Gain your Sacred Oath's ultimate feature."},
]

# ── Active combat abilities (main or bonus action, shown in /ability UI) ──────

COMBAT_FEATURES = [
    {"id": "lay_on_hands",    "name": "Lay on Hands",    "label": "✨ Lay on Hands",
     "action_type": "bonus",  "level_req": 1, "once_per": "combat",
     "desc": "Restore 1d8 + CHA mod HP to yourself or an ally (bonus action, once per combat)"},
    {"id": "bless",           "name": "Bless",           "label": "🙏 Bless",
     "action_type": "bonus",  "level_req": 1, "once_per": None,
     "desc": "All living allies gain +1d4 on their next attack roll this round (bonus action)"},
    {"id": "shield_of_faith", "name": "Shield of Faith", "label": "🛡️ Shield of Faith",
     "action_type": "bonus",  "level_req": 2, "once_per": "combat",
     "desc": "+5 AC until the next hit you take this combat (bonus action, once per combat)"},
    {"id": "divine_smite",    "name": "Divine Smite",    "label": "⚡ Divine Smite",
     "action_type": "action", "level_req": 2, "once_per": None,
     "desc": "Weapon attack + 2d8 radiant damage; crits deal 4d8 (main action)"},
    {"id": "holy_light",      "name": "Holy Light",      "label": "☀️ Holy Light",
     "action_type": "action", "level_req": 3, "once_per": None,
     "desc": "Radiant burst — 2d8 + CHA mod, auto-hit (main action)"},
]

# ── Subclass combat features ──────────────────────────────────────────────────

SUBCLASS_COMBAT_FEATURES = {
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

# ── Level-up interactive choices ──────────────────────────────────────────────

LEVEL_UP_CHOICES = {
    ("paladin", 2): {
        "key":    "fighting_style",
        "prompt": "Choose your Fighting Style:",
        "options": [
            {"id": "defense",               "label": "Defense",
             "desc": "+1 AC while wearing armor"},
            {"id": "dueling",               "label": "Dueling",
             "desc": "+2 damage when wielding a melee weapon in one hand (shield is fine)"},
            {"id": "great_weapon_fighting", "label": "Great Weapon Fighting",
             "desc": "Reroll 1s and 2s on weapon damage dice — keep the new result"},
            {"id": "protection",            "label": "Protection",
             "desc": "Reduce damage to an adjacent shield-less ally by up to 3"},
        ],
    },
    ("paladin", 3): {
        "key":    "subclass",
        "prompt": "Choose your Sacred Oath:",
        "options": [
            {"id": "devotion", "label": "Oath of Devotion",
             "desc": "Sacred Weapon — add CHA mod to all attack rolls for a combat (bonus action)"},
            {"id": "ancients", "label": "Oath of the Ancients",
             "desc": "Nature's Wrath — restrain an enemy, −2 ATK next round (bonus action)"},
            {"id": "vengeance","label": "Oath of Vengeance",
             "desc": "Vow of Enmity — advantage on all attacks this combat (bonus action)"},
        ],
    },
}

# ── Weapons (item stat entries — registered with CharacterCog) ────────────────

WEAPONS = [
    {"id": "warhammer",    "name": "Warhammer",    "slot": "weapon",
     "weapon_type": "martial", "ability": "strength", "dmg": "1d8",  "handed": 1},
    {"id": "morningstar",  "name": "Morningstar",  "slot": "weapon",
     "weapon_type": "martial", "ability": "strength", "dmg": "1d8",  "handed": 1},
    {"id": "holy_avenger", "name": "Holy Avenger", "slot": "weapon",
     "weapon_type": "martial", "ability": "strength", "dmg": "2d8",  "handed": 2},
]

# ── Shop listings (what appears in /shop) ─────────────────────────────────────

SHOP_ITEMS = [
    {"id": "warhammer",    "name": "Warhammer",    "emoji": "🔨",
     "description": "A heavy martial weapon. 1d8 bludgeoning, one-handed.",
     "price": 25, "max_qty": 1, "tier": "common"},
    {"id": "morningstar",  "name": "Morningstar",  "emoji": "🪨",
     "description": "Spiked and brutal — 1d8 piercing, one-handed.",
     "price": 35, "max_qty": 1, "tier": "uncommon"},
    {"id": "holy_avenger", "name": "Holy Avenger", "emoji": "⚔️",
     "description": "A blade blessed by the gods — 2d8 slashing, two-handed. Legendary.",
     "price": 1500, "max_qty": 1, "tier": "legendary"},
    {"id": "holy_symbol",  "name": "Holy Symbol",  "emoji": "✝️",
     "description": "A divine focus worn by those sworn to a deity.",
     "price": 15, "max_qty": 1, "tier": "common"},
]
