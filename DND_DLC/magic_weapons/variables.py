from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# ── Magic Swords ──────────────────────────────────────────────────────────────
# All magical one- or two-handed swords. STR-based unless noted.

WEAPONS_SWORDS = [
    {
        "id":          "flame_tongue",
        "name":        "Flame Tongue",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "strength",
        "dmg":         "1d8+3",   # fire-enchanted longsword
        "handed":      1,
        "sell":        300,
    },
    {
        "id":          "moonblade",
        "name":        "Moonblade",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "dexterity",
        "dmg":         "1d8+2",   # elven finesse blade
        "handed":      1,
        "sell":        450,
    },
    {
        "id":          "vorpal_blade",
        "name":        "Vorpal Blade",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "strength",
        "dmg":         "2d6+4",   # two-handed cleaving sword
        "handed":      2,
        "sell":        800,
    },
]

# ── Magic Bows ────────────────────────────────────────────────────────────────
# DEX-based, ranged, two-handed.

WEAPONS_BOWS = [
    {
        "id":          "hunters_bow",
        "name":        "Hunter's Bow",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "dexterity",
        "dmg":         "1d8+2",
        "handed":      2,
        "ranged":      True,
        "sell":        200,
    },
    {
        "id":          "shadow_bow",
        "name":        "Shadow Bow",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "dexterity",
        "dmg":         "1d10+1",
        "handed":      2,
        "ranged":      True,
        "sell":        380,
    },
    {
        "id":          "elven_longbow",
        "name":        "Elven Longbow",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "dexterity",
        "dmg":         "1d10+3",
        "handed":      2,
        "ranged":      True,
        "sell":        600,
    },
]

# ── Magic Martial Weapons ─────────────────────────────────────────────────────
# STR-based axes, hammers and polearms.

WEAPONS_MARTIAL = [
    {
        "id":          "dwarven_waraxe",
        "name":        "Dwarven Waraxe",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "strength",
        "dmg":         "1d10+1",
        "handed":      1,
        "sell":        220,
    },
    {
        "id":          "thunder_maul",
        "name":        "Thunder Maul",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "strength",
        "dmg":         "2d6+2",
        "handed":      2,
        "sell":        420,
    },
    {
        "id":          "giant_slayer",
        "name":        "Giant Slayer",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "strength",
        "dmg":         "2d8+3",
        "handed":      2,
        "sell":        700,
    },
]

WEAPONS = WEAPONS_SWORDS + WEAPONS_BOWS + WEAPONS_MARTIAL

# ── Shop listings ─────────────────────────────────────────────────────────────

SHOP_ITEMS = [
    # Swords
    {
        "id":          "flame_tongue",
        "name":        "Flame Tongue",
        "emoji":       "🔥",
        "description": "A longsword wreathed in magical fire. 1d8+3 slashing/fire, one-handed.",
        "price":       750,
        "max_qty":     1,
        "tier":        "rare",
    },
    {
        "id":          "moonblade",
        "name":        "Moonblade",
        "emoji":       "🌙",
        "description": "An elven blade that sings in moonlight. 1d8+2 slashing, DEX-based, one-handed.",
        "price":       1100,
        "max_qty":     1,
        "tier":        "epic",
    },
    {
        "id":          "vorpal_blade",
        "name":        "Vorpal Blade",
        "emoji":       "⚔️",
        "description": "A legendary two-handed sword said to part anything it touches. 2d6+4 slashing.",
        "price":       3000,
        "max_qty":     1,
        "tier":        "legendary",
    },
    # Bows
    {
        "id":          "hunters_bow",
        "name":        "Hunter's Bow",
        "emoji":       "🏹",
        "description": "An enchanted shortbow that never misses its mark. 1d8+2, DEX, ranged.",
        "price":       500,
        "max_qty":     1,
        "tier":        "uncommon",
    },
    {
        "id":          "shadow_bow",
        "name":        "Shadow Bow",
        "emoji":       "🌑",
        "description": "A bow woven from shadow-thread — strikes fear before the arrow lands. 1d10+1, DEX, ranged.",
        "price":       900,
        "max_qty":     1,
        "tier":        "rare",
    },
    {
        "id":          "elven_longbow",
        "name":        "Elven Longbow",
        "emoji":       "🌿",
        "description": "Carved from a living moonwood tree. 1d10+3, DEX, ranged.",
        "price":       1800,
        "max_qty":     1,
        "tier":        "epic",
    },
    # Martial weapons
    {
        "id":          "dwarven_waraxe",
        "name":        "Dwarven Waraxe",
        "emoji":       "🪓",
        "description": "Forged under the mountain with runes of slaying. 1d10+1, STR, one-handed.",
        "price":       550,
        "max_qty":     1,
        "tier":        "uncommon",
    },
    {
        "id":          "thunder_maul",
        "name":        "Thunder Maul",
        "emoji":       "⚡",
        "description": "Each strike shakes the ground like a thunderclap. 2d6+2, STR, two-handed.",
        "price":       950,
        "max_qty":     1,
        "tier":        "rare",
    },
    {
        "id":          "giant_slayer",
        "name":        "Giant Slayer",
        "emoji":       "🗡️",
        "description": "A massive two-handed weapon made to fell creatures twice your size. 2d8+3, STR.",
        "price":       2200,
        "max_qty":     1,
        "tier":        "epic",
    },
]
