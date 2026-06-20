# 🗺️ Campaigns DLC

Adventure modules playable via `/wander`. Each campaign has a narrative intro, a sequence of encounters, and a gold + XP reward on completion.

---

## Registered campaigns

| Folder | Campaign | Difficulty | Level | Players | Reward |
|---|---|---|---|---|---|
| [`the_mayors_request/`](the_mayors_request/) | 🏛️ The Mayor's Request | Easy | Lv 1+ | 1–4 | 40–80 g / 120 XP |
| [`a_farmers_trouble/`](a_farmers_trouble/) | 🌾 A Farmer's Trouble | Easy | Lv 1+ | 1–4 | 15–45 g / 100 XP |
| [`beneath_the_old_mill/`](beneath_the_old_mill/) | 🏚️ Beneath the Old Mill | Medium | Lv 2+ | 1–4 | 60–140 g / 200 XP |
| [`the_lonely_ice_mountain/`](the_lonely_ice_mountain/) | 🧊 The Lonely Ice Mountain | Hard | Lv 4+ | 2–4 | 120–280 g / 350 XP |

---

## Encounter types

| Type | Description |
|---|---|
| `combat` | Standard turn-based fight against an enemy |
| `interaction` | Skill check (DC vs stat + modifiers) — pass or face a combat fallback |
| `choice` | Narrative fork — player picks an option, each leading to a different outcome |

---

## Adding a campaign

Create `DND_DLC/campaigns/{id}/variables.py` and call `api.add_campaign(data)` inside `register(api)`.

See [`_template/variables.py`](_template/variables.py) for a commented example with all fields.
