"""
EngineAPI — the LOCKED load-time surface passed to every DLC's register(api) call.

Engine internals may be refactored freely.
This interface must remain stable: never remove or rename a method.
Adding new methods is safe.
"""
import logging
from typing import Callable

log = logging.getLogger("engine")

# Item dict keys that map to engine event names.
# When a DLC adds an item with one of these keys, the engine automatically
# wraps the handler with an equipped-check and subscribes it globally.
_ITEM_HOOKS: dict[str, str] = {
    "on_hit":         "on_hit",
    "on_damage_roll": "on_damage_roll",
    "on_take_damage": "on_take_damage",
    "on_use":         "on_item_use",
    "on_equip":       "on_item_equip",
}


def _make_item_guard(item_id: str, fn: Callable) -> Callable:
    """Wrap an item handler so it only fires when the item is in ctx.player.equipped."""
    def _guarded(ctx):
        if not any(i.get("id") == item_id for i in ctx.player.equipped):
            return []
        return fn(ctx)
    _guarded.__name__ = f"{item_id}:{fn.__name__}"
    return _guarded


class EngineAPI:
    """
    Passed as the sole argument to every DLC's register(api) function.

    DLCs call:
      api.add_class(data)         — register a playable class
      api.add_race(data)          — register a playable race
      api.add_item(data)          — register an item (auto-wires on_hit etc.)
      api.add_spell(data)         — register a spell
      api.add_campaign(data)      — register a campaign
      api.add_recipe(data)        — register a crafting recipe
      api.add_shop_item(data)     — register a shop listing
      api.on(event, fn, priority) — subscribe a handler to an engine event
      api.define_status(...)      — declare a status id for use in Status() effects
      api.define_damage_type(...) — declare a damage type for use in Modify(damage_type=)
    """

    def __init__(self, registry, dispatcher):
        self._r = registry
        self._d = dispatcher

    # ── Content registration ──────────────────────────────────────────────────

    def add_class(self, data: dict):
        self._r.add_class(data)
        log.info("[API] class: %s", data.get("id"))

    def add_race(self, data: dict):
        self._r.add_race(data)
        log.info("[API] race: %s", data.get("id"))

    def add_item(self, data: dict):
        item_id = data["id"]
        for key, event in _ITEM_HOOKS.items():
            handler = data.get(key)
            if callable(handler):
                self._d.subscribe(event, _make_item_guard(item_id, handler))
        self._r.add_item(data)
        log.info("[API] item: %s", item_id)

    def add_spell(self, data: dict):
        self._r.add_spell(data)
        log.info("[API] spell: %s", data.get("id"))

    def add_campaign(self, data: dict):
        self._r.add_campaign(data)
        log.info("[API] campaign: %s", data.get("id"))

    def add_recipe(self, data: dict):
        self._r.add_recipe(data)
        log.info("[API] recipe: %s", data.get("id"))

    def add_shop_item(self, data: dict):
        self._r.add_shop_item(data)
        log.info("[API] shop item: %s", data.get("id"))

    # ── Event subscription ────────────────────────────────────────────────────

    def on(self, event: str, fn: Callable, priority: int = 0):
        """
        Subscribe fn to a named engine event.

        fn(ctx: CombatContext) → list[Effect] | Effect | None

        Higher priority handlers run first. Default priority is 0.
        Handlers at the same priority run in registration order.
        """
        self._d.subscribe(event, fn, priority)
        log.info("[API] on('%s') ← %s (priority=%d)", event, fn.__name__, priority)

    # ── Vocabulary ────────────────────────────────────────────────────────────

    def define_status(self, status_id: str, label: str, icon: str = "",
                      effects: dict | None = None):
        """
        Declare a status effect.

        effects keys (all optional, engine reads and applies them):
          "enemy_ac_penalty":   int   — reduce enemy AC by N while active
          "enemy_atk_penalty":  int   — reduce enemy attack bonus by N while active
          "player_ac_bonus":    int   — add N to player's effective AC while active
          "damage_mult":        float — multiply incoming damage by this (e.g. 0.5)
          "clears_on_hit":      bool  — engine removes status after the player next hits
          "clears_on_take_hit": bool  — engine removes status after the player is next hit
          "clears_on_turn":     bool  — engine removes status at end of this turn
        """
        self._r.define_status(status_id, label, icon, effects or {})

    def define_damage_type(self, type_id: str, label: str, icon: str = ""):
        """Declare a damage type id so it can be referenced in Modify(damage_type=)."""
        self._r.define_damage_type(type_id, label, icon)
