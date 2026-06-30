
# 🧠 Quote Quizes

Interactive quote trivia — answer a 4-choice question about the server's own quote archive. Three question types keep it fresh: guess who said it, who submitted it, or complete the missing half. Play solo for coins, or join a server-wide event where only the fastest correct answer wins.

## 📋 Features

- 🎙️ **Who said it?** — Show a quote, pick the correct author from 4 names
- 📸 **Who submitted it?** — Show a quote, pick who captured and submitted it
- ✍️ **Complete the quote** — See the first half, pick the correct ending (only for longer quotes)
- 💰 **Coin reward** — Correct personal answers earn coins instantly
- 🏆 **Event mode** — Public channel event: only the **first** correct answer per question wins; reward scales by how fast they answered
- ⚡ **Time-based prizes** — Answer faster = more coins (linear decay from max to min)
- 🔗 **Wired into `/startevent`** — Launchable alongside Casino and Multiplier events

## 🚀 Installation

Load the cog as `Quotes.quote_quizes.quote_quizes`.

## 🎮 Commands

| Command | Description |
|---------|-------------|
| `/quiz_quote` | Answer a personal 4-choice quiz question (ephemeral, coins for correct) |
| `/start_quiz_event [questions]` | *(admin)* Start a public quiz event with N questions |
| `/set_quiz_channel <channel>` | *(admin)* Set the channel for quiz events (falls back to casino event channel) |

The event is also launchable via `/startevent → Quote Quiz`.

## ⚙️ How the event works

1. Bot posts a question publicly with 4 buttons.
2. All players can click — each player can only answer once per question.
3. **Only the first correct answer** wins coins; everyone else gets nothing.
4. Reward scales by speed: answering instantly pays `EVENT_REWARD_FIRST`, answering just before timeout pays `EVENT_REWARD_MIN`.
5. After `EVENT_QUESTION_TIMEOUT` seconds the answer is revealed and the next question starts.
6. Final scoreboard posted after all questions.

## ⚙️ Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `QUIZ_REWARD` | `100` | Coins for a correct personal quiz answer |
| `QUIZ_TIMEOUT` | `30` | Seconds before a personal quiz times out |
| `EVENT_QUESTIONS` | `5` | Default questions per event |
| `EVENT_QUESTION_TIMEOUT` | `20` | Seconds per event question |
| `EVENT_REWARD_FIRST` | `250` | Max coins (answer instantly) |
| `EVENT_REWARD_MIN` | `75` | Min coins (answer at the last second) |

## Requirements

Needs at least **4 quotes** in the database with different authors to generate quiz questions. Use `/quote` and `/quote_import` to populate the archive.
