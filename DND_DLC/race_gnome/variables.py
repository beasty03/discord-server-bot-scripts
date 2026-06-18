from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ── Race definition ───────────────────────────────────────────────────────────

RACE = {
    "id":    "gnome",
    "name":  "Gnome",
    "emoji": "🔮",
    "mods":  {"intelligence": 2, "constitution": 1},
}

# ── Race traits (shown in /race_upgrade) ─────────────────────────────────────

TRAITS = [
    {"name": "Gnome Cunning",
     "desc": "Advantage on all Intelligence, Wisdom, and Charisma saving throws against magic."},
    {"name": "Darkvision",
     "desc": "See in dim light as bright light and in darkness as dim light, within 60 ft."},
    {"name": "Tinker",
     "desc": "Proficiency with tinker's tools. Can construct tiny clockwork devices during a short rest."},
    {"name": "Natural Illusionist",
     "desc": "Know the Minor Illusion cantrip. Intelligence is your spellcasting ability for it."},
]
