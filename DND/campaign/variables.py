from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ============================================================================
# TIMING
# ============================================================================

WANDER_JOIN_TIMEOUT = 60   # seconds the party join window stays open
WANDER_RESULT_DELAY = 4    # seconds between the campaign intro and the outcome reveal

# ============================================================================
# CAMPAIGNS — add or edit entries here to change available bounties.
#   id              — unique string key
#   name            — display name
#   emoji           — shown in the title and select list
#   min_level       — initiator must be at least this level to see it
#   difficulty      — label shown to players (Easy / Medium / Hard / Deadly)
#   intro           — flavour text shown at the start of the run
#   success_chance  — base probability of success (0.0 – 1.0); slightly
#                     improved by avg level above min_level (max +15%)
#   reward_gold_*   — gold range; split evenly between all participants
#   reward_xp       — XP awarded to every participant on success
# ============================================================================

CAMPAIGNS = [
    {
        "id":              "goblin_scouts",
        "name":            "Goblin Scouts",
        "emoji":           "👺",
        "min_level":       1,
        "difficulty":      "Easy",
        "intro":           "A band of goblin scouts has been spotted harassing the village outskirts. Drive them off!",
        "success_chance":  0.85,
        "reward_gold_min": 30,
        "reward_gold_max": 80,
        "reward_xp":       75,
    },
    {
        "id":              "bandit_camp",
        "name":            "Bandit Camp",
        "emoji":           "⚔️",
        "min_level":       2,
        "difficulty":      "Medium",
        "intro":           "A bandit camp has been raiding the trade roads for weeks. Root them out.",
        "success_chance":  0.70,
        "reward_gold_min": 80,
        "reward_gold_max": 200,
        "reward_xp":       200,
    },
    {
        "id":              "dark_forest",
        "name":            "Dark Forest",
        "emoji":           "🌑",
        "min_level":       3,
        "difficulty":      "Medium",
        "intro":           "Strange creatures stir in the dark forest to the east. The locals dare not venture in.",
        "success_chance":  0.65,
        "reward_gold_min": 100,
        "reward_gold_max": 300,
        "reward_xp":       350,
    },
    {
        "id":              "ruined_keep",
        "name":            "Ruined Keep",
        "emoji":           "🏰",
        "min_level":       5,
        "difficulty":      "Hard",
        "intro":           "A ruined keep hides a powerful artefact — and the undead army that guards it.",
        "success_chance":  0.55,
        "reward_gold_min": 200,
        "reward_gold_max": 500,
        "reward_xp":       600,
    },
    {
        "id":              "dragons_lair",
        "name":            "Dragon's Lair",
        "emoji":           "🐉",
        "min_level":       10,
        "difficulty":      "Deadly",
        "intro":           "A young dragon has claimed the mountain pass. Heroes are desperately needed.",
        "success_chance":  0.40,
        "reward_gold_min": 500,
        "reward_gold_max": 2000,
        "reward_xp":       2000,
    },
]

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_CAMPAIGN = 0x8E44AD  # purple — D&D theme
COLOR_WIN      = 0x57F287  # green
COLOR_ERROR    = 0xED4245  # red
COLOR_INFO     = 0x5865F2  # blurple
