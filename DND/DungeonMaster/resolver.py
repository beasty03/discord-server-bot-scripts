"""
EffectResolver — collects Effect intents from all handlers and resolves them
into one deterministic ResolvedEffects value.

Resolution rules (order-independent for the common case):
  Modify.add    → all additions sum
  Modify.mult   → all multipliers multiply together
  Flag          → OR across all handlers (any True wins)
  Heal          → amounts accumulate
  Status        → all applied
  BonusAttack   → count accumulates
  Message       → appended in handler priority order
"""
from dataclasses import dataclass, field
from .effects import BonusAttack, Flag, Heal, Message, Modify, Status


@dataclass
class ResolvedEffects:

    # Damage resolution
    damage_add:        int        = 0
    damage_mult:       float      = 1.0
    damage_type_tags:  list[str]  = field(default_factory=list)

    # Healing
    heal_self:         int        = 0
    heal_ally:         int        = 0

    # Combat extras
    bonus_attacks:     int        = 0

    # State
    statuses:          list[tuple] = field(default_factory=list)   # [(id, duration), ...]
    flags:             dict        = field(default_factory=dict)

    # Generic modifiers for non-damage targets (attack_roll, ac, etc.)
    # target → (total_add, total_mult)
    modifiers:         dict        = field(default_factory=dict)

    # Display
    messages:          list[str]   = field(default_factory=list)

    # ── Helpers called by the engine ──────────────────────────────────────────

    def apply_final_damage(self, base: int) -> int:
        """(base + sum_adds) * product_mults, floored at 0."""
        return max(0, int((base + self.damage_add) * self.damage_mult))

    def apply_modifier(self, target: str, base: int) -> int:
        """Apply accumulated add+mult for a named target value, floored at 0."""
        add, mult = self.modifiers.get(target, (0, 1.0))
        return max(0, int((base + add) * mult))


class EffectResolver:

    def resolve(self, effects: list) -> ResolvedEffects:
        r = ResolvedEffects()
        for e in effects:
            if isinstance(e, Modify):
                if e.target == "damage":
                    r.damage_add  += e.add
                    r.damage_mult *= e.mult
                    if e.damage_type:
                        r.damage_type_tags.append(e.damage_type)
                else:
                    prev_add, prev_mult = r.modifiers.get(e.target, (0, 1.0))
                    r.modifiers[e.target] = (prev_add + e.add, prev_mult * e.mult)
            elif isinstance(e, Heal):
                if e.target == "self":
                    r.heal_self += e.amount
                else:
                    r.heal_ally += e.amount
            elif isinstance(e, Status):
                r.statuses.append((e.status_id, e.duration))
            elif isinstance(e, Flag):
                r.flags[e.name] = r.flags.get(e.name, False) or e.value
            elif isinstance(e, BonusAttack):
                r.bonus_attacks += 1
            elif isinstance(e, Message):
                r.messages.append(e.text)
        return r
