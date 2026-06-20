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

    @property
    def registry(self):
        """Live registry — capture at registration time for dynamic handler lookups."""
        return self._r

    # ── Content registration ──────────────────────────────────────────────────

    def add_class(self, data: dict):
        # Auto-include any DLC spells that registered *before* this class loaded.
        class_id    = data["id"]
        existing_ids = {a["id"] for a in data.get("abilities", [])}
        for sp in self._r.spells.values():
            if sp.get("class") == class_id and sp["id"] not in existing_ids:
                handler = sp.get("handler")
                data.setdefault("abilities", []).append({
                    "id":        sp["id"],
                    "name":      sp["name"],
                    "label":     sp.get("label", f"{sp.get('emoji', '')} {sp['name']}").strip(),
                    "action":    sp.get("action", "action"),
                    "level_req": sp.get("level_req", 1),
                    "once_per":  sp.get("once_per"),
                    "handler":   handler,
                    "desc":      sp.get("desc", ""),
                })
                log.info("[API] pre-registered spell '%s' merged into '%s'", sp["id"], class_id)
        self._r.add_class(data)
        log.info("[API] class: %s", class_id)

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
        if "class" not in data:
            raise ValueError(f"add_spell({data.get('id')!r}): missing required 'class' field")
        item_id = data["id"]
        handler = data.get("handler")
        if callable(handler):
            self._d.subscribe("on_ability_use", handler)
            log.info("[API] on('on_ability_use') ← %s", handler.__name__)
        self._r.add_spell(data)
        # If the target class is already registered, inject into its abilities now.
        # (If not registered yet, add_class() will pick up pre-registered spells instead.)
        target_class = data["class"]
        cls = self._r.classes.get(target_class)
        if cls is not None and not any(a["id"] == item_id for a in cls.get("abilities", [])):
            cls.setdefault("abilities", []).append({
                "id":        item_id,
                "name":      data["name"],
                "label":     data.get("label", f"{data.get('emoji', '')} {data['name']}").strip(),
                "action":    data.get("action", "action"),
                "level_req": data.get("level_req", 1),
                "once_per":  data.get("once_per"),
                "handler":   handler,
                "desc":      data.get("desc", ""),
            })
            log.info("[API] spell '%s' injected into '%s' abilities", item_id, target_class)
        log.info("[API] spell: %s", item_id)

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
