
# 📥 Import Quotes

Bulk-import old quotes from any channel into the Quotes database. Scans messages in `"quote - Name"` format, resolves names to Discord user IDs via a configurable name map, attaches GIFs posted within 5 minutes of the quote, and shows a confirmation preview before writing anything.

Commands: 1

## 📋 Features

- 🔍 **Channel scan** — reads the full history of any text channel and picks out quote-formatted messages
- 🔄 **Duplicate detection** — skips quotes already in the database; updates user IDs for entries that were stored with an unresolved name
- 🖼️ **GIF linking** — pairs a GIF sent within 5 minutes of the quote message automatically
- 👤 **Name mapping** — maps display names to Discord user IDs via `NAME_MAP` in `variables.py`
- ✅ **Confirm before import** — shows a preview of what will be imported with Import / Cancel buttons
- 🔒 **Role-gated** — only users with the **Quote Tracker** role can run the command

## 🚀 Installation

Load the cog as `Quotes.import_quotes.import_quotes`.

## 🎮 Commands

| Command | Description |
|---------|-------------|
| `/quote_import <channel>` | Scan a channel and import quotes in `"quote - Name"` format |

## ⚙️ Configuration (`variables.py`)

| Variable | Description |
|----------|-------------|
| `NAME_MAP` | Dict mapping display names to `(user_id, display_name)` tuples |

### Name map example

```python
NAME_MAP = {
    "John":    ("123456789012345678", "John"),
    "Alice":   ("987654321098765432", "Alice"),
}
```

Names not found in `NAME_MAP` are stored with user ID `0` and flagged in the confirmation summary. You can add them to the map and re-import — duplicates are skipped automatically, so only the unresolved entries will be updated.
