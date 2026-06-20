# 🔮 Spells DLC

Wizard spells registered via `api.add_spell()`. Each spell is automatically:
- Injected into the Wizard's ability list in the registry
- Made available via `/ability` autocomplete (gated by `level_req`)
- Optionally sold as a spell scroll in the shop

---

## Folders

| Folder | Contents |
|---|---|
| [`base_spells/`](base_spells/) | Shield, plus scrolls for Burning Hands and Thunderwave |
| [`advanced_spells/`](advanced_spells/) | Scorching Ray (Lv 3) and Misty Step (Lv 3) |
| [`master_spells/`](master_spells/) | Fireball (Lv 5) and Counterspell (Lv 5) |

---

## Adding a spell

```python
def _my_spell(ctx):
    if ctx.player.char_class != "wizard" or ctx.turn.ability_id != "my_spell":
        return []
    if ctx.player.level < 3:
        return []
    dmg = ctx.roll("2d6")
    return [Modify("damage", add=dmg), Message(f"My Spell: {dmg} damage!")]

api.add_spell({
    "id":        "my_spell",
    "name":      "My Spell",
    "emoji":     "✨",
    "label":     "✨ My Spell",
    "action":    "action",   # or "bonus"
    "level_req": 3,
    "once_per":  None,       # None | "combat" | "rest"
    "class":     "wizard",
    "handler":   _my_spell,
    "desc":      "2d6 damage.",
})
```
