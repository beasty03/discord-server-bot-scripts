"""
automod_config.py
=================
Singleton config for the Automod cog.  Persists to Admin/automod/automod_settings.json.
"""
from __future__ import annotations
import json
from pathlib import Path

_CONFIG_FILE = Path(__file__).parent / "automod_settings.json"

_DEFAULTS: dict = {
    "enabled": False,
    "log_channel_id":   None,
    "log_channel_name": None,
    "filters": {
        "bad_words": {
            "enabled": True,
            "words": [],
        },
        "spam": {
            "enabled":        True,
            "max_messages":   5,
            "window_seconds": 5,
        },
        "caps": {
            "enabled":    True,
            "percent":    80,
            "min_length": 15,
        },
        "mentions": {
            "enabled":   True,
            "max_count": 5,
        },
        "links": {
            "enabled":             False,
            "whitelisted_domains": [
                "discord.com", "discord.gg", "tenor.com", "giphy.com",
                "imgur.com", "youtube.com", "youtu.be",
            ],
        },
    },
    "actions": {
        "warn_threshold":  3,
        "timeout_minutes": 5,
    },
    "whitelist_role_ids": [],
}


class AutomodConfig:
    _inst: AutomodConfig | None = None

    def __new__(cls):
        if cls._inst is None:
            inst        = super().__new__(cls)
            inst._d     = inst._load()
            cls._inst   = inst
        return cls._inst

    def _load(self) -> dict:
        if _CONFIG_FILE.exists():
            try:
                return json.loads(_CONFIG_FILE.read_text("utf-8"))
            except Exception:
                pass
        import copy
        return copy.deepcopy(_DEFAULTS)

    def _save(self):
        _CONFIG_FILE.write_text(json.dumps(self._d, indent=2, ensure_ascii=False), "utf-8")

    # ── Enabled ───────────────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._d.get("enabled", False)

    def set_enabled(self, value: bool):
        self._d["enabled"] = value
        self._save()

    # ── Log channel ───────────────────────────────────────────────────────────

    @property
    def log_channel_id(self) -> int | None:
        return self._d.get("log_channel_id")

    @property
    def log_channel_name(self) -> str | None:
        return self._d.get("log_channel_name")

    def set_log_channel(self, cid: int, name: str):
        self._d["log_channel_id"]   = cid
        self._d["log_channel_name"] = name
        self._save()

    # ── Filter helpers ────────────────────────────────────────────────────────

    def _filter(self, name: str) -> dict:
        return self._d.setdefault("filters", {}).setdefault(name, {})

    def _set_filter(self, name: str, key: str, value):
        self._filter(name)[key] = value
        self._save()

    # ── Bad words ─────────────────────────────────────────────────────────────

    def bad_words(self) -> list[str]:
        return self._filter("bad_words").get("words", [])

    def bad_words_enabled(self) -> bool:
        return self._filter("bad_words").get("enabled", True)

    def add_bad_word(self, word: str):
        w = word.lower().strip()
        words = self.bad_words()
        if w not in words:
            words.append(w)
            self._set_filter("bad_words", "words", words)

    def remove_bad_word(self, word: str) -> bool:
        w     = word.lower().strip()
        words = self.bad_words()
        if w in words:
            words.remove(w)
            self._set_filter("bad_words", "words", words)
            return True
        return False

    def set_bad_words_enabled(self, value: bool):
        self._set_filter("bad_words", "enabled", value)

    # ── Spam ──────────────────────────────────────────────────────────────────

    def spam(self) -> dict:
        return self._filter("spam")

    def set_spam(self, max_msgs: int, window: int):
        f = self._filter("spam")
        f["max_messages"]   = max_msgs
        f["window_seconds"] = window
        f["enabled"]        = True
        self._save()

    def spam_enabled(self) -> bool:
        return self._filter("spam").get("enabled", True)

    def set_spam_enabled(self, value: bool):
        self._set_filter("spam", "enabled", value)

    # ── Caps ──────────────────────────────────────────────────────────────────

    def caps(self) -> dict:
        return self._filter("caps")

    def set_caps(self, percent: int, min_length: int = 15):
        f = self._filter("caps")
        f["percent"]    = percent
        f["min_length"] = min_length
        f["enabled"]    = percent > 0
        self._save()

    def caps_enabled(self) -> bool:
        return self._filter("caps").get("enabled", True)

    # ── Mentions ──────────────────────────────────────────────────────────────

    def mentions(self) -> dict:
        return self._filter("mentions")

    def set_max_mentions(self, count: int):
        f = self._filter("mentions")
        f["max_count"] = count
        f["enabled"]   = count > 0
        self._save()

    def mentions_enabled(self) -> bool:
        return self._filter("mentions").get("enabled", True)

    # ── Links ─────────────────────────────────────────────────────────────────

    def links(self) -> dict:
        return self._filter("links")

    def links_enabled(self) -> bool:
        return self._filter("links").get("enabled", False)

    def set_links_enabled(self, value: bool):
        self._set_filter("links", "enabled", value)

    def link_whitelist(self) -> list[str]:
        return self._filter("links").get("whitelisted_domains", [])

    def add_link_whitelist(self, domain: str) -> bool:
        d       = domain.lower().strip().lstrip("www.")
        domains = self.link_whitelist()
        if d not in domains:
            domains.append(d)
            self._set_filter("links", "whitelisted_domains", domains)
            return True
        return False

    def remove_link_whitelist(self, domain: str) -> bool:
        d       = domain.lower().strip().lstrip("www.")
        domains = self.link_whitelist()
        if d in domains:
            domains.remove(d)
            self._set_filter("links", "whitelisted_domains", domains)
            return True
        return False

    # ── Actions ───────────────────────────────────────────────────────────────

    def warn_threshold(self) -> int:
        return self._d.get("actions", {}).get("warn_threshold", 3)

    def set_warn_threshold(self, n: int):
        self._d.setdefault("actions", {})["warn_threshold"] = n
        self._save()

    def timeout_minutes(self) -> int:
        return self._d.get("actions", {}).get("timeout_minutes", 5)

    def set_timeout_minutes(self, n: int):
        self._d.setdefault("actions", {})["timeout_minutes"] = n
        self._save()

    # ── Whitelist roles ───────────────────────────────────────────────────────

    def whitelist_role_ids(self) -> list[int]:
        return self._d.get("whitelist_role_ids", [])

    def add_whitelist_role(self, rid: int) -> bool:
        ids = self.whitelist_role_ids()
        if rid not in ids:
            ids.append(rid)
            self._d["whitelist_role_ids"] = ids
            self._save()
            return True
        return False

    def remove_whitelist_role(self, rid: int) -> bool:
        ids = self.whitelist_role_ids()
        if rid in ids:
            ids.remove(rid)
            self._d["whitelist_role_ids"] = ids
            self._save()
            return True
        return False
