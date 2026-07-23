# 🐾 Tamagotchi

A virtual pet system. Adopt a pet, name it, and keep it alive by feeding, playing, cleaning, and resting. Stats decay over time — neglect your pet and it will die. All actions use Discord buttons.

Commands: 4

## 📋 Features

- 🐣 **8 pet types** — Cat, Dog, Bunny, Chick, Turtle, Dragon, Waifu, Goth Mommy (each with unique mood expressions)
- 📊 **4 stats** — Hunger, Happiness, Health, Energy with on-demand decay (no background tasks)
- 🌱 **Life stages** — Egg → Baby → Child → Teen → Adult based on age
- ❤️ **Health system** — poor care causes health loss; thriving pets slowly regenerate
- 🎭 **Mood faces** — 8 mood levels expressed differently per pet type
- 🟩 **Progress bars** — visual stat bars in every status embed
- 🔒 **Action cooldowns** — each action has a configurable cooldown to prevent spamming
- 💀 **Permadeath** — a dead pet is gone forever (use `/release_pet` to start fresh)

## 🚀 Installation

Load the cog as `Tamagotchi.tamagotchi.tamagotchi`.

Database table `tamagotchi` is created automatically on `cog_load`.

## 🎮 Commands

| Command | Description |
|---------|-------------|
| `/adopt <type> <name>` | Adopt a new tamagotchi pet |
| `/mypet` | View your pet's status with action buttons |
| `/rename_pet <name>` | Rename your pet |
| `/release_pet` | Release your pet (confirm required) |

## ⚙️ How it works

1. `/adopt` lets you pick a pet type and name — you can only have one pet per server.
2. `/mypet` shows a status embed with hunger, happiness, health, and energy bars.
3. Four buttons: **🍖 Feed**, **🎾 Play**, **🛁 Clean**, **💤 Rest** — each has a cooldown.
4. Stats decay based on hours since `last_updated` (calculated at command time, not via background task).
5. If health reaches 0 the pet dies — the embed shows a grey tombstone view.

## ⚙️ Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `FEED_COOLDOWN_MINS` | `30` | Minutes between feeds |
| `FEED_COST` | `50` | Coins deducted per feed |
| `PLAY_COOLDOWN_MINS` | `60` | Minutes between play sessions |
| `CLEAN_COOLDOWN_MINS` | `240` | Minutes between cleans |
| `REST_COOLDOWN_MINS` | `180` | Minutes between rests |
| `DECAY_HUNGER` | `5.0` | Hunger increase per hour |
| `DECAY_HAPPINESS` | `3.0` | Happiness decrease per hour |
| `DECAY_ENERGY` | `3.0` | Energy decrease per hour |
| `VIEW_TIMEOUT` | `90` | Seconds before buttons disable |

## Requirements

- Creates `tamagotchi` table (all pet stats + timestamps).
- Uses the existing bank balance system for feed costs.
