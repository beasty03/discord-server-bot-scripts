"""
Shared log-category config.  Import this anywhere to check whether a
bot-logs category is currently enabled before posting.

Usage:
    from Admin.panel.log_config import is_log_enabled

    if is_log_enabled("house_daily"):
        await bot_logs.send(embed=embed)
"""
import json
from pathlib import Path
from threading import Lock

_CONFIG_PATH = Path(__file__).parent / "log_control_settings.json"
_LOCK = Lock()

# ── default state (all enabled) ───────────────────────────────────────────────

CATEGORIES: dict[str, str] = {
    "house_daily":   "House daily income posts",
    "fight_results": "Tamagotchi fight outcomes",
    "api_warnings":  "Missing API key alerts",
    "automod":       "AutoMod violation log (posted to #mod-logs)",
    "tamagotchi":    "Pet adoption and death events",
}


def _load() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict):
    with _LOCK:
        _CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_log_enabled(category: str) -> bool:
    """Return True if the given log category is enabled (default: True)."""
    return _load().get(category, True)


def toggle_log(category: str) -> bool:
    """Toggle a category and return the new state."""
    data = _load()
    new_state = not data.get(category, True)
    data[category] = new_state
    _save(data)
    return new_state


def get_all() -> dict[str, bool]:
    """Return {category: enabled} for all known categories."""
    data = _load()
    return {k: data.get(k, True) for k in CATEGORIES}
