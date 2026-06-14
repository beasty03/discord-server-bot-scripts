# 🛡️ Parties

Form and manage adventuring parties. All actions live under the `/party` command group. A character (from the `character` script) is required to use any party command.

## Commands

| Command | Description |
|---------|-------------|
| `/party create [public\|private]` | Create a party with yourself as the first member. Public parties appear in `/party join`; private ones are invite-only. Defaults to public. |
| `/party join` | Browse open public parties and pick one to join. |
| `/party invite <user>` | Send an Accept/Decline invite to a player — the only way into a private party. |
| `/party leave` | Leave your current party. |

## Rules

- A character (`/name`, `/race`, `/class`) is required before using any party command.
- One party per player per server — use `/party leave` before joining or creating another.
- Any member can invite, not just the creator.
- If the creator leaves, the party stays alive and the label transfers to a remaining member.
- An empty party is automatically cleaned up.

## Configuration (`variables.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_PARTY_SIZE` | `6` | Maximum members per party (creator included) |
| `JOIN_LIST_TIMEOUT` | `120` | Seconds the `/party join` picker stays clickable |
| `INVITE_TIMEOUT` | `300` | Seconds an Accept/Decline invite stays live |
| `MAX_JOIN_BUTTONS` | `20` | Max parties shown in the join picker (Discord max is 25 buttons) |
