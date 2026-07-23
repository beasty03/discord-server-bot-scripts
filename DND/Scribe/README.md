# 📖 Scribe

Records campaign runs and generates a narrative story recap. Currently template-based — structured for an Ollama drop-in when ready.

---

Commands: 2

## Commands

| Command | Description |
|---|---|
| `/story [user]` | Show the story of a player's last completed campaign run. |
| `/set_scribe_channel <channel>` | Set the channel for auto-posted stories (admin only). |

---

## How it works

The DungeonMaster logs every significant event during a run — attacks, kills (with any flavor text the player typed), skill checks, flee actions. After the run, that log is saved to `dnd_run_log`.

`/story` reads the most recent run log for a user and turns it into a narrative using the template engine. Kill descriptions typed by players are embedded directly into the story as quotes.

### Ollama slot

The `_generate_story()` function in `scribe.py` has a `# TODO` comment marking exactly where the template logic should be replaced by an Ollama call. When ready:

1. Feed the structured `run_log` list as context to the Ollama prompt
2. Return the model's prose instead of the templated string
3. No other changes needed

---

## Configuration (`variables.py`)

| Variable | Default | Description |
|---|---|---|
| `SCRIBE_CHANNEL_ID` | `0` | Channel for auto-posting stories; 0 = disabled. Set via `/set_scribe_channel`. |
