# 🏪 Shop

Daily rotating item shop with a tier system, limited stock, and DLC registration. Each day's inventory is seeded by the date so every player sees the same shop until midnight.

---

## Commands

| Command | Description |
|---|---|
| `/shop` | Browse today's items and bundles, and buy them. |

---

## How the shop works

1. The first `/shop` call of the day generates stock and writes it to the DB.
2. Items and bundles are selected by **weighted random draw** — higher-tier items are drawn less often.
3. Each selected listing gets a stock count drawn from its tier's `stock_min`/`stock_max` range.
4. Sold-out items remain visible (~~strikethrough~~) but cannot be purchased.
5. Stock resets at midnight (next date → new seed → new selection).
6. Old stock rows are deleted after 7 days.

---

## Tier system

| Tier | Emoji | Draw weight | Stock per day |
|---|---|---|---|
| Common | ⚪ | 60 | 5–10 |
| Uncommon | 🟢 | 25 | 3–5 |
| Rare | 🔵 | 12 | 1–3 |
| Epic | 🟣 | 3 | 1 |

Weight is relative — with the defaults, a common item is ~20× more likely to appear on any given day than an epic one.

---

## Configuration (`variables.py`)

| Variable | Default | Description |
|---|---|---|
| `MAX_SHOP_ITEMS` | `4` | How many individual items to pick each day |
| `MAX_SHOP_BUNDLES` | `2` | How many bundles to pick each day |
| `TIERS` | see above | Per-tier weight and stock range |
| `SHOP_ITEMS` | 2 base items | Individual items always eligible for the pool |
| `SHOP_BUNDLES` | 2 base bundles | Bundles always eligible for the pool |

### Adding a base item

Add an entry to `SHOP_ITEMS` in `variables.py`. The `id` must match an item in `DND/character/variables.py`.

```python
{
    "id":          "my_item",
    "name":        "My Item",
    "emoji":       "✨",
    "description": "What it does.",
    "price":       100,
    "max_qty":     3,       # max a player can own at once
    "tier":        "uncommon",
}
```

### Adding a base bundle

```python
{
    "id":          "my_bundle",
    "name":        "My Bundle",
    "emoji":       "📦",
    "description": "What's in it.",
    "items":       [("item_id", qty), ("other_item", qty)],
    "price":       150,
    "tier":        "common",
}
```

---

## DLC integration

DLC cogs register their items and bundles in `setup()`:

```python
async def setup(bot):
    shop = bot.get_cog("ShopCog")
    if shop:
        shop.register_item(MY_SHOP_ITEM)
        shop.register_bundle(MY_SHOP_BUNDLE)
```

`register_item` / `register_bundle` are idempotent — calling them twice with the same `id` is a no-op.

DLC items are merged into the eligible pool before each day's draw, so they compete on equal footing with base items.

---

## Database

Table: `dnd_shop_stock`

| Column | Type | Description |
|---|---|---|
| `date` | TEXT | ISO date (`YYYY-MM-DD`) |
| `item_id` | TEXT | Item or bundle id |
| `stock` | INTEGER | Units remaining today |

Primary key is `(date, item_id)`. Stock is decremented on each successful purchase. `INSERT OR IGNORE` prevents duplicate generation under concurrent requests.
