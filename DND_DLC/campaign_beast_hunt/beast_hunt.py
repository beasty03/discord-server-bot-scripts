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
    _dlc_shop_items   = [var.SHOP_ITEM, var.RECIPE_SHOP_ITEM]
    _dlc_shop_bundles = [var.SHOP_BUNDLE]
    _dlc_recipes      = [var.RECIPE]


async def setup(bot: commands.Bot):
    dm = bot.get_cog("DungeonMasterCog")
    if dm:
        dm.register_campaign(var.CAMPAIGN)
    else:
        log.warning("BeastHunt DLC: DungeonMasterCog not loaded — campaign not registered.")

    char = bot.get_cog("CharacterCog")
    if char:
        for item in var.CHAR_ITEMS:
            char.register_item(item)
        for shop_item in [var.SHOP_ITEM, var.RECIPE_SHOP_ITEM]:
            char.register_shop_item(shop_item)
    else:
        log.warning("BeastHunt DLC: CharacterCog not loaded — items not registered.")

    recipes_cog = bot.get_cog("RecipesCog")
    if recipes_cog:
        recipes_cog.register_recipe(var.RECIPE)
    else:
        log.warning("BeastHunt DLC: RecipesCog not loaded — recipe not registered.")

    shop = bot.get_cog("ShopCog")
    if shop:
        shop.register_item(var.SHOP_ITEM)
        shop.register_bundle(var.SHOP_BUNDLE)
    else:
        log.warning("BeastHunt DLC: ShopCog not loaded — shop items not registered.")

    await bot.add_cog(BeastHuntDLC(bot))
    log.info("✅ DND_DLC/BeastHunt loaded")
