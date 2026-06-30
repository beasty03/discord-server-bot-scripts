
# 🧠 Quotes Event

A standalone multiplayer event built from the server's own quote archive. The bot posts a 4-choice trivia question publicly — guess who said it, who submitted it, or complete the missing half — and only the fastest correct answer in the channel wins coins. Runs independently of the Casino Event system, with its own channel and trigger.

## 📋 Features

- 🎙️ **Who said it?** — Show a quote, pick the correct author from 4 names
- 📸 **Who submitted it?** — Show a quote, pick who captured and submitted it
- ✍️ **Complete the quote** — See the first half, pick the correct ending (only for longer quotes)
- 🏆 **Always multiplayer** — every question is posted publicly; there's no solo mode
- ⚡ **Only the first correct answer wins** — reward scales by speed, faster = more coins
- 🔢 **Multi-question events** — runs N questions back to back with a final scoreboard

## 🚀 Installation

Load the cog as `Events.quotes_event.quotes_event`.

## 🎮 Commands

| Command | Description |
|---------|-------------|
| `/start_quiz_event [questions]` | *(admin)* Start a quiz event with N questions (default 5) |
| `/set_quiz_channel <channel>` | *(admin)* Set the channel quiz events are posted in |

This is its own event type — it is **not** part of `/startevent` or the Casino Event system.

## ⚙️ How it works

1. Admin runs `/start_quiz_event` (channel must be set first via `/set_quiz_channel`).
2. Bot posts a question publicly with 4 buttons.
3. Anyone can click, but each player can only answer once per question.
4. **Only the first correct answer wins coins** — everyone else gets nothing, even if also correct.
5. Reward scales by speed: answering instantly pays `EVENT_REWARD_FIRST`, answering just before timeout pays `EVENT_REWARD_MIN`.
6. After `EVENT_QUESTION_TIMEOUT` seconds the answer is revealed and the next question starts.
7. Final scoreboard posted after all questions.

## ⚙️ Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `EVENT_QUESTIONS` | `5` | Default questions per event |
| `EVENT_QUESTION_TIMEOUT` | `20` | Seconds per event question |
| `EVENT_REWARD_FIRST` | `250` | Max coins (answer instantly) |
| `EVENT_REWARD_MIN` | `75` | Min coins (answer at the last second) |

## Requirements

Needs at least **4 quotes** in the database with different authors to generate quiz questions. Use `/quote` and `/quote_import` (in the Quotes cogs) to populate the archive.
