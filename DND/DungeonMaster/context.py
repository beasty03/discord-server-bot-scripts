"""
CombatContext — the LOCKED runtime surface every DLC handler receives.

Handlers read this object. They NEVER mutate it.
All changes are expressed by returning Effect intents.

This interface must not change after DLC authors start using it.
If new fields are needed, add them; never remove or rename existing ones.
"""
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class PlayerSnap:
    """Immutable-by-convention snapshot of a player at the moment an event fires."""
    id:        str
    name:      str
    level:     int
    char_class: str
    race:      str
    subclass:  str | None
    stats:     dict          # {"strength": 16, "str_mod": 3, "dexterity": 12, ...}
    hp:        int
    max_hp:    int
    equipped:  list          # list of full item dicts from registry (id, slot, dmg, ...)
    subrace:   str | None = None


@dataclass
class EnemySnap:
    """Immutable-by-convention snapshot of the current enemy."""
    name:      str
    emoji:     str
    hp:        int
    max_hp:    int
    ac:        int
    atk_bonus: int
    dmg:       str           # dice expression, e.g. "2d6+3"


@dataclass
class TurnInfo:
    """Facts about the current action / roll in progress."""
    attack_roll:  int        = 0
    is_crit:      bool       = False
    is_hit:       bool       = False
    base_damage:  int        = 0
    damage_type:  str | None = None
    ability_id:   str | None = None    # set when action type is "ability"
    check_type:   str | None = None    # e.g. "perception" during skill checks
    check_roll:   int | None = None


class CombatContext:
    """
    The single object passed to every DLC handler at runtime.

    Read-only by enforcement — attempting to set any attribute raises AttributeError.
    Use ctx.roll("2d6+3") to roll dice.
    Use ctx.has_flag("advantage") to read combat flags.
    """

    def __init__(
        self,
        player:  PlayerSnap,
        enemy:   EnemySnap,
        turn:    TurnInfo,
        flags:   dict,
        roll_fn: Callable[[str], int],
    ):
        object.__setattr__(self, "_player",  player)
        object.__setattr__(self, "_enemy",   enemy)
        object.__setattr__(self, "_turn",    turn)
        object.__setattr__(self, "_flags",   dict(flags))
        object.__setattr__(self, "_roll_fn", roll_fn)

    def __setattr__(self, name, value):
        raise AttributeError(
            "CombatContext is read-only. Return Effect intents instead of mutating state."
        )

    @property
    def player(self) -> PlayerSnap:  return self._player
    @property
    def enemy(self)  -> EnemySnap:   return self._enemy
    @property
    def turn(self)   -> TurnInfo:    return self._turn
    @property
    def flags(self)  -> dict:        return self._flags

    def roll(self, expr: str) -> int:
        """Roll dice using the engine's RNG. e.g. ctx.roll('2d8+3')"""
        return self._roll_fn(expr)

    def has_flag(self, name: str) -> bool:
        """Check a boolean combat flag. Safe to call for any name."""
        return bool(self._flags.get(name, False))
