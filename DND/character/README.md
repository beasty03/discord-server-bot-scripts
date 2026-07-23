# 📜 Character

Create and manage your D&D character — roll ability scores, pick a race and class, and view your full character sheet.

Commands: 13

## Commands

| Command | Description |
|---------|-------------|
| `/name <name>` | Create your character and roll ability scores (4d6 drop lowest). If you already have one, renames it. |
| `/race <race>` | Set your race and apply its ability bonuses. |
| `/class <class>` | Set your class, receive starting gear, and compute HP and AC. |
| `/sheet [user]` | Show the full character sheet — abilities, modifiers, HP, AC, proficiency, XP, and balance. |
| `/backpack` | Show your inventory and equipped items. |
| `/level` | Show your current level and XP progress toward the next level. |
| `/class_upgrade [class]` | Browse all class features by level. Defaults to your current class. |
| `/race_upgrade [race]` | Browse all racial traits. Defaults to your current race. |

## Character setup order

1. `/name` — rolls base ability scores and creates your character
2. `/race` — adds racial ability bonuses
3. `/class` — sets hit die, AC, and starting equipment

All derived values (modifiers, AC, max HP, proficiency) are computed fresh on display — editing your race or class never double-applies bonuses.

## Races

| Race | Ability bonuses |
|------|----------------|
| 🧑 Human | +1 to all six abilities |
| 🧝 Elf | +2 DEX · +1 INT |
| 🧔 Dwarf | +2 CON · +1 STR |
| 🧒 Halfling | +2 DEX · +1 CHA |
| 👹 Half-Orc | +2 STR · +1 CON |
| 😈 Tiefling | +2 CHA · +1 INT |

## Classes

| Class | Hit die | Primary | Weapon proficiencies | Starting gear |
|-------|---------|---------|----------------------|---------------|
| ⚔️ Fighter | d10 | STR | Simple, Martial | Longsword, Shield |
| 🪓 Barbarian | d12 | STR | Simple, Martial | Greataxe |
| 🗡️ Rogue | d8 | DEX | Simple + Longsword, Shortsword, Rapier | Dagger, Leather Armor |
| 🏹 Ranger | d10 | DEX | Simple, Martial | Shortbow, Leather Armor |
| 🪄 Wizard | d6 | INT | Dagger, Quarterstaff (specific only) | Quarterstaff, Spellbook |
| ✨ Cleric | d8 | WIS | Simple | Mace, Shield |

## Weapon proficiency

`/backpack` shows the attack modifier for each weapon:

- **Proficient** — `⚔️ +5 (STR +3, prof +2)` — ability mod + proficiency bonus
- **Not proficient** — `⚔️ +3 (STR +3, no prof)` — ability mod only

Weapons have a `weapon_type` (`simple` or `martial`) and an `ability` (`strength` or `dexterity`). Class `weapon_profs` lists can contain type names (`"simple"`, `"martial"`) or specific item IDs for classes with limited proficiencies (Rogue, Wizard).

## Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `ROLL_METHOD` | `"roll"` | `"roll"` = 4d6 drop lowest · `"array"` = standard array (15 14 13 12 10 8) |
| `STANDARD_ARRAY` | `[15,14,13,12,10,8]` | Used only when `ROLL_METHOD = "array"` |
| `MAX_LEVEL` | `20` | Highest reachable level |

Races, classes, and items can be extended by adding entries to their lists in `variables.py`. XP thresholds follow the 5e standard table.
