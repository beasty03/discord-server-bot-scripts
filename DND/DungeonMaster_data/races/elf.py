RACE = {
    "id":    "elf",
    "name":  "Elf",
    "emoji": "🧝",
    "mods":  {
        "dexterity":    2,
        "intelligence": 1,
    },
}

TRAITS = [
    {"name": "Darkvision",
     "desc": "See in dim light as bright light and in darkness as dim light, within 60 ft."},
    {"name": "Keen Senses",
     "desc": "Proficiency in the Perception skill — sharper eyes and ears than most."},
    {"name": "Fey Ancestry",
     "desc": "Advantage on saving throws vs. charm; immune to magical sleep effects."},
    {"name": "Trance",
     "desc": "4 hours of elven meditation replaces 8 hours of sleep for a long rest."},
]

# Chosen at Lv 1 via LEVEL_UP_CHOICES — stored as 'elf_subrace'.
RACIAL_FEATURES = [
    {"id": "high_elf",
     "label": "High Elf",
     "desc": "+1 Intelligence — arcane attunement enhances spell attack rolls and INT-based abilities"},
    {"id": "wood_elf",
     "label": "Wood Elf",
     "desc": "+1 Dexterity — forest-born reflexes sharpen your DEX-based attack rolls and AC"},
]

LEVEL_UP_CHOICES = {
    ("elf", 1): {
        "key":    "subrace",
        "prompt": "Choose your Elven Heritage:",
        "options": RACIAL_FEATURES,
    },
}
