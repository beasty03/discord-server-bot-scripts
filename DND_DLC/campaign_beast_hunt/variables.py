from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ── Shop DLC items ────────────────────────────────────────────────────────────

SHOP_ITEM = {
    "id":          "boar_tusk_charm",
    "name":        "Boar Tusk Charm",
    "emoji":       "🐗",
    "description": "A trophy from the Boar King. Worn by survivors as a badge of honour.",
    "price":       75,
    "max_qty":     1,
    "tier":        "uncommon",
}

SHOP_BUNDLE = {
    "id":          "beast_hunters_kit",
    "name":        "Beast Hunter's Kit",
    "emoji":       "🏹",
    "description": "Everything you need to track and survive the Prowling Beast.",
    "items":       [("health_potion", 2), ("boar_tusk_charm", 1)],
    "price":       100,
    "tier":        "uncommon",
}

# ── Campaign ──────────────────────────────────────────────────────────────────

CAMPAIGN = {
    "id":              "beast_hunt",
    "name":            "The Prowling Beast",
    "emoji":           "🐗",
    "min_level":       1,
    "min_players":     1,
    "max_players":     4,
    "difficulty":      "Medium",
    "intro":           (
        "Livestock have gone missing near the village — dragged off in the night. "
        "Witnesses describe a dire wolf pack led by a monstrous boar no hunter has yet bested. "
        "Track them down before the next full moon, or the village will be abandoned."
    ),
    "reward_gold_min": 40,
    "reward_gold_max": 80,
    "reward_xp":       150,
    "encounters": [
        # ── 1. Skill check: find the pack before they find you ────────────────
        {
            "type":          "interaction",
            "name":          "Track the Pack",
            "intro":         (
                "Fresh tracks cut through the mud — large paws and cloven hooves. "
                "Someone with a sharp eye could pinpoint the pack's resting ground "
                "before they catch your scent."
            ),
            "skill":         "wisdom",
            "skill_label":   "🔍 Track Them",
            "dc":            10,
            "success_text":  (
                "You spot the pack resting in a hollow behind a fallen oak. "
                "Moving downwind, you have the element of surprise."
            ),
            "failure_text":  (
                "The trail splits and you lose it in the rain. "
                "A low growl behind you — they've found you first."
            ),
            "combat_fallback": None,
        },
        # ── 2. Combat: Dire Wolf ──────────────────────────────────────────────
        {
            "type":  "combat",
            "name":  "Dire Wolf",
            "intro": (
                "A massive dire wolf lunges from the tree line — "
                "hackles raised, yellow eyes locked on you!"
            ),
            "enemy": {
                "name":      "Dire Wolf",
                "emoji":     "🐺",
                "hp":        22,
                "ac":        13,
                "atk_bonus": 5,
                "dmg":       "2d6+3",
                "drops":     [
                    {"id": "leather_scrap", "chance": 70},
                    {"id": "herb",          "chance": 40},
                ],
            },
        },
        # ── 3. Combat: The Boar King (boss) ──────────────────────────────────
        {
            "type":  "combat",
            "name":  "The Boar King",
            "intro": (
                "The ground trembles. The Boar King crashes through the brush — "
                "a mountain of muscle and scarred hide, tusks gleaming with old blood. "
                "It fixes you with one baleful eye and charges."
            ),
            "enemy": {
                "name":      "Boar King",
                "emoji":     "🐗",
                "hp":        42,
                "ac":        14,
                "atk_bonus": 6,
                "dmg":       "2d8+4",
                "drops":     [
                    {"id": "boar_tusk_charm", "chance": 100},
                    {"id": "leather_scrap",   "chance": 90},
                    {"id": "herb",            "chance": 60},
                ],
            },
        },
    ],
}
