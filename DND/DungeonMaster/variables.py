from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ── Timing ────────────────────────────────────────────────────────────────────
WANDER_JOIN_TIMEOUT = 60   # seconds party join window stays open
ROUND_TIMEOUT       = None # no timeout — players take as long as they need
INTERACTION_TIMEOUT = 45   # seconds for skill check / interaction choice
KILL_MODAL_TIMEOUT  = 120  # seconds to describe the killing blow
RESULT_DELAY        = 8    # pause between rounds (seconds)

# ── Quest board ───────────────────────────────────────────────────────────────
# When more than MAX_SHOWN campaigns are available, rotate daily.
MAX_SHOWN_CAMPAIGNS = 5

# ============================================================================
# CAMPAIGNS
#
# Each encounter is either:
#   type "combat"      → enemy stats block, players fight in rounds
#   type "interaction" → one skill check; on failure: combat fallback or just continues
#
# combat encounter keys:
#   name, intro, enemy: {name, emoji, hp, ac, atk_bonus, dmg}
#
# interaction encounter keys:
#   name, intro, skill (ability name), skill_label (button text),
#   dc, success_text, failure_text,
#   combat_fallback: enemy dict or None (None = failure has no combat consequence)
# ============================================================================

CAMPAIGNS = []
_DISCARDED = [
    {
        "id":              "goblin_scouts",
        "name":            "Goblin Scouts",
        "emoji":           "👺",
        "min_level":       1,
        "min_players":     1,
        "max_players":     4,
        "difficulty":      "Easy",
        "intro":           "A band of goblin scouts has been harassing the village outskirts. Drive them off!",
        "reward_gold_min": 30,
        "reward_gold_max": 80,
        "reward_xp":       75,
        "encounters": [
            {
                "type":  "combat",
                "name":  "Goblin Scouts",
                "intro": "Three goblins leap from the bushes, blades drawn!",
                "enemy": {"name": "Goblin Scouts", "emoji": "👺", "hp": 21, "ac": 13, "atk_bonus": 4, "dmg": "1d4+2", "initiative": 1,
                          "drops": [{"id": "herb", "chance": 70}]},
            },
            {
                "type":          "interaction",
                "name":          "Goblin Chief",
                "intro":         "The goblin chief plants himself in your path, sneering. *'Leave — or bleed.'*",
                "skill":         "charisma",
                "skill_label":   "🗣️ Persuade",
                "dc":            10,
                "success_text":  "The chief grumbles, steps aside, and waves his scouts off.",
                "failure_text":  "The chief spits and draws his blade. *'Wrong answer.'*",
                "combat_fallback": {"name": "Goblin Chief", "emoji": "👺", "hp": 15, "ac": 14, "atk_bonus": 5, "dmg": "1d6+3", "initiative": 2,
                                    "drops": [{"id": "herb", "chance": 50}]},
            },
        ],
    },
    {
        "id":              "bandit_camp",
        "name":            "Bandit Camp",
        "emoji":           "⚔️",
        "min_level":       2,
        "min_players":     1,
        "max_players":     4,
        "difficulty":      "Medium",
        "intro":           "A bandit camp has been raiding the trade roads for weeks. Root them out.",
        "reward_gold_min": 80,
        "reward_gold_max": 200,
        "reward_xp":       200,
        "encounters": [
            {
                "type":  "combat",
                "name":  "Camp Guards",
                "intro": "Two armed bandits step out of the shadows, blades ready.",
                "enemy": {"name": "Camp Guards", "emoji": "🗡️", "hp": 22, "ac": 12, "atk_bonus": 3, "dmg": "1d6+1", "initiative": 1,
                          "drops": [{"id": "leather_scrap", "chance": 50}]},
            },
            {
                "type":  "combat",
                "name":  "Bandit Lieutenant",
                "intro": "A hardened lieutenant charges from the tent, eyes wild with rage.",
                "enemy": {"name": "Bandit Lieutenant", "emoji": "⚔️", "hp": 28, "ac": 13, "atk_bonus": 5, "dmg": "1d8+2", "initiative": 2,
                          "drops": [{"id": "leather_scrap", "chance": 70}]},
            },
            {
                "type":          "interaction",
                "name":          "Bandit Boss",
                "intro":         "The boss stands at the ridge. *'I'll make you a deal — walk away and I let you live.'*",
                "skill":         "strength",
                "skill_label":   "😤 Intimidate",
                "dc":            12,
                "success_text":  "The boss backs down slowly, hands raised. *'Alright... we're done here.'*",
                "failure_text":  "The boss laughs and draws a crossbow. *'Nice try, hero.'*",
                "combat_fallback": {"name": "Bandit Boss", "emoji": "⚔️", "hp": 38, "ac": 14, "atk_bonus": 5, "dmg": "1d8+3", "initiative": 3,
                                    "drops": [{"id": "leather_scrap", "chance": 80}, {"id": "herb", "chance": 30}]},
            },
        ],
    },
    {
        "id":              "dark_forest",
        "name":            "Dark Forest",
        "emoji":           "🌑",
        "min_level":       3,
        "min_players":     1,
        "max_players":     4,
        "difficulty":      "Medium",
        "intro":           "Strange creatures stir in the dark forest to the east. The locals dare not venture in.",
        "reward_gold_min": 100,
        "reward_gold_max": 300,
        "reward_xp":       350,
        "encounters": [
            {
                "type":  "combat",
                "name":  "Giant Forest Spider",
                "intro": "A massive spider drops from the canopy, fangs dripping with venom.",
                "enemy": {"name": "Giant Forest Spider", "emoji": "🕷️", "hp": 26, "ac": 12, "atk_bonus": 3, "dmg": "1d8+3", "initiative": 3,
                          "drops": [{"id": "herb", "chance": 80}]},
            },
            {
                "type":          "interaction",
                "name":          "The Hermit Witch",
                "intro":         "An old woman emerges from a gnarled oak. She knows the forest's secrets — if you can earn her trust.",
                "skill":         "wisdom",
                "skill_label":   "🔍 Read Her Intent",
                "dc":            13,
                "success_text":  "The witch smiles and reveals the safe path, warning you of what lurks ahead.",
                "failure_text":  "She eyes you coldly and vanishes. The path ahead shimmers and splits — you're on your own.",
                "combat_fallback": None,
            },
            {
                "type":  "combat",
                "name":  "Shadow Hound",
                "intro": "A creature of living shadow lunges from between the trees.",
                "enemy": {"name": "Shadow Hound", "emoji": "🐺", "hp": 35, "ac": 14, "atk_bonus": 5, "dmg": "2d4+3", "initiative": 4,
                          "drops": [{"id": "arcane_shard", "chance": 35}, {"id": "scroll_scorching_ray", "chance": 8}]},
            },
        ],
    },
    {
        "id":              "ruined_keep",
        "name":            "Ruined Keep",
        "emoji":           "🏰",
        "min_level":       5,
        "min_players":     2,
        "max_players":     4,
        "difficulty":      "Hard",
        "intro":           "A ruined keep hides a powerful artefact — and the undead army that guards it.",
        "reward_gold_min": 200,
        "reward_gold_max": 500,
        "reward_xp":       600,
        "encounters": [
            {
                "type":  "combat",
                "name":  "Skeleton Warriors",
                "intro": "Skeleton warriors rise from the courtyard stones, empty sockets glowing red.",
                "enemy": {"name": "Skeleton Warriors", "emoji": "💀", "hp": 39, "ac": 13, "atk_bonus": 4, "dmg": "1d6+2", "initiative": 0,
                          "drops": [{"id": "arcane_shard", "chance": 30}]},
            },
            {
                "type":          "interaction",
                "name":          "The Bound Ghost",
                "intro":         "A ghost drifts from the inner tower. It was the keep's last guardian — and it has unfinished business.",
                "skill":         "charisma",
                "skill_label":   "🕊️ Commune with It",
                "dc":            14,
                "success_text":  "The ghost's anguish fades. It points you to a hidden passage — and whispers a name the Lich fears.",
                "failure_text":  "The ghost wails and collapses the passage ahead. You'll have to fight through.",
                "combat_fallback": {"name": "Restless Spirits", "emoji": "👻", "hp": 30, "ac": 11, "atk_bonus": 4, "dmg": "1d6+3", "initiative": 2,
                                    "drops": [{"id": "arcane_shard", "chance": 50}]},
            },
            {
                "type":  "combat",
                "name":  "Lich Apprentice",
                "intro": "A robed figure rises from behind the altar, crackling with dark energy.",
                "enemy": {"name": "Lich Apprentice", "emoji": "🧙", "hp": 55, "ac": 15, "atk_bonus": 6, "dmg": "2d6+4", "initiative": 2,
                          "drops": [{"id": "arcane_shard", "chance": 80}, {"id": "scroll_misty_step", "chance": 12}, {"id": "scroll_scorching_ray", "chance": 10}]},
            },
        ],
    },
    {
        "id":              "kobold_den",
        "name":            "Kobold Den",
        "emoji":           "🦎",
        "min_level":       1,
        "min_players":     1,
        "max_players":     4,
        "difficulty":      "Easy",
        "intro":           "A nest of kobolds has seized an abandoned mine, terrorising the nearby farms. Clear them out!",
        "reward_gold_min": 25,
        "reward_gold_max": 60,
        "reward_xp":       60,
        "encounters": [
            {
                "type":  "combat",
                "name":  "Kobold Pack",
                "intro": "A pack of yipping kobolds rushes from the dark tunnels, brandishing crude spears! (Tip: use `/attack` — with multiple kobolds you can pick your target!)",
                "enemy": {"name": "Kobold", "emoji": "🦎", "hp": 20, "ac": 12, "atk_bonus": 3, "dmg": "1d4+1", "initiative": 2,
                          "drops": [{"id": "herb", "chance": 40}]},
            },
            {
                "type":          "interaction",
                "name":          "Mine Collapse",
                "intro":         "Deep in the mine a structural beam has cracked. The ceiling groans ominously above you.",
                "skill":         "strength",
                "skill_label":   "💪 Brace the Beam",
                "dc":            11,
                "success_text":  "You heave the beam back into place just in time — the ceiling holds.",
                "failure_text":  "The beam snaps! Rocks crash down, and everyone stumbles through the dust.",
                "combat_fallback": None,
            },
            {
                "type":  "combat",
                "name":  "Warchief's Last Stand",
                "intro": "The kobold warchief stands before a crude dragon idol, rallying the last of his kin with a shrieking war cry!",
                "enemy": {"name": "Kobold Warchief", "emoji": "🦎", "hp": 27, "ac": 13, "atk_bonus": 4, "dmg": "1d6+2", "initiative": 1,
                          "drops": [{"id": "arcane_shard", "chance": 20}, {"id": "herb", "chance": 60}]},
            },
        ],
    },
    {
        "id":              "crossroads",
        "name":            "The Crossroads",
        "emoji":           "🛤️",
        "min_level":       2,
        "min_players":     1,
        "max_players":     4,
        "difficulty":      "Medium",
        "intro":           "You stand at a crossroads on the king's road. Reports of trouble reach you from every direction — you can only investigate one. (Tip: use `/choose` to decide!)",
        "reward_gold_min": 50,
        "reward_gold_max": 120,
        "reward_xp":       120,
        "encounters": [
            {
                "type":    "choice",
                "name":    "Which Path?",
                "intro":   "Three roads stretch before you. The party must choose — only one can be answered today.",
                "options": [
                    {
                        "label":        "🌾 Village Road — farmers called for help",
                        "result_text":  "You race toward the distant smoke. A farmstead is under attack!",
                        "encounters": [
                            {
                                "type":  "combat",
                                "name":  "Raiding Wolf Pack",
                                "intro": "A pack of dire wolves circles the farmstead, snapping at terrified villagers!",
                                "enemy": {"name": "Dire Wolf", "emoji": "🐺", "hp": 24, "ac": 12, "atk_bonus": 4, "dmg": "1d8+2", "initiative": 3,
                                          "drops": [{"id": "herb", "chance": 50}]},
                            },
                        ],
                    },
                    {
                        "label":        "🏚️ Old Bridge — merchants gone missing",
                        "result_text":  "The bridge looms in the mist — and so does the troll beneath it.",
                        "encounters": [
                            {
                                "type":  "combat",
                                "name":  "Bridge Troll",
                                "intro": "A massive troll heaves itself onto the bridge, hurling boulders and roaring with hunger!",
                                "enemy": {"name": "Bridge Troll", "emoji": "👹", "hp": 42, "ac": 14, "atk_bonus": 5, "dmg": "1d10+3", "initiative": 0,
                                          "drops": [{"id": "arcane_shard", "chance": 25}]},
                            },
                        ],
                    },
                    {
                        "label":        "🌲 Forest Trail — scouts gone silent",
                        "result_text":  "The forest swallows every sound. Dozens of yellow eyes blink at you from the dark.",
                        "encounters": [
                            {
                                "type":          "interaction",
                                "name":          "The Watching Eyes",
                                "intro":         "Something large crouches in the undergrowth. A low growl rolls through the trees. Rushing in means teeth — standing still might mean passage.",
                                "skill":         "wisdom",
                                "skill_label":   "🔍 Read the Forest",
                                "dc":            12,
                                "success_text":  "You project calm and stillness. The eyes withdraw. The scouts' trail becomes clear ahead.",
                                "failure_text":  "You flinch — and the predator lunges!",
                                "combat_fallback": {"name": "Forest Stalker", "emoji": "🐆", "hp": 30, "ac": 13, "atk_bonus": 4, "dmg": "1d8+3", "initiative": 4,
                                                    "drops": [{"id": "herb", "chance": 60}]},
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "id":              "dragons_lair",
        "name":            "Dragon's Lair",
        "emoji":           "🐉",
        "min_level":       10,
        "min_players":     2,
        "max_players":     4,
        "difficulty":      "Deadly",
        "intro":           "A young dragon has claimed the mountain pass. Heroes are desperately needed.",
        "reward_gold_min": 500,
        "reward_gold_max": 2000,
        "reward_xp":       2000,
        "encounters": [
            {
                "type":          "interaction",
                "name":          "The Dragon's Riddle",
                "intro":         "The dragon coils at the cave mouth. *'Answer my riddle, little ones, and I may let you pass. Fail — and burn.'*",
                "skill":         "intelligence",
                "skill_label":   "🧠 Solve the Riddle",
                "dc":            16,
                "success_text":  "The dragon tilts its head slowly. *'Clever. You may enter... though I make no promises.'*",
                "failure_text":  "The dragon roars. *'WRONG.'* It lunges before you can react.",
                "combat_fallback": {"name": "Enraged Dragon", "emoji": "🐉", "hp": 40, "ac": 16, "atk_bonus": 8, "dmg": "2d8+5", "initiative": 5,
                                    "drops": [{"id": "arcane_shard", "chance": 75}]},
            },
            {
                "type":  "combat",
                "name":  "Young Dragon",
                "intro": "The dragon fills the cavern with heat and fury. There is no running from this.",
                "enemy": {"name": "Young Dragon", "emoji": "🐉", "hp": 110, "ac": 17, "atk_bonus": 8, "dmg": "2d10+5", "initiative": 6,
                          "drops": [{"id": "arcane_shard", "chance": 90}, {"id": "scroll_fireball", "chance": 10}, {"id": "scroll_counterspell", "chance": 8}]},
            },
        ],
    },
]

# ── Embed colors ──────────────────────────────────────────────────────────────
COLOR_CAMPAIGN    = 0x8E44AD
COLOR_COMBAT      = 0xE74C3C
COLOR_INTERACTION = 0x3498DB
COLOR_WIN         = 0x57F287
COLOR_ERROR       = 0xED4245
COLOR_INFO        = 0x5865F2
