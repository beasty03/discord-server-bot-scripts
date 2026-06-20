from DND.DungeonMaster.effects import Flag, Heal, Message, Modify, Status


def register(api):

    # ── Campaign-exclusive items ───────────────────────────────────────────────

    api.add_item({
        "id":          "stolen_coin_pouch",
        "name":        "Stolen Coin Pouch",
        "emoji":       "💰",
        "slot":        "misc",
        "tier":        "common",
        "sell":        17,
        "description": "A grubby pouch of stolen coins — 10 to 25 gold worth. Sell it to collect.",
    })

    api.add_item({
        "id":          "goblin_scimitar",
        "name":        "Goblin Scimitar",
        "emoji":       "⚔️",
        "slot":        "weapon",
        "weapon_type": "simple",
        "ability":     "dexterity",
        "dmg":         "1d6",
        "handed":      1,
        "tier":        "common",
        "sell":        8,
        "description": "A crude curved blade taken from a scummy goblin. Battered but serviceable.",
    })

    api.add_item({
        "id":          "dire_wolf_fang",
        "name":        "Dire Wolf Fang",
        "emoji":       "🦷",
        "slot":        "misc",
        "tier":        "common",
        "sell":        12,
        "description": "A razor-sharp fang from a dire wolf. Useful for crafting or as a trophy.",
    })

    # Boss drop ────────────────────────────────────────────────────────────────
    api.define_damage_type("necrotic", label="Necrotic", icon="💀")

    api.define_status(
        "soul_drain",
        label="Soul Drain",
        icon="💀",
        effects={
            "enemy_atk_penalty": 2,
            "clears_on_turn":    True,
        },
    )

    def _wraith_blade_on_hit(ctx):
        if ctx.has_flag("wraith_blade_drained"):
            return []
        n = ctx.roll("1d6")
        return [
            Modify("damage", add=n, damage_type="necrotic"),
            Heal(2),
            Flag("wraith_blade_drained", True),
            Status("soul_drain", 1),
            Message(f"🗡️ Wraith Blade drains the soul — +{n} necrotic, heal 2 HP, enemy −2 ATK!"),
        ]

    api.add_item({
        "id":          "wraith_blade",
        "name":        "Wraith Blade",
        "emoji":       "🗡️",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "dexterity",
        "dmg":         "1d8",
        "handed":      1,
        "tier":        "epic",
        "sell":        350,
        "description": "A blade honed by dark magic. Once per combat: +1d6 necrotic, heal 2 HP, enemy −2 ATK.",
        "on_hit":      _wraith_blade_on_hit,
    })

    # ── Campaign ───────────────────────────────────────────────────────────────

    api.add_campaign({
        "id":              "the_mayors_request",
        "name":            "The Mayor's Request",
        "emoji":           "🏛️",
        "min_level":       1,
        "min_players":     1,
        "max_players":     4,
        "difficulty":      "Easy",
        "intro": (
            "The mayor of Millvale catches you at the tavern door, voice low and urgent. "
            "'A goblin has been preying on our roads for weeks — merchants robbed, carts overturned, "
            "one man came back without his boots. The beast lairs in a cave east of the mill road. "
            "Clear it out, and I'll see you paid.' "
            "He slides a coin purse across the table. You finish your drink and head east."
        ),
        "reward_gold_min": 40,
        "reward_gold_max": 80,
        "reward_xp":       120,
        "encounters": [

            # ── 1. The Forest Path ───────────────────────────────────────────
            {
                "type":  "combat",
                "name":  "The Forest Path",
                "intro": (
                    "The trail east of Millvale cuts through dense woodland before it reaches the cave. "
                    "You're halfway through when something large steps out from between the trees — "
                    "a dire wolf, fur matted and yellow eyes fixed on you. "
                    "It doesn't growl. It just lowers its head and charges."
                ),
                "enemy": {
                    "name":       "Dire Wolf",
                    "emoji":      "🐺",
                    "hp":         24,
                    "ac":         13,
                    "atk_bonus":  4,
                    "dmg":        "1d8+2",
                    "initiative": 5,
                    "drops": [
                        {"id": "small_health_potion", "chance": 10},
                        {"id": "dire_wolf_fang", "chance": 40},
                    ],
                },
            },

            # ── 2. The Goblin's Cave ──────────────────────────────────────────
            {
                "type":        "interaction",
                "name":        "The Goblin's Cave",
                "intro": (
                    "A narrow cave entrance splits the hillside ahead, rank with the smell of old "
                    "meat and burnt wood. Inside, firelight flickers. You can hear a goblin muttering "
                    "to itself, counting something — coins, maybe. It hasn't heard you yet."
                ),
                "skill":        "dexterity",
                "skill_label":  "🤫 Creep up on the goblin",
                "dc":           11,
                "success_text": (
                    "You move low and quiet along the cave wall, keeping to the shadows. "
                    "The goblin is hunched over a pile of stolen goods, back to you, still counting. "
                    "You close the distance fast — and catch it completely off guard."
                ),
                "failure_text": (
                    "Your boot scrapes loose gravel. The goblin spins around with a shriek, "
                    "snatching up its blade. 'YOU! Not supposed to be HERE!'"
                ),
                "combat_fallback": {
                    "name":       "Skrix the Cave Goblin",
                    "emoji":      "👺",
                    "hp":         14,
                    "ac":         11,
                    "atk_bonus":  2,
                    "dmg":        "1d4+1",
                    "initiative": 4,
                    "drops": [
                        {"id": "stolen_coin_pouch",   "chance": 80},
                        {"id": "goblin_scimitar",     "chance": 45},
                        {"id": "small_health_potion", "chance": 35},
                    ],
                },
            },

            # ── 3. The Back Chamber ───────────────────────────────────────────
            {
                "type":  "choice",
                "name":  "The Back Chamber",
                "intro": (
                    "Deeper in, past the goblin's fire pit and its picked-clean meal scraps, the cave "
                    "narrows then opens into a small natural chamber. The air here is colder. "
                    "At the center, balanced on a flat stone like a deliberate offering, sits a gem — "
                    "the size of a fist, deep violet, glowing faintly with a light that shifts when "
                    "you move. Whatever the goblin was guarding, it was this."
                ),
                "options": [
                    {
                        "id":          "take",
                        "label":       "💎 Take the gem",
                        "result_text": (
                            "The gem is warm. Almost alive, pulsing gently against your palm "
                            "like a slow heartbeat. You tuck it into your pack — a fine bonus "
                            "on top of the mayor's coin.\n\n"
                            "Then the shadows at the back of the chamber thicken. "
                            "And something steps out of them."
                        ),
                        "encounters": [
                            {
                                "type":  "combat",
                                "name":  "The Hollow King",
                                "intro": "The darkness takes shape. Two pale eyes open in the black.",
                                "enemy": {
                                    "name":       "The Hollow King",
                                    "emoji":      "👁️",
                                    "hp":         90,
                                    "ac":         16,
                                    "atk_bonus":  7,
                                    "dmg":        "2d8+4",
                                    "initiative": 8,
                                    "drops": [
                                        {"id": "wraith_blade",        "chance": 60},
                                        {"id": "large_health_potion", "chance": 70},
                                        {"id": "health_potion",       "chance": 90},
                                    ],
                                },
                            },
                        ],
                    },
                    {
                        "id":          "leave",
                        "label":       "🚪 Leave it and head back",
                        "result_text": (
                            "Something about it makes you hesitate. The glow doesn't quite behave "
                            "like reflected torchlight. You pull your hand back and walk away. "
                            "The mayor wanted the goblin dealt with — that's done."
                        ),
                        "encounters": [],
                    },
                ],
            },

        ],
    })
