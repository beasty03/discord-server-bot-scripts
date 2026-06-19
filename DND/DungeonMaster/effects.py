"""
Typed effect intents — the only thing DLC handlers are allowed to return.

Handlers never mutate state. They return a list of these objects; the engine
collects them from all subscribed handlers and resolves them deterministically.

Resolution rules (documented, order-independent for the common case):
  Modify.add   — all additions sum
  Modify.mult  — all multipliers multiply together
  Flag         — OR across all handlers (any True wins)
  Heal         — amounts accumulate
  Status       — all statuses applied
  BonusAttack  — count accumulates
  Message      — all messages shown in order
"""
from dataclasses import dataclass


@dataclass
class Modify:
    """Adjust a numeric value in the engine's current calculation."""
    target:      str         # "damage" | "attack_roll" | "ac" | "heal_amount" | any custom string
    add:         int   = 0
    mult:        float = 1.0
    damage_type: str | None = None   # optional tag (e.g. "fire") applied to the added amount


@dataclass
class Heal:
    """Restore HP."""
    amount: int
    target: str = "self"   # "self" | "ally"


@dataclass
class Status:
    """Apply a status effect by id."""
    status_id: str
    duration:  int = 1     # turns; -1 = lasts until explicitly cleared


@dataclass
class Flag:
    """Set a boolean combat flag (e.g. advantage, shielded)."""
    name:  str
    value: bool = True


@dataclass
class BonusAttack:
    """Grant one additional attack this turn."""
    pass


@dataclass
class Message:
    """Append a line to the combat log for this event."""
    text: str


# Convenience union — use in type hints inside DLC files
Effect = Modify | Heal | Status | Flag | BonusAttack | Message
