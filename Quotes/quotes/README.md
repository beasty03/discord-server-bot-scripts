# Quotes

A channel-based quote system. Members can quote each other with `/quote`, which posts a formatted embed to a dedicated quotes channel. After each quote, the quoter must drop a gif in the channel before the next quote can be posted — keeping the channel lively.

Commands: 10

## How it works

1. An admin sets the quotes channel with `/set_quote_channel`.
2. Any member runs `/quote @user <text>`.
3. The bot posts the quote as an embed in the quotes channel.
4. The quoter receives an ephemeral prompt to drop a gif in the quotes channel.
5. Once a gif is detected from that user in the quotes channel, the lock clears and `/quote` is available again.

### Example

> `/quote @Alice "I told you the build would break"`
>
> Posts in #quotes:
> ```
> > I told you the build would break
>
> — Alice
> Quoted by Bob · Server Name
> ```
> Bob then drops a gif in #quotes → next quote is unlocked.

## Commands

| Command | Who | Description |
|---------|-----|-------------|
| `/quote @user <text>` | Everyone | Post a quote attributed to a user |
| `/set_quote_channel #channel` | Admin | Set the channel where quotes are posted |

## Gif gate

- Only one quote can be pending per server at a time.
- After a `/quote`, **only the person who ran the command** can unlock the next one by posting a gif.
- The gif must be posted in the **quotes channel** (not any other channel).
- Accepted gif formats: Discord's native gif picker (Tenor/Giphy), `.gif` file attachments, or raw tenor.com / giphy.com links.
- If someone tries `/quote` while a gif is pending, they see who needs to post and where.

## Setup

1. Load the cog in your bot launcher:
   ```
   Quotes/quotes/quotes.py
   ```
2. Run `/set_quote_channel #your-channel` to configure where quotes appear.
3. Members can now use `/quote`.

## Configuration

### `quotes_settings.json` (auto-generated)

| Key | Type | Description |
|-----|------|-------------|
| `quote_channel_id` | int | Channel ID where quotes are posted |

## Technical notes

- The pending gif state is stored in memory (`bot` object), so a bot restart clears any active lock.
- The gif gate is per-guild — different servers track their own pending state independently.
- `/set_quote_channel` requires the `Administrator` permission.
