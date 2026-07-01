from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ============================================================================
# KNOWN COG GROUPS  (used by /bot_status)
# Add or remove entries here whenever a new cog is added to the bot.
# ============================================================================

COG_GROUPS: dict[str, list[str]] = {
    "🎰 Casino": [
        "GambleCog", "BlackjackCog", "RouletteCog", "HigherLowerCog",
        "BaccaratCog", "SlotsCog", "HorseRacingCog", "CrossyRoadCog",
        "CoinFlipCog", "RPSCog", "PokerCog", "DiamondMinesCog",
        "RocketCog", "SpinWheelCog", "CrapsCog", "UnderOverCog",
    ],
    "👤 User": ["BankCog", "StatsCog", "LeaderboardCog"],
    "📋 General": ["SelfRoles", "QuotesCog", "HelpCog"],
    "🎉 Events": ["CasinoEventCog", "MultiplierEventCog", "QuotesEventCog"],
    "⚔️ DnD": ["CharacterCog", "PartiesCog", "DungeonMasterCog", "ShopCog", "RecipesCog", "ScribeCog"],
    "🐾 Tamagotchi": ["TamagotchiCog", "FightClubCog"],
    "🎮 Minigames": ["HangmanCog", "WordleCog", "TicTacToeCog", "Connect4Cog"],
    "🔗 Webhooks": ["WordleRecap"],
    "⚙️ Admin": [
        "ConfigCog", "AutomodCog", "WelcomeSystem", "Rules",
        "CommandsCog", "AdminPanelCog",
    ],
}

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_OK     = 0x57F287
COLOR_WARN   = 0xF39C12
COLOR_ERROR  = 0xED4245
COLOR_PANEL  = 0x5865F2
