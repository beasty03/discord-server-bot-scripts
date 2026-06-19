"""
EventDispatcher — maintains priority-ordered handler lists per event name,
fires events, collects raw Effect intents, and returns ResolvedEffects.

Handler signature:  fn(ctx: CombatContext) -> list[Effect] | Effect | None
"""
import logging
from collections import defaultdict
from typing import Callable

log = logging.getLogger("engine")


class EventDispatcher:

    def __init__(self, resolver):
        # event_name → [(priority, fn), ...] sorted high-first
        self._handlers: dict[str, list[tuple[int, Callable]]] = defaultdict(list)
        self._resolver  = resolver

    def subscribe(self, event: str, fn: Callable, priority: int = 0):
        bucket = self._handlers[event]
        bucket.append((priority, fn))
        bucket.sort(key=lambda x: x[0], reverse=True)

    def fire(self, event: str, ctx) -> "ResolvedEffects":
        """
        Call every handler registered for *event* in priority order.
        Collect all Effect intents, resolve, and return ResolvedEffects.
        A handler that raises is logged and skipped — it never breaks the loop.
        """
        raw: list = []
        for _pri, handler in self._handlers.get(event, []):
            try:
                result = handler(ctx)
                if result is None:
                    continue
                if isinstance(result, list):
                    raw.extend(result)
                else:
                    raw.append(result)
            except Exception as exc:
                log.warning("[Dispatcher] handler error on '%s' (%s): %s",
                            event, getattr(handler, "__name__", "?"), exc)
        return self._resolver.resolve(raw)

    def registered_events(self) -> list[str]:
        return list(self._handlers.keys())
