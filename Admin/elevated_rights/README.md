# Elevated Rights

Grants a member a role for a fixed duration and removes it automatically when time is up. Useful for temporary VIP access, event roles, timed permissions, "elevated" support access, etc. Grants persist in ForgeDB, so they survive a bot restart — an expired grant is cleaned up the next time the background check runs, even if that's on a fresh process.

Commands: 5

## Commands

- `/elevate @member [role] [duration] [reason]` — grant a role for a duration (default `1h`). `role` is optional if a default is set via `/set_elevate_role`. Duration accepts `s`/`m`/`h`/`d`/`w`, and combinations like `1d12h`.
- `/elevate_remove @member [role]` — revoke a temporary grant early. Same optional-role fallback as `/elevate`.
- `/elevate_list [@member]` — list active grants (all, or just one member's), with time remaining.
- `/set_elevate_role @role` — set the role `/elevate` and `/elevate_remove` use by default when no role is given.
- `/set_elevate_time [default_duration] [max_duration_hours]` — change the server's default `/elevate` duration and/or its max cap. Pass either or both. `max_duration_hours 0` removes the cap.

`/elevate`, `/elevate_remove`, and `/elevate_list` require **Manage Roles**. `/set_elevate_role` and `/set_elevate_time` require **Manage Server**, since they change a server-wide setting rather than acting on one member.

`/elevate` additionally requires:
- the bot's top role to be above the role being granted
- the invoking staff member's top role to be above the role being granted (server owner is exempt)
- the role not be `@everyone` or a managed (bot/integration/booster) role

## Settings

- `CHECK_INTERVAL_SECONDS` (variables.py) — how often the expiry sweep runs, default `60`
- `COLOR_INFO` / `COLOR_ERROR` (variables.py) — embed accent colors
- `MAX_DURATION_HOURS` (variables.py, fallback) — hard cap on how long a single grant can last, default `168` (1 week). Set to `0` to disable the cap.
- `DEFAULT_DURATION` (variables.py, fallback) — duration used when `/elevate` omits the option, default `"1h"`

`MAX_DURATION_HOURS` and `DEFAULT_DURATION` are just the starting fallback values — an admin can override either at runtime per server with `/set_elevate_time`, which is stored in ForgeDB and takes priority over `variables.py`.

There's no `variables.py` fallback for the role itself — until `/set_elevate_role` is run, `role` is required on `/elevate` and `/elevate_remove`.

## Setup

### Prerequisites

- Python 3.10 or higher
- Discord bot token
- [auto-discord-server-deployment](https://github.com/beasty03/auto-discord-server-deployment) setup completed
- Bot must have the **Manage Roles** permission and its role must sit **above** any role it will grant

### Steps

1. **Copy this folder into your cogs directory:**
   ```
   auto-discord-server-deployment/cogs/Admin/elevated_rights/
   ```

2. **Configure `variables.py`** if you want different defaults for duration cap, sweep interval, or embed colors.

3. **Load the cog** in your bot launcher as `Admin.elevated_rights.elevated_rights`.

4. **Grant a role:** `/elevate @user @role 2h reason:"covering the mod shift"`

## How It Works

Each grant is stored in ForgeDB keyed on `(guild_id, user_id, role_id)` with an `expires_at` unix timestamp. A background loop (`tasks.loop`, interval set by `CHECK_INTERVAL_SECONDS`) scans for rows past their expiry, removes the role from the member if they still have it and are still in the guild, and deletes the row. Running `/elevate` again for a member who already holds the role from a prior grant simply overwrites the expiry (`INSERT OR REPLACE`), so re-running it extends the grant rather than stacking duplicate rows.

If the member left the guild, or the guild/role no longer exists, the stale row is just cleaned up without attempting a role removal.

> **Note:** Discord itself has no concept of a temporary role — this is enforced entirely by the bot's own sweep, so the bot must stay running (or restart promptly) for expiry to be reliable.
