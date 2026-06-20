# 🧩 DLC — Content Extensions

All D&D content lives here: classes, races, campaigns, items, spells, and recipes. The engine loads everything automatically at startup — no engine edits needed to add new content.

---

## How the loader works

At startup the engine scans:
- `DND_DLC/*/variables.py` (one level deep)
- `DND_DLC/{subdir}/*/variables.py` (two levels deep)

Each file must export one function:

```python
def register(api):
    ...
```

---

## Folders

| Folder | Contents |
|---|---|
| [`classes/`](classes/) | Playable classes with abilities, subclasses, and level choices |
| [`races/`](races/) | Playable races with stat bonuses and passive traits |
| [`campaigns/`](campaigns/) | Adventures: combat, interaction, and choice encounters |
| [`items/`](items/) | Weapons, armor, consumables, companions, and accessories |
| [`spells/`](spells/) | Wizard spells (auto-injected into wizard's ability list) |
| [`recipes/`](recipes/) | Craftable items via the `/craft` command |
| [`_template/`](_template/) | Commented starter — copy this to create new DLC |

---

## API reference

```python
api.add_class(data)              # Playable class
api.add_race(data)               # Playable race
api.add_item(data)               # Item (weapon, armor, consumable, accessory…)
api.add_spell(data)              # Wizard spell (auto-adds to wizard abilities + shop scroll)
api.add_campaign(data)           # Campaign
api.add_recipe(data)             # Crafting recipe
api.add_shop_item(data)          # Add to the daily shop pool
api.on(event, fn, priority=0)    # Subscribe a handler to a combat event
api.define_status(id, ...)       # Named status effect with mechanical effects
api.define_damage_type(id, ...)  # Named damage type
```

---

## Campaign item dependencies

Every item a campaign drops **must** be registered in that campaign's own `variables.py`. Campaigns are self-contained — no silent dependencies on other DLC files.

The item DLC folders below exist for shop listings and general availability, but they do not exempt campaigns from registering their own drops.

### Item DLC folders

| Folder | Contents |
|---|---|
| [`items/base_materials/`](items/base_materials/) | `herb`, `leather_scrap`, `arcane_shard` |
| [`items/base_equipment/`](items/base_equipment/) | `shield`, `leather_armor`, `chain_mail`, `spellbook`, `reroll_token`, `boar_tusk_charm` |
| [`items/simple_weapons/`](items/simple_weapons/) | `dagger`, `handaxe`, `mace`, `quarterstaff` |
| [`items/martial_weapons/`](items/martial_weapons/) | `shortsword`, `longsword`, `rapier`, `greataxe`, `greatsword`, `flail` |
| [`items/ranged_weapons/`](items/ranged_weapons/) | `shortbow`, `longbow` |
| [`items/health_potions/`](items/health_potions/) | `small_health_potion`, `health_potion`, `large_health_potion` |
| [`items/companions/`](items/companions/) | `wolf_companion`, `eagle_companion`, `bear_companion`, `baby_dragon_companion` |
| [`items/currency/`](items/currency/) | `large_coin_pouch` |
| [`spells/base_spells/`](spells/base_spells/) | `scroll_burning_hands`, `scroll_thunderwave`, `scroll_shield_spell` |
| [`spells/advanced_spells/`](spells/advanced_spells/) | `scroll_scorching_ray`, `scroll_misty_step` |
| [`spells/master_spells/`](spells/master_spells/) | `scroll_fireball`, `scroll_counterspell` |

---

## Combat events

| Event | When it fires |
|---|---|
| `on_combat_start` | Combat begins |
| `on_turn_start` | Each round, once per active player |
| `on_before_attack` | Before the d20 attack roll |
| `on_damage_roll` | After a hit is confirmed, before damage is applied |
| `on_hit` | Same moment as `on_damage_roll`, for non-damage hit effects |
| `on_take_damage` | When the player is hit by an enemy |
| `on_ability_use` | Player activates an ability button |
| `on_item_use` | Player uses a consumable item |
| `on_item_equip` | Player equips an item |
| `on_skill_check` | During an interaction encounter |
| `on_kill` | Enemy is killed |
| `on_level_up` | Player levels up |
| `on_combat_end` | Combat ends (win or loss) |

---

## Effect types

Handlers return a list of effects. Returning `[]` means "no effect."

| Effect | What it does |
|---|---|
| `Heal(n)` | Restore `n` HP to the acting player |
| `Modify("damage", add=n)` | Add `n` to the current damage roll |
| `Modify("attack_roll", add=n)` | Add `n` to the attack roll before comparing to AC |
| `Status("id", turns)` | Apply a named status for N turns |
| `Flag("name", value)` | Set a boolean flag on the run state |
| `BonusAttack()` | Grant one additional weapon attack |
| `Message("text")` | Append a line to the round summary |
