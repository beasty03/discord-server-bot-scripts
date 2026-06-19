def register(api):
    api.add_campaign({
        "id":              "the_lonely_ice_mountain",
        "name":            "The Lonely Ice Mountain",
        "emoji":           "🧊",
        "min_level":       4,
        "min_players":     2,
        "max_players":     4,
        "difficulty":      "Hard",
        "intro": (
            "A small village at the foot of a frozen mountain has been terrorized by violent "
            "storms and lightning strikes for weeks — all originating from the peak above. "
            "The local barman pulls you aside with desperate eyes: 'Scale that mountain and "
            "find out what's up there. I'll make it worth your while.' The climb begins in bitter cold."
        ),
        "reward_gold_min": 120,
        "reward_gold_max": 280,
        "reward_xp":       350,
        "encounters": [

            {
                "type":  "combat",
                "name":  "Base of the Mountain",
                "intro": (
                    "The trail up the mountain starts quiet — too quiet. Then two massive dire wolves "
                    "burst from behind a snowdrift, fangs bared, fur matted with ice. They're starving "
                    "and you're in their way."
                ),
                "enemy": {
                    "name":       "Dire Wolf Pack",
                    "emoji":      "🐺",
                    "hp":         36,
                    "ac":         13,
                    "atk_bonus":  4,
                    "dmg":        "1d10+3",
                    "initiative": 2,
                    "drops": [
                        {"id": "leather_scrap", "chance": 40},
                    ],
                },
            },

            {
                "type":        "interaction",
                "name":        "The Fallen Boulder",
                "intro": (
                    "Halfway up the mountain path, a massive boulder has tumbled across the trail — "
                    "easily two tonnes of frozen rock. The wind howls around it. You could try to "
                    "muscle it aside, or pick your way around through the ice shelf."
                ),
                "skill":       "strength",
                "skill_label": "💪 Heave the Boulder",
                "dc":          14,
                "success_text": (
                    "With a thunderous grunt the boulder grinds aside, opening the path. "
                    "Your arms ache but the way forward is clear."
                ),
                "failure_text": (
                    "The boulder doesn't budge. You take the long way around — "
                    "and something in the ice ahead begins to move."
                ),
                "combat_fallback": {
                    "name":       "Ice Golem",
                    "emoji":      "🧊",
                    "hp":         52,
                    "ac":         15,
                    "atk_bonus":  5,
                    "dmg":        "1d10+4",
                    "initiative": 1,
                    "drops": [
                        {"id": "arcane_shard", "chance": 25},
                    ],
                },
            },

            {
                "type":  "combat",
                "name":  "Summit — The Storm Giant",
                "intro": (
                    "At the peak, the clouds split apart to reveal the source of it all. "
                    "A giant of immense size stands at the summit, a warhammer crackling with "
                    "lightning raised above its head. Its eyes burn electric blue. "
                    "It turns to face you — and the storm intensifies."
                ),
                "enemy": {
                    "name":       "Storm Giant",
                    "emoji":      "⚡",
                    "hp":         85,
                    "ac":         16,
                    "atk_bonus":  7,
                    "dmg":        "2d8+5",
                    "initiative": 3,
                    "drops": [
                        {"id": "storm_breaker", "chance": 20},
                        {"id": "arcane_shard",  "chance": 35},
                        {"id": "herb",          "chance": 25},
                    ],
                },
            },

        ],
    })
