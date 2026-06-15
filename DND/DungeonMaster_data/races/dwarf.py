RACE = {
    "id":    "dwarf",
    "name":  "Dwarf",
    "emoji": "🧔",
    "mods":  {
        "constitution": 2,
        "strength":     1,
    },
}

TRAITS = [
    {"name": "Darkvision",
     "desc": "See in dim light as bright light and in darkness as dim light, within 60 ft."},
    {"name": "Dwarven Resilience",
     "desc": "Advantage on saving throws vs. poison; resistance to poison damage."},
    {"name": "Stonecunning",
     "desc": "Double proficiency bonus on History checks related to stone or stonework."},
    {"name": "Tool Proficiency",
     "desc": "Proficiency with one artisan's tool (smith's, brewer's, or mason's tools)."},
]

# Chosen at Lv 1 via LEVEL_UP_CHOICES — stored as 'dwarf_trait'.
RACIAL_FEATURES = [
    {"id": "dwarven_toughness",
     "label": "Dwarven Toughness",
     "desc": "+1 max HP per character level — applied immediately and at every future level-up"},
    {"id": "battle_born",
     "label": "Battle-Born",
     "desc": "+1 to all melee attack rolls — ingrained Dwarven combat heritage"},
]

LEVEL_UP_CHOICES = {
    ("dwarf", 1): {
        "key":    "trait",
        "prompt": "Choose your Dwarven Heritage:",
        "options": RACIAL_FEATURES,
    },
}
