# ⚔️ Tamagotchi Fight Club

Challenge another user's tamagotchi to a PvP battle. Your pet's stats (health, energy, happiness, weight) determine its fighting power — a well-cared pet fights harder. Bet coins, fight, and claim the prize.

Commands: 2

## 📋 Features

- ⚔️ **PvP challenges** — challenge any server member who owns a living pet
- 🎲 **Stats-based combat** — health → HP & defense, energy + weight → attack, happiness → bonus attack
- ⚡ **Crits & dodges** — 10% crit chance (1.5× damage), 5% dodge chance (zero damage)
- 📜 **Battle log** — see every round's damage, crits, and dodges in the result embed
- 💰 **Coin betting** — winner takes the full pot, draw refunds both players
- 🐾 **Post-fight effects** — winner gains happiness & health, loser loses some
- 📊 **Fight record** — track wins, losses, and total earnings with `/fight_stats`

## 🚀 Installation

Load the cog as `Tamagotchi.fight_club.fight_club`.

Database table `tamagotchi_fights` is created automatically on `cog_load`.

## 🎮 Commands

| Command | Description |
|---------|-------------|
| `/challenge @user <bet>` | Challenge another user's tamagotchi to a fight |
| `/fight_stats` | View your tamagotchi's win/loss record |

## ⚙️ How it works

1. Use `/challenge @opponent <bet>` — a public embed appears showing both pets' stats and the prize pool.
2. The opponent has 60 seconds to click **⚔️ Accept** or **🏳️ Decline**.
3. On accept, both bets are deducted and the fight plays out instantly.
4. The result embed shows the full battle log, winner, and coin transfer.
5. Win: +10 happiness, +5 health to winner's pet. Lose: −15 happiness, −10 health to loser's pet.

## ⚙️ Fight stat formulas

| Fight stat | Formula |
|------------|---------|
| Max HP | `clamp(health × 2, 20, 200)` |
| Attack | `clamp(weight × 0.8 + energy × 0.5 + happiness × 0.2, 10, 60)` |
| Defense | `clamp(health × 0.2, 0, 20)` |

## ⚙️ Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `BET_MIN` | `100` | Minimum allowed bet |
| `CHALLENGE_TIMEOUT` | `60` | Seconds opponent has to respond |
| `MAX_ROUNDS` | `10` | Maximum rounds before HP determines winner |
| `CRIT_CHANCE` | `0.10` | Probability of a critical hit (1.5× damage) |
| `DODGE_CHANCE` | `0.05` | Probability of fully dodging an attack |
| `WIN_HAPPINESS_GAIN` | `10` | Happiness gained by winning pet |
| `WIN_HEALTH_GAIN` | `5` | Health gained by winning pet |
| `LOSE_HAPPINESS_LOSS` | `15` | Happiness lost by losing pet |
| `LOSE_HEALTH_LOSS` | `10` | Health lost by losing pet (never lethal) |

## Requirements

- Requires the `tamagotchi` table from `Tamagotchi.tamagotchi.tamagotchi`.
- Uses the existing bank balance system (`db.get_balance`, `db.update_balance`).
- Creates `tamagotchi_fights` table for fight record tracking.
