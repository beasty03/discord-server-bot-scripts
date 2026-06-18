import random
import logging
from pathlib import Path
import importlib.util as _ilu
from discord.ext import commands

_spec = _ilu.spec_from_file_location('paladin_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

log = logging.getLogger("launcher")

# ============================================================================
# ABILITY HANDLERS
# Each handler matches the DLC handler signature:
#   async def handler(run, action_or_bonus, uid, name, stats, enemies,
#                     target_idx, round_lines, run_id, gid, rnd, enemy)
# ============================================================================


async def _handle_bless(run, bonus, uid, name, stats, enemies, target_idx,
                        round_lines, run_id, gid, rnd, enemy):
    """Bless (bonus action): all alive allies get +1d4 on their next attack roll this round.

    Implemented by adding every alive uid to run["help_uids"] — the engine
    already reads this set and applies a +1d4 bonus when resolving attack rolls.
    """
    alive = {
        u for u, _ in run["participants"]
        if run["player_hp"].get(u, 0) > 0 and u not in run.get("fled", set())
    }
    run.setdefault("help_uids", set()).update(alive)
    run["log"].append({"type": "feature", "uid": uid, "name": name,
                       "feature": "bless", "round": rnd})
    n = len(alive)
    round_lines.append(
        f"🙏 **{name}** casts **Bless** — "
        f"{n} {'ally' if n == 1 else 'allies'} gain +1d4 to attacks this round!")


async def _handle_shield_of_faith(run, bonus, uid, name, stats, enemies, target_idx,
                                   round_lines, run_id, gid, rnd, enemy):
    """Shield of Faith (bonus action): +5 AC until the next hit this combat.

    Uses run["shield_self_uids"] — the engine already grants +5 AC to any uid
    in that set when resolving incoming enemy attacks, then clears the uid.
    """
    run.setdefault("shield_self_uids", set()).add(uid)
    run["log"].append({"type": "feature", "uid": uid, "name": name,
                       "feature": "shield_of_faith", "round": rnd})
    round_lines.append(
        f"🛡️ **{name}** casts **Shield of Faith** — +5 AC until the next hit!")


async def _handle_holy_light(run, action, uid, name, stats, enemies, target_idx,
                              round_lines, run_id, gid, rnd, enemy):
    """Holy Light (main action): 2d8 + CHA mod radiant damage, auto-hit."""
    if not stats:
        return
    cha_mod = stats["mods"]["charisma"]
    dmg     = random.randint(1, 8) + random.randint(1, 8) + max(0, cha_mod)
    enemies[target_idx]["hp"] = max(0, enemies[target_idx]["hp"] - dmg)

    cha_txt = f"+{cha_mod}" if cha_mod > 0 else (str(cha_mod) if cha_mod < 0 else "")
    run["log"].append({"type": "feature", "uid": uid, "name": name,
                       "feature": "holy_light", "dmg": dmg, "round": rnd})
    round_lines.append(
        f"☀️ **{name}** Holy Light → **{dmg} radiant dmg** *(2d8{cha_txt}, auto-hit)*")


# ============================================================================
# COG & SETUP
# ============================================================================

class PaladinDLC(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    dm   = bot.get_cog("DungeonMasterCog")
    char = bot.get_cog("CharacterCog")
    shop = bot.get_cog("ShopCog")

    if dm:
        # Class picker + HP/armor/start-items
        dm.register_class(var.CLASS)

        # Display: /class_upgrade feature list and level-up embeds
        dm.register_class_features("paladin", var.CLASS_FEATURES)

        # Display: /ability combat menu
        dm.register_combat_features("paladin", var.COMBAT_FEATURES)

        # Display: subclass /ability menu entries after Lv 3 oath choice
        for subclass_id, feats in var.SUBCLASS_COMBAT_FEATURES.items():
            dm.register_subclass_combat_features(subclass_id, feats)

        # Display: level-up choice prompts (fighting style at Lv 2, oath at Lv 3)
        for key, choice in var.LEVEL_UP_CHOICES.items():
            dm.register_level_up_choice(key, choice)

        # New spell handlers — divine_smite, lay_on_hands, sacred_weapon,
        # natures_wrath, vow_of_enmity are already in the base engine's elif chain.
        dm.register_ability_handler("bless",           _handle_bless)
        dm.register_ability_handler("shield_of_faith", _handle_shield_of_faith)
        dm.register_ability_handler("holy_light",      _handle_holy_light)

    else:
        log.warning("Paladin DLC: DungeonMasterCog not loaded — class not registered.")

    if char:
        # Weapon stat entries (needed for combat damage resolution and /equip)
        for weapon in var.WEAPONS:
            char.register_item(weapon)
        # Holy symbol — misc slot, needed as start item and sold in shop
        char.register_item({"id": "holy_symbol", "name": "Holy Symbol",
                             "emoji": "✝️", "slot": "misc"})
    else:
        log.warning("Paladin DLC: CharacterCog not loaded — items not registered.")

    if shop:
        # Shop listings (price, tier, description — appear in /shop pool)
        for item in var.SHOP_ITEMS:
            shop.register_item(item)
    else:
        log.warning("Paladin DLC: ShopCog not loaded — shop items not registered.")

    await bot.add_cog(PaladinDLC(bot))
    log.info("✅ DND_DLC/class_paladin loaded")
