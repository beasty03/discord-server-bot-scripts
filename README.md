# discord-server-bot-scripts

Modular Discord bot (discord.py 2.x). Each feature lives in its own folder — the launcher auto-discovers and loads everything. Adding a script means creating a folder, not touching the core.

---

## Repo structure

```
Category/
└── scriptname/
    ├── scriptname.py   ← the cog (commands live here)
    ├── variables.py    ← all config and constants
    └── README.md       ← what the script does (required)
```

All three files are required. The `README.md` is displayed in the app to show users and contributors what the script does and how to configure it.

Current categories: `Admin` · `Casino` · `DND` · `Events` · `General` · `Quotes` · `User` · `Webhooks`

---

## Adding a new script

### 1. Create the folder

Pick the right category and name the folder after your script. All three files are mandatory.

```
Casino/mygame/
├── mygame.py      ← cog
├── variables.py   ← config
└── README.md      ← shown in the app; describe what the script does and its config options
```

### 2. Write `variables.py`

```python
from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

# your constants here
MIN_BET = 10
MAX_BET = -1  # -1 = no limit

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

COLOR_WIN   = 0x57F287
COLOR_LOSE  = 0xED4245
COLOR_INFO  = 0x5865F2
COLOR_ERROR = 0xED4245
```

### 3. Write `mygame.py`

```python
import discord
import importlib.util as _ilu
import logging
from pathlib import Path
from discord import app_commands
from discord.ext import commands

# Always load variables.py this way — never use sys.path.insert + import variables
_spec = _ilu.spec_from_file_location('mygame_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

from forge_db import ForgeDB  # the only database interface — never edit forge_db.py

log = logging.getLogger("launcher")


class MyGameCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    @app_commands.command(name="mygame", description="What this command does.")
    async def mygame(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello!")


async def setup(bot: commands.Bot):
    await bot.add_cog(MyGameCog(bot))
    log.info("✅ Casino/MyGame cog loaded")
```

**Two hard rules:**
- Always use `importlib.util` with a **unique** module name (`mygame_variables`). Using `sys.path.insert + import variables` breaks other cogs because Python caches the module name.
- Never edit `forge_db.py` or `database_manager.py`. Only call `ForgeDB.get()`.

### 4. Register in `General/help/help.py`

Add one line to the relevant category's `sections` list:

```python
("🎮 My Game", "MyGameCog"),
```

The cog class name in `sections` must exactly match the class name in your `.py` file.

> **Note:** The `description` field on each category in help.py is a Discord `SelectOption` description — max **100 characters**. Exceeding it raises a `ValueError` at runtime.

---

## ForgeDB quick reference

```python
db = ForgeDB.get()

db.ensure_user(uid, gid, display_name)        # call before any balance operation
db.get_balance(uid, gid) -> int
db.update_balance(uid, gid, delta, tx_type)   # delta is negative to deduct
db.execute(sql, params=()) -> list[tuple]      # raw SQL for custom reads/writes
```

All user and guild IDs are stored and passed as **strings**: `uid = str(interaction.user.id)`.

---

## Key patterns used across cogs

Look at an existing cog in the same category for a full working example. Patterns worth knowing:

- **House bank** — every money-moving cog mirrors player transactions to a bot-user "house" account. See `Casino/gamble/gamble.py`.
- **Stats recording** — `INSERT INTO casino_stats … ON CONFLICT DO UPDATE`. Copied identically in every casino cog.
- **Background game loop** — `asyncio.create_task(self._run_game(...))` with a `try/except/finally` that clears the active-game flag. See `Casino/horseracing/horseracing.py`.
- **Buttons** — `discord.ui.View` subclass with `@discord.ui.button` decorators. Use `ephemeral=True` for private responses.
- **Dynamic buttons** — use a `_make_callback(self, item)` closure, never `lambda` (late-binding bug).
- **Discord timestamps** — `<t:{unix_ts}:R>` goes negative after expiry. Switch to static text when a phase closes.
- **Multiplier event** — `dm_mult = getattr(self.bot, 'multiplier_event_mult', None) or 1.0` in any payout.
