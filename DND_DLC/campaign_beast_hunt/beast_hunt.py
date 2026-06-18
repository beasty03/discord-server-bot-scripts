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
    _dlc_shop_items   = [var.SHOP_ITEM]    # discovered by ShopCog without load-order dependency
    _dlc_shop_bundles = [var.SHOP_BUNDLE]


async def setup(bot: commands.Bot):
    dm = bot.get_cog("DungeonMasterCog")
    if dm:
        dm.register_campaign(var.CAMPAIGN)
    else:
        log.warning("BeastHunt DLC: DungeonMasterCog not loaded — campaign not registered.")

    shop = bot.get_cog("ShopCog")
    if shop:
        shop.register_item(var.SHOP_ITEM)
        shop.register_bundle(var.SHOP_BUNDLE)
    else:
        log.warning("BeastHunt DLC: ShopCog not loaded — shop items not registered.")

    await bot.add_cog(BeastHuntDLC(bot))
    log.info("✅ DND_DLC/BeastHunt loaded")
