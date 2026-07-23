
# 🧠 Quotes Event

A multiplayer event built from the server's own quote archive. The bot posts a 4-choice trivia question publicly — guess who said it, who submitted it, or complete the missing half — and only the fastest correct answer in the channel wins coins. It fires automatically on a random interval (like Casino and Multiplier events) and shares their admin commands.

Commands: 1

## 📋 Features

- 🎙️ **Who said it?** — Show a quote, pick the correct author from 4 names
- 📸 **Who submitted it?** — Show a quote, pick who captured and submitted it
- ✍️ **Complete the quote** — See the first half, pick the correct ending (only for longer quotes)
- 🏆 **Always multiplayer** — every question is posted publicly; there's no solo mode
- ⚡ **Only the first correct answer wins** — reward scales by speed, faster = more coins
- 🔢 **Multi-question events** — runs N questions back to back with a final scoreboard
- 🔁 **Auto-fires** — runs on its own random interval, same as Casino/Multiplier events
- 🔗 **Shared admin commands** — uses the same `/startevent`, `/set_eventannouncement_channel`, `/set_event_downtime`, and `/event_check` as the other event types

## 🚀 Installation

Load the cog as `Events.quotes_event.quotes_event`.

## 🎮 Commands

| Command | Description |
|---------|-------------|
| `/start_quiz_event [questions]` | *(admin)* Manually start a quiz event with N questions (default 5) |
| `/set_quiz_channel <channel>` | *(admin)* Set the channel quiz events are posted in (dedicated fallback) |
| `/startevent → Quote Quiz` | *(admin, in `Events/casino_event`)* Start a quiz event via the shared event picker |
| `/set_eventannouncement_channel → Quote Quiz` | *(admin, in `Events/casino_event`)* Set the channel via the shared picker (takes priority over `/set_quiz_channel`) |
| `/set_event_downtime → Quote Quiz` | *(admin, in `Events/casino_event`)* Set the random auto-fire interval (minutes) |
| `/event_check` | *(in `Events/casino_event`)* Shows Quote Quiz status alongside Casino and Multiplier events |

## ⚙️ How it works

1. Set a channel via `/set_quiz_channel` or `/set_eventannouncement_channel → Quote Quiz`.
2. The event fires automatically every `EVENT_INTERVAL_MIN`–`EVENT_INTERVAL_MAX` minutes (random), or an admin can trigger it early with `/start_quiz_event` or `/startevent → Quote Quiz`.
3. Bot posts a question publicly with 4 buttons.
4. Anyone can click, but each player can only answer once per question.
5. **Only the first correct answer wins coins** — everyone else gets nothing, even if also correct.
6. Reward scales by speed: answering instantly pays `EVENT_REWARD_FIRST`, answering just before timeout pays `EVENT_REWARD_MIN`.
7. After `EVENT_QUESTION_TIMEOUT` seconds the answer is revealed and the next question starts.
8. Final scoreboard posted after all questions.

## ⚙️ Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `EVENT_INTERVAL_MIN` / `EVENT_INTERVAL_MAX` | `30` / `90` | Minutes between automatic event fires (random in range) |
| `EVENT_QUESTIONS` | `5` | Default questions per event |
| `EVENT_QUESTION_TIMEOUT` | `20` | Seconds per event question |
| `EVENT_REWARD_FIRST` | `250` | Max coins (answer instantly) |
| `EVENT_REWARD_MIN` | `75` | Min coins (answer at the last second) |

## Requirements

Needs at least **4 quotes** in the database with different authors to generate quiz questions. Use `/quote` and `/quote_import` (in the Quotes cogs) to populate the archive.
