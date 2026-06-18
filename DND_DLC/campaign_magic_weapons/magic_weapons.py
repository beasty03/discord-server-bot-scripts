import logging
from pathlib import Path
import importlib.util as _ilu
from discord.ext import commands

_spec = _ilu.spec_from_file_location('magic_weapons_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

log = logging.getLogger("launcher")


class MagicWeaponsDLC(commands.Cog):
    _dlc_shop_items = var.SHOP_ITEMS   # discovered by ShopCog without load-order dependency

    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    char = bot.get_cog("CharacterCog")

    if char:
        for weapon in var.WEAPONS:
            char.register_item(weapon)
        for item in var.SHOP_ITEMS:
            char.register_shop_item(item)
    else:
        log.warning("Magic Weapons DLC: CharacterCog not loaded — weapons not registered.")

    await bot.add_cog(MagicWeaponsDLC(bot))
    log.info("✅ DND_DLC/campaign_magic_weapons loaded")
