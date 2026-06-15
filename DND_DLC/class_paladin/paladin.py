import logging
from pathlib import Path

import importlib.util as _ilu
from discord.ext import commands

_spec = _ilu.spec_from_file_location('paladin_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

log = logging.getLogger("launcher")


class PaladinDLC(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    dm = bot.get_cog("DungeonMasterCog")
    if dm:
        dm.register_class(var.CLASS)
    char = bot.get_cog("CharacterCog")
    if char:
        char.register_item({"id": "holy_symbol", "name": "Holy Symbol", "emoji": "✝️", "slot": "misc"})
    await bot.add_cog(PaladinDLC(bot))
    log.info("✅ DND_DLC/class_paladin loaded")
