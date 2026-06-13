# Multiplier Event

A server-wide economy boost event. When active, all currency earned across the bot is multiplied by a random value between the configured min and max. The multiplier applies to **profit only** — the original wager is always returned on top of the boosted profit.

## How it works

1. An admin runs `/startevent Multiplier` (or `/start_multiplier_event`).
2. The bot picks a random multiplier between `MULTIPLIER_MIN` and `MULTIPLIER_MAX` (e.g. **1.47x**).
3. An announcement is posted to the configured channel with a live countdown showing when it ends.
4. For the duration of the event, every currency gain across all supported scripts is multiplied.
5. When time runs out (or an admin uses `/stop_multiplier_event`), the multiplier clears and an end message is posted.

### Example

> Normal gamble win: bet **500**, profit **500** → receive **+500**
> At **1.8x** event: profit **500 × 1.8 = 900** → receive **+900**
> The original bet is always returned on top.

## Affected scripts

| Script | Command | What gets boosted |
|--------|---------|-------------------|
| `Casino/gamble` | `/gamble` | Win profit |
| `Casino/blackjack` | `/blackjack` | Win / Blackjack profit |
| `Casino/roulette` | `/roulette` | Win profit |
| `Casino/baccarat` | `/baccarat` | Win profit |
| `Casino/higher_lower` | `/highlow` | Cashout profit |
| `User/bank` | `/daily` | Daily bonus amount |
| `Events/casino_event` | `/join` | Event win payouts |

> `/give` (player-to-player transfers) is intentionally excluded — the multiplier applies to currency earned from the bot, not from other players.

## Commands

### Starting events

| Command | Description |
|---------|-------------|
| `/startevent Multiplier` | Start a Multiplier event from the shared event command |
| `/startevent Casino` | Start a Casino event (for comparison) |

### Admin / Mod (Multiplier Event only)

| Command | Description |
|---------|-------------|
| `/start_multiplier_event` | Start the event immediately |
| `/stop_multiplier_event` | End the active event early |
| `/set_multiplier_channel #channel` | Set the announcement channel |
| `/set_multiplier_duration <seconds>` | How long the event lasts (default: 300s / 5 min) |
| `/set_multiplier_min <value>` | Minimum multiplier, e.g. `1.1` |
| `/set_multiplier_max <value>` | Maximum multiplier, e.g. `2.0` |

All `set_` commands require admin/mod permissions.

## Configuration

### `variables.py`

| Variable | Default | Description |
|----------|---------|-------------|
| `EVENT_CHANNEL_ID` | `0` | Fallback channel ID if not set via command |
| `MULTIPLIER_MIN` | `1.1` | Lowest possible multiplier |
| `MULTIPLIER_MAX` | `2.0` | Highest possible multiplier |
| `EVENT_DURATION` | `300` | Duration in seconds (5 minutes) |

### `multiplier_event_settings.json` (auto-generated)

Persists command-set values across bot restarts.

| Key | Type | Description |
|-----|------|-------------|
| `event_channel_id` | int | Channel ID for announcements |
| `event_duration` | int | Duration in seconds |
| `multiplier_min` | float | Minimum multiplier |
| `multiplier_max` | float | Maximum multiplier |

## Setup

1. Load the cog in your bot launcher:
   ```
   Events/multiplier_event/multiplier_event.py
   ```
2. Run `/set_multiplier_channel #your-channel` to configure the announcement channel.
3. Optionally adjust duration and range with the `set_` commands.
4. Use `/startevent Multiplier` or `/start_multiplier_event` to kick off the first event.

## Technical notes

- The active multiplier is stored on the bot object as `bot.multiplier_event_mult` (a `float` when active, `None` when not).
- All affected cogs read this attribute at resolution time — no restart needed.
- If the bot restarts mid-event the multiplier is lost silently; start a new event manually.
- The multiplier always applies to **profit** (payout minus original wager), preventing overpayment when the wager is also returned.
