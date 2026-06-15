import importlib.util as _ilu
import logging
from pathlib import Path

from discord.ext import commands

_spec = _ilu.spec_from_file_location('beast_hunt_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

log = logging.getLogger("launcher")


class BeastHuntDLC(commands.Cog):
    """DLC campaign — no slash commands, exists only to register content."""
    pass


async def setup(bot: commands.Bot):
    dm = bot.get_cog("DungeonMasterCog")
    if dm:
        dm.register_campaign(var.CAMPAIGN)
    else:
        log.warning("BeastHunt DLC: DungeonMasterCog not loaded — campaign not registered. "
                    "Make sure DND/DungeonMaster loads before DND_DLC cogs.")
    await bot.add_cog(BeastHuntDLC(bot))
    log.info("✅ DND_DLC/BeastHunt loaded")
