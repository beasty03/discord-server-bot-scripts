# 🌈 Rainbow Role

A role whose color automatically cycles through the rainbow on a background loop. Members opt in and out with a single command — the color itself keeps shifting for everyone who has the role, whether or not the bot restarts in between.

Commands: 4

## Commands

- `/rainbow_join` — get the rainbow role. Auto-creates it (named `🌈 Rainbow` by default) the first time it's used if no role has been configured yet.
- `/rainbow_leave` — remove your rainbow role.
- `/set_rainbow_role <role>` — use an existing role instead of the auto-created one.
- `/set_rainbow_speed <seconds>` — change how often the color shifts (minimum enforced to avoid Discord rate limits).

`/rainbow_join` and `/rainbow_leave` are open to everyone. `/set_rainbow_role` and `/set_rainbow_speed` require **Manage Server**.

## Settings (variables.py)

- `DEFAULT_ROLE_NAME` — name used when `/rainbow_join` auto-creates the role, default `"🌈 Rainbow"`.
- `DEFAULT_INTERVAL_SECONDS` — how often (seconds) the color shifts, default `5`. Overridable per server at runtime with `/set_rainbow_speed`.
- `HUE_STEP_DEGREES` — how far (out of 360°) the hue advances each shift, default `6` (a full cycle takes 60 shifts).
- `MIN_INTERVAL_SECONDS` — lowest value `/set_rainbow_speed` will accept, default `1`, to keep the bot from hammering Discord's rate limit on role edits.

## Setup

### Prerequisites

- Python 3.10 or higher
- Discord bot token
- [auto-discord-server-deployment](https://github.com/beasty03/auto-discord-server-deployment) setup completed
- Bot must have the **Manage Roles** permission, and its top role must sit above wherever the rainbow role ends up

### Steps

1. **Copy this folder into your cogs directory:**
   ```
   auto-discord-server-deployment/cogs/Aesthetic/rainbow_role/
   ```

2. **Configure `variables.py`** if you want a different default name, cycle speed, or step size.

3. **Load the cog** in your bot launcher as `Aesthetic.rainbow_role.rainbow_role`.

4. Run `/rainbow_join` to try it out.

## How It Works

The first `/rainbow_join` on a server auto-creates the role (or an admin can hand-pick one first with `/set_rainbow_role`) and stores its ID, current hue, and shift interval in ForgeDB, keyed by guild. A single background loop (`tasks.loop`) ticks on the configured interval, advancing each configured server's hue by `HUE_STEP_DEGREES` and converting it to RGB via HSV, then edits the role's color. The current hue is persisted, so a bot restart resumes the cycle roughly where it left off instead of snapping back to red.

If the bot loses the **Manage Roles** permission or its position drops below the rainbow role, color updates for that server are skipped (and logged) until the setup is fixed — nothing crashes, it just stops shifting.
