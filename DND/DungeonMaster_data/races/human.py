RACE = {
    "id":    "human",
    "name":  "Human",
    "emoji": "🧑",
    "mods":  {
        "strength": 1, "dexterity": 1, "constitution": 1,
        "intelligence": 1, "wisdom": 1, "charisma": 1,
    },
}

TRAITS = [
    {"name": "Versatile",
     "desc": "+1 to all six ability scores."},
    {"name": "Adaptable",
     "desc": "One additional skill proficiency of your choice."},
    {"name": "Extra Language",
     "desc": "Know one additional language of your choice."},
]

# Variant Human (chosen at Lv 1 via LEVEL_UP_CHOICES):
# +1 to two different ability scores of your choice + one feat.
# The feat is the mechanically meaningful part; stored as 'human_feat'.
FEATS = [
    {"id": "alert",
     "label": "Alert",
     "desc": "+5 to initiative — you always act before surprised creatures and cannot be surprised"},
    {"id": "tough",
     "label": "Tough",
     "desc": "+2 HP per level (current and future) — retroactive HP boost applied immediately"},
    {"id": "sharpshooter",
     "label": "Sharpshooter",
     "desc": "Bonus action: enter Sharpshooter stance — next ranged attack is −5 to hit but +10 damage"},
    {"id": "great_weapon_master",
     "label": "Great Weapon Master",
     "desc": "After a crit or a kill, make one extra attack as a bonus action this round"},
]

LEVEL_UP_CHOICES = {
    ("human", 1): {
        "key":    "feat",
        "prompt": "Choose a Feat (Variant Human):",
        "options": FEATS,
    },
}
