# 🎒 Items DLC

Weapons, armor, consumables, companions, and accessories registered through the DLC engine.

---

## Folders

| Folder | Contents |
|---|---|
| [`simple_weapons/`](simple_weapons/) | Dagger, Handaxe, Quarterstaff, Club, Mace, Spear |
| [`martial_weapons/`](martial_weapons/) | Shortsword, Longsword, Greataxe, Rapier, Flail, Greatsword |
| [`ranged_weapons/`](ranged_weapons/) | Shortbow, Longbow, Hand Crossbow, Heavy Crossbow |
| [`health_potions/`](health_potions/) | Small / Medium / Large / Greater health potions |
| [`companions/`](companions/) | Wolf, Eagle, Bear companions (Beast Master Ranger only) |
| [`the_lonely_ice_mountain_items/`](the_lonely_ice_mountain_items/) | Storm Breaker, Chain Lightning (campaign drops) |

---

## Item slots

| Slot | Description |
|---|---|
| `weapon` | Equipped as main weapon — provides `dmg` and `atk_bonus` |
| `armor` | Provides `ac_bonus` |
| `offhand` | Shield or offhand weapon |
| `consumable` | Single-use healing or status item |
| `accessory` | Passive effects via `on_hit`, `on_take_damage`, `on_damage_roll` hooks |
| `companion` | Beast Master pet — attacks each round |
| `spell_scroll` | Teaches a spell to a Wizard permanently on use |
| `misc` | Quest items — no combat effect |

---

## Adding items

```python
def register(api):
    api.add_item({
        "id":          "my_item",
        "name":        "My Item",
        "emoji":       "⚔️",
        "slot":        "weapon",
        "weapon_type": "martial",
        "ability":     "strength",
        "dmg":         "1d8",
        "handed":      1,
        "tier":        "uncommon",
        "sell":        40,
        "description": "What it does.",
    })
    api.add_shop_item({...})  # optional — adds to daily shop pool
```
