def register(api):
    api.add_campaign({
        "id":              "a_farmers_trouble",
        "name":            "A Farmer's Trouble",
        "emoji":           "🌾",
        "min_level":       1,
        "min_players":     1,
        "max_players":     4,
        "difficulty":      "Easy",
        "intro": (
            "A red-faced farmer stops you outside the village inn, hat in hand. "
            "'Please — they've taken everything. Goblins, in the wheat field, every night for a week. "
            "There's a cave not far from here, east of the field. That's where they're holed up.' "
            "He presses a handful of copper into your palm and promises more if you clear them out. "
            "The cave can't be far. You set off at dusk."
        ),
        "reward_gold_min": 15,
        "reward_gold_max": 45,
        "reward_xp":       100,
        "encounters": [

            {
                "type":  "combat",
                "name":  "The Wheat Field",
                "intro": (
                    "The field is half-destroyed — stalks trampled, grain scattered across the dirt. "
                    "Two goblin scouts are still here, stuffing grain sacks and cackling to each other. "
                    "They spot you before you can reach the tree line and raise their rusty blades."
                ),
                "enemy": {
                    "name":       "Goblin Scouts",
                    "emoji":      "👺",
                    "hp":         18,
                    "ac":         12,
                    "atk_bonus":  2,
                    "dmg":        "1d4+1",
                    "initiative": 3,
                    "drops":      [],
                },
            },

            {
                "type":        "interaction",
                "name":        "The Cave Entrance",
                "intro": (
                    "A narrow crack in the hillside opens into a low cave — firelight flickers inside "
                    "and you can hear goblins laughing. A lone lookout sits just inside the entrance, "
                    "picking his teeth. You could try to slip past him before he raises the alarm."
                ),
                "skill":       "dexterity",
                "skill_label": "🤫 Sneak past the lookout",
                "dc":          10,
                "success_text": (
                    "You press flat against the cave wall and inch past the lookout. "
                    "He stares at the fire and never turns around. "
                    "You slip into the den undetected — they won't see you coming."
                ),
                "failure_text": (
                    "A loose pebble skitters under your boot. The lookout whips around, "
                    "screams something in Goblin, and lunges at you."
                ),
                "combat_fallback": {
                    "name":       "Goblin Lookout",
                    "emoji":      "👺",
                    "hp":         14,
                    "ac":         12,
                    "atk_bonus":  2,
                    "dmg":        "1d4+1",
                    "initiative": 4,
                    "drops":      [],
                },
            },

            {
                "type":  "combat",
                "name":  "The Goblin Den",
                "intro": (
                    "The cave opens into a filthy den — stolen grain sacks piled in the corner, "
                    "a fire pit in the middle, and goblins everywhere. Their number matches your party: "
                    "at least two, and they all look angry. Their leader shoves the others forward "
                    "and points a rusty blade straight at you."
                ),
                "enemy": {
                    "name":       "Goblin Pack",
                    "emoji":      "👺",
                    "hp":         28,
                    "ac":         12,
                    "atk_bonus":  3,
                    "dmg":        "1d6+2",
                    "initiative": 2,
                    "drops":      [],
                },
            },

        ],
    })
