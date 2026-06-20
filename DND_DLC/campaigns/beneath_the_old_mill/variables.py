def register(api):
    from DND.DungeonMaster.effects import Heal, Message, Modify

    # ── Campaign-exclusive items ───────────────────────────────────────────────

    api.add_item({
        "id":          "iron_key",
        "name":        "Iron Key",
        "emoji":       "🗝️",
        "slot":        "misc",
        "tier":        "common",
        "sell":        0,
        "description": "A tarnished iron key taken from the kobold captain. Opens the sealed gate.",
    })

    def _amulet_fortitude_on_take_damage(ctx):
        return [Heal(2), Message("🔮 Amulet of Fortitude pulses — restores 2 HP!")]

    api.add_item({
        "id":          "amulet_of_fortitude",
        "name":        "Amulet of Fortitude",
        "emoji":       "🔮",
        "slot":        "accessory",
        "tier":        "uncommon",
        "sell":        90,
        "description": "A warm amber amulet. Restores 2 HP each time you are struck.",
        "on_take_damage": _amulet_fortitude_on_take_damage,
    })

    def _wolf_fang_on_damage_roll(ctx):
        return [Modify("damage", add=1), Message("🦷 Wolf Fang: +1 damage!")]

    api.add_item({
        "id":          "wolf_fang_necklace",
        "name":        "Wolf Fang Necklace",
        "emoji":       "🦷",
        "slot":        "accessory",
        "tier":        "common",
        "sell":        50,
        "description": "A necklace strung with dire wolf fangs. Adds +1 to every damage roll.",
        "on_damage_roll": _wolf_fang_on_damage_roll,
    })

    api.add_item({
        "id":          "scroll_burning_hands",
        "name":        "Scroll of Burning Hands",
        "emoji":       "📜",
        "slot":        "spell_scroll",
        "teaches":     "burning_hands",
        "tier":        "common",
        "sell":        25,
        "description": "Teaches a Wizard the Burning Hands spell (3d6 fire cone).",
    })

    api.add_item({
        "id":          "scroll_shield_spell",
        "name":        "Scroll of Shield",
        "emoji":       "📜",
        "slot":        "spell_scroll",
        "teaches":     "shield_spell",
        "tier":        "common",
        "sell":        25,
        "description": "Teaches a Wizard the Shield spell (+5 AC vs the next hit, bonus action).",
    })

    # ── Campaign ───────────────────────────────────────────────────────────────

    api.add_campaign({
        "id":              "beneath_the_old_mill",
        "name":            "Beneath the Old Mill",
        "emoji":           "🏚️",
        "min_level":       2,
        "min_players":     2,
        "max_players":     4,
        "difficulty":      "Medium",
        "intro": (
            "Word has reached Millhaven: the merchant Aldric was taken underground by kobold raiders "
            "nesting beneath the old mill on the edge of town. A ransom note arrived at dawn — "
            "you aren't paying it. You light your torches, pry open the hatch behind the mill wheel, "
            "and drop into the dark. Skittering claws echo somewhere below."
        ),
        "reward_gold_min": 150,
        "reward_gold_max": 300,
        "reward_xp":       280,
        "encounters": [

            # ── 1. Entry Shaft ────────────────────────────────────────────────
            {
                "type":  "combat",
                "name":  "The Entry Shaft",
                "intro": (
                    "You land in a torchlit stone corridor still damp from the millstream above. "
                    "Three kobold sentries spin around, rusted daggers already drawn. "
                    "One of them opens its mouth to screech — you can't let that alarm reach the rest."
                ),
                "enemy": {
                    "name":       "Kobold Sentries",
                    "emoji":      "🐊",
                    "hp":         30,
                    "ac":         12,
                    "atk_bonus":  4,
                    "dmg":        "1d4+2",
                    "initiative": 14,
                    "drops": [
                        {"id": "small_health_potion", "chance": 65},
                        {"id": "dagger",              "chance": 35},
                    ],
                },
            },

            # ── 2. Guard Barracks ─────────────────────────────────────────────
            {
                "type":  "combat",
                "name":  "The Guard Barracks",
                "intro": (
                    "A low room reeking of rotting meat and damp fur. Straw pallets cover the floor — "
                    "and four kobolds on them are very much awake. One heaves a javelin before you "
                    "even clear the doorway. These were the ones who dragged Aldric down here."
                ),
                "enemy": {
                    "name":       "Kobold Pack",
                    "emoji":      "🐊",
                    "hp":         40,
                    "ac":         12,
                    "atk_bonus":  4,
                    "dmg":        "1d6+2",
                    "initiative": 12,
                    "drops": [
                        {"id": "scroll_burning_hands", "chance": 30},
                        {"id": "handaxe",              "chance": 35},
                        {"id": "small_health_potion",  "chance": 50},
                    ],
                },
            },

            # ── 3. The Dark Passage ───────────────────────────────────────────
            {
                "type":        "interaction",
                "name":        "The Dark Passage",
                "intro": (
                    "The corridor narrows until you're walking single file. "
                    "The torchlight barely reaches the floor, and the stone looks uneven ahead — "
                    "or is that just shadows? Something about the air pressure feels wrong."
                ),
                "skill":        "wisdom",
                "skill_label":  "👁️ Perception",
                "dc":           13,
                "success_text": (
                    "Sharp eyes save the group. You spot a pressure plate hidden under a thin "
                    "scatter of gravel, wire running up to a log suspended above the passage. "
                    "You point it out quietly and everyone steps around it. The path ahead is clear."
                ),
                "failure_text": (
                    "The wrong foot lands on the wrong stone. A heavy log swings from the "
                    "ceiling with a sickening crack — everyone catches a rattling blow. "
                    "You regroup, bruised and a little embarrassed, and press on."
                ),
                "combat_fallback": None,
            },

            # ── 4. The Kennel ─────────────────────────────────────────────────
            {
                "type":  "combat",
                "name":  "The Kennel",
                "intro": (
                    "Iron cages line the walls, most broken and empty. Two are not. "
                    "A pair of dire wolves burst their cage doors the moment you step inside — "
                    "starved to the edge of frenzy, yellow eyes gleaming, jaws already open."
                ),
                "enemy": {
                    "name":       "Dire Wolves",
                    "emoji":      "🐺",
                    "hp":         54,
                    "ac":         13,
                    "atk_bonus":  5,
                    "dmg":        "2d6+3",
                    "initiative": 12,
                    "drops": [
                        {"id": "wolf_fang_necklace", "chance": 55},
                        {"id": "health_potion",      "chance": 45},
                    ],
                },
            },

            # ── 5. The Corpse Hall ────────────────────────────────────────────
            {
                "type":        "interaction",
                "name":        "The Corpse Hall",
                "intro": (
                    "A wide hall scattered with bones — adventurers who came before you and didn't "
                    "make it out. The kobolds stripped the bodies long ago, but kobolds are careless. "
                    "They miss things."
                ),
                "skill":        "intelligence",
                "skill_label":  "🔍 Investigation",
                "dc":           10,
                "success_text": (
                    "Beneath a collapsed helmet, wedged into a crack in the floor, you find a "
                    "battered leather satchel. Inside: a health potion still sealed, a handful "
                    "of gold coins, and wrapped in oilcloth — a shortsword in decent condition. "
                    "Whoever hid it here didn't make it back to collect it."
                ),
                "failure_text": (
                    "You search the hall carefully but find nothing beyond old bones and dust. "
                    "Whatever these adventurers carried, the kobolds got to it first. "
                    "You move on with nothing to show for it."
                ),
                "combat_fallback": None,
            },

            # ── 6. The Treasure Vault ─────────────────────────────────────────
            {
                "type":  "combat",
                "name":  "The Treasure Vault",
                "intro": (
                    "A vaulted stone chamber — and at its centre, a beautiful iron-banded chest, "
                    "lid slightly ajar, the glint of coins visible inside. "
                    "Someone left an unlocked treasure chest in the middle of a kobold den.\n\n"
                    "You should probably not open that. One of you opens it anyway.\n\n"
                    "The chest LUNGES."
                ),
                "enemy": {
                    "name":       "Mimic",
                    "emoji":      "📦",
                    "hp":         58,
                    "ac":         12,
                    "atk_bonus":  5,
                    "dmg":        "1d8+3",
                    "initiative": 15,
                    "drops": [
                        {"id": "amulet_of_fortitude", "chance": 75},
                        {"id": "health_potion",        "chance": 60},
                        {"id": "scroll_misty_step",    "chance": 20},
                    ],
                },
            },

            # ── 7. The Sealed Gate ────────────────────────────────────────────
            {
                "type":        "interaction",
                "name":        "The Sealed Gate",
                "intro": (
                    "At the end of a long corridor the passage is blocked by a heavy iron gate. "
                    "The lock is enormous — a thick iron bar mechanism that no amount of picking "
                    "will open. You could try to force it, but this thing was built to hold."
                ),
                "skill":        "strength",
                "skill_label":  "💪 Force the Gate",
                "dc":           22,
                "success_text": (
                    "Against all odds, raw strength carries the day. The gate groans, "
                    "bends, and finally gives with a shriek of metal. Beyond it: stairs descending "
                    "into cold, stale air. You hear a faint voice from somewhere below."
                ),
                "failure_text": (
                    "The gate doesn't budge. This lock needs a key — and the kobold captain "
                    "who runs this place almost certainly has one. You'll need to find his quarters "
                    "and come back. You backtrack deeper into the dungeon."
                ),
                "combat_fallback": None,
            },

            # ── 8. Captain's Quarters ─────────────────────────────────────────
            {
                "type":  "combat",
                "name":  "The Captain's Quarters",
                "intro": (
                    "A door marked with a crudely painted skull — the captain's room. "
                    "You kick it open. The kobold captain is already on his feet, a rusted longsword "
                    "levelled at you, two bodyguards flanking him. On the table behind him: "
                    "a ring of iron keys. He sees where your eyes go and snarls."
                ),
                "enemy": {
                    "name":       "Kobold Captain & Guards",
                    "emoji":      "👑",
                    "hp":         55,
                    "ac":         14,
                    "atk_bonus":  5,
                    "dmg":        "1d8+3",
                    "initiative": 13,
                    "drops": [
                        {"id": "iron_key",            "chance": 100},
                        {"id": "shortsword",          "chance": 45},
                        {"id": "small_health_potion", "chance": 80},
                        {"id": "scroll_shield_spell", "chance": 20},
                    ],
                },
            },

            # ── 9. The Gate Revisited ─────────────────────────────────────────
            {
                "type":        "interaction",
                "name":        "The Sealed Gate — Revisited",
                "intro": (
                    "You make your way back through the dungeon to the sealed iron gate. "
                    "The captain's key ring is in hand. One of these has to fit."
                ),
                "skill":        "strength",
                "skill_label":  "🗝️ Unlock the Gate",
                "dc":           5,
                "success_text": (
                    "The third key on the ring slides home with a satisfying click. "
                    "The gate swings open on protesting hinges. Beyond it: stone stairs "
                    "descending into cold, damp air. From somewhere below, a hoarse voice calls out — "
                    "'Hello? Is someone there? Please — please help me!'"
                ),
                "failure_text": (
                    "You fumble with the keys for a moment before one catches. "
                    "The gate opens with a groan. Below: stairs dropping into cold darkness. "
                    "A faint, hoarse voice drifts up from the depths. Someone is alive down there."
                ),
                "combat_fallback": None,
            },

            # ── 10. The Deep Cellar ───────────────────────────────────────────
            {
                "type":  "combat",
                "name":  "The Deep Cellar",
                "intro": (
                    "The cellar is miserable — dripping stone walls, a single guttering torch, "
                    "and chained to an iron ring in the far wall: Aldric the merchant, "
                    "thin and hollow-eyed but alive. Two kobold jailers spin around at your arrival "
                    "and level their spears. Aldric rasps: 'Get them! Quickly — there are more above!'"
                ),
                "enemy": {
                    "name":       "Kobold Jailers",
                    "emoji":      "🐊",
                    "hp":         28,
                    "ac":         12,
                    "atk_bonus":  4,
                    "dmg":        "1d4+2",
                    "initiative": 11,
                    "drops": [
                        {"id": "health_potion",       "chance": 65},
                        {"id": "small_health_potion", "chance": 75},
                    ],
                },
            },

            # ── 11. Aldric's Cell — Rescue ────────────────────────────────────
            {
                "type":        "interaction",
                "name":        "Aldric's Cell",
                "intro": (
                    "The jailers are down. Aldric strains against his chains, eyes wide with relief "
                    "and exhaustion. The key to his shackles hangs from a hook on the wall — "
                    "of course the kobolds left it right there. You take it."
                ),
                "skill":        "dexterity",
                "skill_label":  "🗝️ Unlock the Shackles",
                "dc":           5,
                "success_text": (
                    "The shackle lock opens on the first try. Aldric slumps forward, catching "
                    "himself on the wall, then straightens up with a long, shaky breath. "
                    "'I knew someone would come,' he says, voice cracking. 'I knew it.' "
                    "He presses a heavy purse into the nearest hand. 'Whatever you find in this "
                    "dungeon — keep it. You earned it ten times over. Now let's get out of here.'\n\n"
                    "You climb back into the light."
                ),
                "failure_text": (
                    "You fumble with the lock before it gives. Aldric stumbles free, clutching your "
                    "arm for support. 'Bless you,' he whispers. 'All of you. Let's not stay down here "
                    "a moment longer than we have to.' He presses a purse of coins into your hands, "
                    "and you help him up the stairs and back into the daylight."
                ),
                "combat_fallback": None,
            },
        ],
    })
