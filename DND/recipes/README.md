# ⚗️ Recipes

Crafting system for the D&D module. Players collect materials from campaign encounters, unlock recipes via scrolls, and craft tiered healing potions.

---

Commands: 3

## Commands

| Command | Description |
|---|---|
| `/recipes` | Browse all crafting recipes with lock/unlock status and material availability. |
| `/craft` | Select a known recipe and craft it if you have the required materials. |
| `/learn_recipe` | Consume a recipe scroll from your backpack to permanently unlock a recipe. |

---

## How crafting works

1. **Gather materials** — crafting materials drop from enemies during campaign encounters.
2. **Unlock recipes** — some recipes are always known (common); others require a 📜 recipe scroll. Scrolls drop in campaigns or appear in the shop.
3. **Craft** — use `/craft`, pick a recipe, and confirm. Materials are consumed and the item goes straight to your backpack.

---

## Tiers and potions

| Potion | Tier | Heal | Recipe |
|---|---|---|---|
| Small Health Potion | Common ⚪ | 1d4+1 | Always known: 🌿 Herb ×2 |
| Health Potion | Uncommon 🟢 | 2d4+2 | Unlock with 📜 Recipe: Health Potion |
| Large Health Potion | Rare 🔵 | 4d4+4 | Unlock with 📜 Recipe: Large Health Potion |

---

## Crafting materials

| Material | Tier | Drops from |
|---|---|---|
| 🌿 Herb | Common | Goblins, bandits, forest creatures, boar |
| 🪶 Leather Scrap | Uncommon | Bandits, boar |
| 💎 Arcane Shard | Rare | Shadow hound, undead, lich, dragon |

Drop chance is per surviving player per combat encounter and varies by enemy type.

---

## Recipe scrolls

Recipe scrolls can be obtained from:
- The 🏪 shop (when they appear in the daily rotation)
- Campaign drops (planned for future DLC)

Use `/learn_recipe` to consume a scroll and permanently unlock its recipe on your account.

---

## DLC integration

DLC cogs can register additional recipes in `setup()`:

```python
async def setup(bot):
    recipes = bot.get_cog("RecipesCog")
    if recipes:
        recipes.register_recipe(MY_RECIPE)
```

Recipe format mirrors the entries in `variables.py`. The `unlock` field can reference any item with `slot: "recipe"` registered in `DND/character/variables.py`.

---

## Configuration (`variables.py`)

| Variable | Description |
|---|---|
| `RECIPES` | List of all base crafting recipes |
| `TIER_EMOJI` | Emoji per tier for display |

Add new base recipes to the `RECIPES` list. DLC recipes are injected at runtime and compete equally.
