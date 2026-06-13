# Double Money Event

A server-wide economy boost event. When active, all currency earned across the bot is multiplied by a random value between the configured min and max. The multiplier applies to **profit only** — the original wager is always returned on top of the boosted profit.

## How it works

1. An admin runs `/start_double_money_event`.
2. The bot picks a random multiplier between `MULTIPLIER_MIN` and `MULTIPLIER_MAX` (e.g. **1.47x**).
3. An announcement is posted to the configured channel with a live countdown showing when it ends.
4. For the duration of the event, every currency gain across all supported scripts is multiplied.
5. When time runs out (or an admin uses `/stop_double_money_event`), the multiplier is removed and an end message is posted.

### Example

> Normal gamble win: bet **500**, profit **500** → receive **+500**
> At **1.8x** event: profit **500 × 1.8 = 900** → receive **+900**
> Original bet is always returned separately.

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

> `/give` (player transfers) is intentionally excluded — the multiplier applies to currency earned from the bot, not from other players.

## Commands

### Player

| Command | Description |
|---------|-------------|
| *(none)* | The event is announced in the configured channel; no player command needed |

### Admin / Mod

| Command | Description |
|---------|-------------|
| `/start_double_money_event` | Start the event immediately with a random multiplier |
| `/stop_double_money_event` | End the active event early |
| `/set_double_money_channel #channel` | Set the channel where announcements are posted |
| `/set_double_money_duration <seconds>` | How long the event lasts (default: 300s / 5 min) |
| `/set_double_money_min <value>` | Minimum multiplier, e.g. `1.1` |
| `/set_double_money_max <value>` | Maximum multiplier, e.g. `2.0` |

All `set_` commands require admin/mod permissions (enforced by the bot's channel guard).

## Configuration

### `variables.py`

| Variable | Default | Description |
|----------|---------|-------------|
| `EVENT_CHANNEL_ID` | `0` | Fallback channel ID if not set via command |
| `MULTIPLIER_MIN` | `1.1` | Lowest possible multiplier |
| `MULTIPLIER_MAX` | `2.0` | Highest possible multiplier |
| `EVENT_DURATION` | `300` | Duration in seconds (5 minutes) |

### `double_money_settings.json` (auto-generated)

Persists command-set values across bot restarts. Written automatically by `set_` commands — do not edit manually.

| Key | Type | Description |
|-----|------|-------------|
| `event_channel_id` | int | Channel ID for announcements |
| `event_duration` | int | Duration in seconds |
| `multiplier_min` | float | Minimum multiplier |
| `multiplier_max` | float | Maximum multiplier |

## Setup

1. Load the cog in your bot launcher (same pattern as other cogs):
   ```
   Events/double_money/double_money.py
   ```
2. Run `/set_double_money_channel #your-channel` to configure the announcement channel.
3. Optionally adjust duration and multiplier range with the `set_` commands.
4. Use `/start_double_money_event` to kick off the first event.

## Technical notes

- The active multiplier is stored on the bot object as `bot.double_money_multiplier` (a `float` when active, `None` when not).
- All affected cogs check this attribute at resolution time — no restart or reload required.
- If the bot restarts mid-event, the multiplier is lost and the event ends silently. A new event must be started manually.
- The multiplier always applies to **profit** (payout minus original bet), not the total payout. This prevents overpaying when a player's original bet is also returned on win.
