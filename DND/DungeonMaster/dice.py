import random
import re

_EXPR = re.compile(r'^(\d+)d(\d+)([+-]\d+)?$')


def roll(expr: str) -> int:
    """Roll dice. Supports '2d6', '1d20+5', 'd8-1'. Raises ValueError on bad input."""
    expr = expr.strip().lower()
    if expr.startswith("d"):
        expr = "1" + expr
    m = _EXPR.match(expr)
    if not m:
        raise ValueError(f"Invalid dice expression: {expr!r}")
    n   = max(1, int(m.group(1)))
    d   = max(1, int(m.group(2)))
    mod = int(m.group(3)) if m.group(3) else 0
    return sum(random.randint(1, d) for _ in range(n)) + mod
