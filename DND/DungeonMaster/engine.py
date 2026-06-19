"""
EngineCore — the content-agnostic D&D runtime Discord Cog.

Responsibilities:
  - Initialize the registry, resolver, dispatcher, and EngineAPI at startup
  - Run the DLC loader (scans DND_DLC/*/variables.py, calls register(api))
  - Expose engine.registry, engine.fire(), engine.roll() to other cogs

Other cogs (combat, shop, character, recipes) obtain a reference via:
    engine = bot.get_cog("EngineCore")
"""
import logging
from pathlib import Path

from discord.ext import commands

from .api        import EngineAPI
from .context    import CombatContext, EnemySnap, PlayerSnap, TurnInfo
from .dice       import roll as _roll
from .dispatcher import EventDispatcher
from .loader     import DLCLoader
from .registry   import ContentRegistry
from .resolver   import EffectResolver, ResolvedEffects

log = logging.getLogger("engine")

def _find_dlc_root() -> Path:
    """Walk up from this file until we find a directory that contains DND_DLC/."""
    candidate = Path(__file__).resolve().parent
    for _ in range(6):
        dlc = candidate / "DND_DLC"
        if dlc.is_dir():
            return dlc
        candidate = candidate.parent
    return Path(__file__).parent.parent.parent / "DND_DLC"  # original fallback

_DLC_ROOT = _find_dlc_root()


class EngineCore(commands.Cog):
    """Content-agnostic D&D runtime. All content comes from DLC folders."""

    def __init__(self, bot: commands.Bot):
        self.bot        = bot
        self.registry   = ContentRegistry()
        _resolver       = EffectResolver()
        self.dispatcher = EventDispatcher(_resolver)
        self.api        = EngineAPI(self.registry, self.dispatcher)

    async def cog_load(self):
        loader = DLCLoader(self.api, _DLC_ROOT)
        loaded, skipped = loader.load_all()
        log.info(
            "[Engine] ready — DLCs: %d loaded / %d skipped | "
            "classes=%d  races=%d  items=%d  campaigns=%d  recipes=%d",
            loaded, skipped,
            len(self.registry.classes),
            len(self.registry.races),
            len(self.registry.items),
            len(self.registry.campaigns),
            len(self.registry.recipes),
        )

    # ── Runtime helpers ────────────────────────────────────────────────────────

    def fire(self, event: str, ctx: CombatContext) -> ResolvedEffects:
        """Fire an engine event and return the fully resolved effects."""
        return self.dispatcher.fire(event, ctx)

    @staticmethod
    def roll(expr: str) -> int:
        """Roll dice. e.g. engine.roll('2d8+3')"""
        return _roll(expr)

    def make_context(
        self,
        player:  PlayerSnap,
        enemy:   EnemySnap,
        turn:    TurnInfo | None = None,
        flags:   dict     | None = None,
    ) -> CombatContext:
        """Convenience factory — builds a CombatContext wired to this engine's dice."""
        return CombatContext(
            player  = player,
            enemy   = enemy,
            turn    = turn  or TurnInfo(),
            flags   = flags or {},
            roll_fn = _roll,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(EngineCore(bot))
    log.info("✅ DND/DungeonMaster engine loaded")
