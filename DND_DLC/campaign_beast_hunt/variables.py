from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ── Shop DLC ──────────────────────────────────────────────────────────────────

SHOP_ITEM = {
    "id":          "boar_tusk_charm",
    "name":        "Boar Tusk Charm",
    "emoji":       "🐗",
    "description": "A trophy from the Prowling Beast. Worn by survivors as a badge of honour.",
    "price":       75,
    "max_qty":     1,
    "tier":        "uncommon",
}

SHOP_BUNDLE = {
    "id":          "beast_hunters_kit",
    "name":        "Beast Hunter's Kit",
    "emoji":       "🏹",
    "description": "Everything you need to track and take down the Prowling Beast.",
    "items":       [("health_potion", 2), ("boar_tusk_charm", 1)],
    "price":       100,
    "tier":        "uncommon",
}

CAMPAIGN = {
    "id":              "beast_hunt",
    "name":            "The Prowling Beast",
    "emoji":           "🐗",
    "min_level":       1,
    "min_players":     1,
    "max_players":     4,
    "difficulty":      "Easy",
    "intro":           (
        "Livestock have gone missing near the village. A massive beast was spotted "
        "prowling the fields at dusk. The farmer's reward is modest — but the beast must be stopped."
    ),
    "reward_gold_min": 20,
    "reward_gold_max": 50,
    "reward_xp":       50,
    "encounters": [
        {
            "type":          "interaction",
            "name":          "Track the Beast",
            "intro":         (
                "Fresh tracks lead into the brush. Someone with a keen eye might narrow "
                "down exactly where the beast is hiding before it finds you first."
            ),
            "skill":         "wisdom",
            "skill_label":   "🔍 Track It",
            "dc":            8,
            "success_text":  (
                "You spot the beast's den behind a fallen oak — you have the element of surprise."
            ),
            "failure_text":  "The tracks go cold. You'll have to flush it out the hard way.",
            "combat_fallback": None,
        },
        {
            "type":  "combat",
            "name":  "Wild Boar",
            "intro": (
                "The beast charges from the undergrowth — a massive boar, "
                "tusks lowered and eyes wild with fury!"
            ),
            "enemy": {
                "name":      "Wild Boar",
                "emoji":     "🐗",
                "hp":        11,
                "ac":        11,
                "atk_bonus": 3,
                "dmg":       "1d6+1",
            },
        },
    ],
}
