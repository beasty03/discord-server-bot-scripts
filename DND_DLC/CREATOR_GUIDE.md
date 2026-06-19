# DLC Creator Guide

Create custom content for the D&D bot without touching a single engine file.
Drop a `variables.py` into the right folder, restart the bot, and it's live.

For an AI-guided step-by-step interview, open a Claude Code session and type `/dlc-create`.

---

## Quick start

```
DND_DLC/
  items/
    my_sword/
      variables.py    ← one file, that's it
  campaigns/
    my_adventure/
      variables.py
  races/
    my_race/
      variables.py
  classes/
    my_class/
      variables.py
```

Every `variables.py` exports exactly one function:

```python
from DND.DungeonMaster.effects import BonusAttack, Flag, Heal, Message, Modify, Status

def register(api):
    # your content here
    pass
```

Folders starting with `_` are skipped (use for templates and drafts).

---

## Effects — what handlers can return

Handlers return a list of these objects. Never mutate state directly.

| Effect | What it does |
|---|---|
| `Modify("damage", add=N)` | Add N to the current damage total |
| `Modify("damage", add=N, damage_type="fire")` | Add N fire damage (tagged, for future resistance checks) |
| `Modify("attack_roll", add=N)` | Add N to the attack roll (use on `on_before_attack`) |
| `Heal(N)` | Restore N HP to the acting player |
| `Status("status_id", duration)` | Apply a named status for N turns |
| `Flag("flag_name", True)` | Set a boolean flag readable via `ctx.has_flag("flag_name")` |
| `BonusAttack()` | Grant one extra attack this turn |
| `Message("text")` | Show a line in the combat log |

All additions from multiple handlers sum together. All multipliers multiply together.

---

## CombatContext — what handlers can read

```python
def my_handler(ctx):
    # Player
    ctx.player.id           # Discord user id string
    ctx.player.name         # Display name
    ctx.player.level        # int
    ctx.player.char_class   # "ranger", "wizard", etc.
    ctx.player.race         # "elf", "dwarf", etc.
    ctx.player.subclass     # "hunter", "evocation", etc. (None if not chosen)
    ctx.player.hp           # current HP
    ctx.player.max_hp       # max HP
    ctx.player.equipped     # list of item dicts (id, slot, dmg, ...)
    ctx.player.stats.get("mods", {}).get("strength", 0)  # ability modifier

    # Enemy
    ctx.enemy.name          # display name
    ctx.enemy.hp            # current HP
    ctx.enemy.max_hp        # max HP at start of combat
    ctx.enemy.ac            # armor class

    # Current action
    ctx.turn.ability_id     # which ability was used (None if normal attack)
    ctx.turn.attack_roll    # the d20 roll
    ctx.turn.is_crit        # True on natural 20
    ctx.turn.is_hit         # True if the attack hit
    ctx.turn.base_damage    # damage rolled before any effects

    # Helpers
    ctx.roll("2d6+3")       # roll dice, returns int
    ctx.has_flag("name")    # check a flag set by Flag(), returns bool
```

---

## Events

| Event | When it fires |
|---|---|
| `on_ability_use` | Player activates an ability — check `ctx.turn.ability_id` |
| `on_damage_roll` | After a hit — add passive damage bonuses here |
| `on_hit` | Same moment — use for hit-triggered status effects |
| `on_before_attack` | Before d20 vs AC comparison — modify `attack_roll` here |
| `on_take_damage` | When an enemy's attack lands on the player |
| `on_turn_start` | Start of each round — passive regen, persistent effects |
| `on_skill_check` | During interaction encounters — racial skill bonuses |

---

## Status effects

Every `status_id` used in a `Status()` call must be declared first:

```python
api.define_status(
    "my_status",
    label = "My Status",
    icon  = "✨",
    effects = {
        "player_ac_bonus":    2,     # +N to player AC while active
        "enemy_ac_penalty":   2,     # -N from enemy AC while active
        "enemy_atk_penalty":  2,     # -N from enemy attack bonus while active
        "damage_mult":        0.5,   # multiply incoming damage (0.5 = half damage)
        "clears_on_hit":      True,  # remove after the player's next hit
        "clears_on_take_hit": True,  # remove after the player is next hit
        "clears_on_turn":     True,  # remove at the start of next round
    }
)
```

Only include the keys that matter — all default to 0 / False.

---

## Item fields

```python
api.add_item({
    # Required
    "id":    "my_item",       # unique snake_case — never reuse an id from character/variables.py
    "name":  "My Item",
    "slot":  "weapon",        # weapon | offhand | armor | misc | consumable | material | recipe | companion

    # Weapon-only
    "weapon_type": "martial", # simple | martial
    "ability":     "strength",# strength | dexterity
    "dmg":         "1d8",
    "handed":      1,         # 1 or 2
    "ranged":      False,     # True for bows/crossbows

    # Armor/offhand
    "ac_bonus": 2,

    # Consumable
    "heal_expr": "2d4+2",     # dice expression; engine rolls this on use

    # Economy
    "sell":  50,
    "tier":  "uncommon",      # common | uncommon | rare | epic | legendary
    "emoji": "⚔️",
    "description": "...",

    # Combat hooks (auto-wired — only fires when item is equipped)
    "on_damage_roll": my_fn,  # fires after every hit
    "on_hit":         my_fn,  # fires on hit, for status/flag effects
    "on_take_damage": my_fn,  # fires when the player is hit
    "on_use":         my_fn,  # fires when a consumable is used
})
```

To also list it in the shop:

```python
api.add_shop_item({
    "id":          "my_item",
    "name":        "My Item",
    "emoji":       "⚔️",
    "description": "...",
    "price":       250,
    "max_qty":     1,
    "tier":        "uncommon",
})
```

---

## Campaign fields

```python
api.add_campaign({
    "id":              "my_campaign",
    "name":            "My Campaign",
    "emoji":           "🗺️",
    "min_level":       1,
    "min_players":     1,
    "max_players":     4,
    "difficulty":      "Medium",   # Easy | Medium | Hard | Deadly
    "intro":           "...",
    "reward_gold_min": 50,
    "reward_gold_max": 100,
    "reward_xp":       150,
    "encounters": [ ... ],
})
```

### Encounter types

**Combat:**
```python
{
    "type":  "combat",
    "name":  "Ambush in the Woods",
    "intro": "Three bandits step from the shadows.",
    "enemy": {
        "name":       "Bandit",
        "emoji":      "🗡️",
        "hp":         28,
        "ac":         13,
        "atk_bonus":  4,
        "dmg":        "1d6+2",
        "initiative": 2,
        "drops": [
            {"id": "leather_scrap", "chance": 40},
            {"id": "herb",          "chance": 25},
        ],
    },
}
```

**Interaction (skill check):**
```python
{
    "type":         "interaction",
    "name":         "The Locked Gate",
    "intro":        "A rusted gate blocks the path.",
    "skill":        "strength",
    "skill_label":  "💪 Force it open",
    "dc":           12,
    "success_text": "The gate swings open with a groan.",
    "failure_text": "The gate holds fast. The noise draws attention...",
    "combat_fallback": {        # enemy spawns on failure; set None for no fight
        "name": "Guard", "emoji": "⚔️", "hp": 22, "ac": 13,
        "atk_bonus": 3, "dmg": "1d6+1", "initiative": 2, "drops": [],
    },
}
```

**Choice:**
```python
{
    "type":  "choice",
    "name":  "The Crossroads",
    "intro": "Two paths lie ahead.",
    "options": [
        {
            "label":       "🌲 Take the forest path",
            "result_text": "You enter the dark forest.",
            "encounters":  [ ... ],   # list of combat/interaction sub-encounters
        },
        {
            "label":       "🏚️ Take the village road",
            "result_text": "You approach a quiet village.",
            "encounters":  [ ... ],
        },
    ],
}
```

### Enemy stat scaling

| Difficulty | Level | HP    | AC    | ATK | DMG       |
|---|---|---|---|---|---|
| Easy       | 1–2   | 18–25 | 11–13 | +2–3 | 1d4+1 – 1d6+2 |
| Medium     | 2–4   | 25–38 | 13–14 | +3–5 | 1d6+2 – 1d8+3 |
| Hard       | 4–6   | 38–55 | 14–16 | +5–6 | 1d8+3 – 2d6+3 |
| Boss       | 6+    | 55–110| 15–17 | +6–8 | 2d6+4 – 2d10+5 |

---

## Race fields

```python
api.add_race({
    "id":           "my_race",
    "name":         "My Race",
    "emoji":        "🧝",
    "stat_bonuses": {"dexterity": 2, "intelligence": 1},
    "traits": [
        {"name": "Keen Senses",  "desc": "Advantage on Perception checks."},
        {"name": "Fey Ancestry", "desc": "Advantage on saves vs charm."},
    ],
})

# Hook handlers onto events for combat effects:
def _elf_passive(ctx):
    if ctx.player.race != "my_race": return []
    # ...
    return [...]

api.on("on_damage_roll", _elf_passive)
```

---

## Class fields

```python
api.add_class({
    "id":           "my_class",
    "name":         "My Class",
    "emoji":        "⚔️",
    "hit_die":      10,
    "armor":        14,           # base AC (unarmored)
    "primary_stat": "strength",
    "weapon_profs": ["simple", "martial"],
    "armor_profs":  ["light", "medium", "heavy", "shields"],
    "saving_throws": ["strength", "constitution"],
    "start_items":  ["longsword", "shield"],
    "features": [
        {"level": 1, "name": "Fighting Style", "desc": "Choose a combat style."},
        {"level": 5, "name": "Extra Attack",    "desc": "Attack twice per action."},
    ],
    "abilities": [
        {
            "id":        "my_ability",
            "name":      "My Ability",
            "label":     "✨ My Ability",
            "action":    "action",    # "action" | "bonus"
            "level_req": 1,
            "once_per":  "combat",    # None | "combat" | "rest"
            "handler":   _my_ability, # the Python function
            "desc":      "Does something powerful.",
        },
    ],
    "subclasses": {
        "my_subclass": {
            "abilities": ["my_subclass_ability"],
            "desc": "Flavour description.",
        },
    },
    "level_choices": {
        ("my_class", 3): {
            "key":    "subclass",
            "prompt": "Choose your subclass:",
            "options": [
                {"id": "my_subclass", "label": "My Subclass", "desc": "..."},
            ],
        },
    },
})
```

---

## Recipe fields

```python
api.add_recipe({
    "id":          "my_crafted_item",
    "name":        "My Crafted Item",
    "emoji":       "⚗️",
    "tier":        "rare",
    "unlock":      "recipe_my_crafted_item",  # item id of the recipe scroll; None = always known
    "inputs":      [("herb", 3), ("leather_scrap", 2)],
    "output":      ("my_crafted_item", 1),
    "description": "Crafted from rare herbs.",
})
```

---

## Available base item ids (for drops and start_items)

From `DND/character/variables.py`:
`longsword` `shortsword` `greataxe` `greatsword` `handaxe` `dagger` `shortbow` `longbow`
`quarterstaff` `mace` `rapier` `shield` `leather_armor` `chain_mail` `spellbook`
`small_health_potion` `health_potion` `large_health_potion`
`herb` `leather_scrap` `arcane_shard`
`recipe_hp_medium` `recipe_hp_large`
`scroll_misty_step` `scroll_scorching_ray` `scroll_fireball` `scroll_counterspell`

---

## Rules

- One `variables.py` per folder. One `register(api)` per file.
- IDs are permanent — changing them after release breaks existing player data.
- Only import from `DND.DungeonMaster.effects` — never from engine internals.
- Handlers must always return a list. Return `[]` to do nothing.
- `register()` runs once at bot startup. Do not put per-combat logic outside handlers.
- Folders starting with `_` are ignored by the loader.
