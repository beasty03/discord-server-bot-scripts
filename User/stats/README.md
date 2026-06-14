# 📊 Stats

Shows a player's profile card — level, balance, and anything else added to the stats system over time.

## Commands

| Command | Description |
|---------|-------------|
| `/stats [user]` | View your own profile, or another player's by mentioning them |

## Display

The embed shows:

- **Level** — driven by the XP system (placeholder until XP is implemented)
- **Balance** — current coin balance

## Extending

New stat fields plug in here. To add one:

1. Pull the data from `ForgeDB` inside `StatsCog.stats`
2. Add an `embed.add_field(...)` call
3. If it needs a new DB table, create it in `cog_load` with `CREATE TABLE IF NOT EXISTS`

The `_get_level(uid, gid, db)` function at the top of `stats.py` is the single place to swap in the real XP lookup once the system is ready.
