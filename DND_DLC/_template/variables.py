"""
DLC TEMPLATE — copy this folder (remove the _ prefix) to start a new DLC.

The ONLY required export is register(api).
Import Effect types at the top. Define handlers as plain functions.
Register content and subscribe handlers inside register().

Available api methods:
  api.add_class(data)            api.add_race(data)
  api.add_item(data)             api.add_spell(data)
  api.add_campaign(data)         api.add_recipe(data)
  api.add_shop_item(data)
  api.on(event, fn, priority=0)
  api.define_status(id, label, icon="")
  api.define_damage_type(id, label, icon="")

Engine events:
  on_combat_start   on_turn_start     on_before_attack
  on_damage_roll    on_hit            on_take_damage
  on_heal           on_skill_check    on_ability_use
  on_item_use       on_item_equip     on_kill
  on_combat_end     on_level_up

Handler signature:
  def my_handler(ctx) -> list[Effect]:
      ...
  api.on("event_name", my_handler)

Item on_* hooks (auto-wired by api.add_item — only fires when item is equipped):
  "on_hit"          "on_damage_roll"  "on_take_damage"
  "on_use"          "on_equip"
"""
from DND.DungeonMaster.effects import BonusAttack, Flag, Heal, Message, Modify, Status


def register(api):
    # ── Vocabulary (optional) ─────────────────────────────────────────────────
    # api.define_damage_type("fire",    label="Fire",    icon="🔥")
    # api.define_status("poisoned",     label="Poisoned", icon="☠️")

    # ── Class ─────────────────────────────────────────────────────────────────
    # def _my_ability(ctx):
    #     if ctx.turn.ability_id != "my_ability":
    #         return []
    #     if ctx.player.char_class != "my_class":
    #         return []
    #     healed = ctx.roll("1d8") + ctx.player.stats.get("str_mod", 0)
    #     return [Heal(healed), Message(f"My Ability heals {healed} HP!")]
    #
    # def _my_passive(ctx):
    #     if ctx.player.char_class != "my_class":
    #         return []
    #     if ctx.player.level >= 5:
    #         return [BonusAttack(), Message("Passive: extra attack!")]
    #     return []
    #
    # api.add_class({
    #     "id":            "my_class",
    #     "name":          "My Class",
    #     "emoji":         "⚔️",
    #     "hit_die":       10,
    #     "primary_stat":  "strength",
    #     "weapon_profs":  ["simple", "martial"],
    #     "armor_profs":   ["light", "medium", "heavy", "shields"],
    #     "saving_throws": ["strength", "constitution"],
    #     "start_items":   ["shortsword"],
    #     "features": [
    #         {"level": 1, "name": "My Feature", "desc": "Does something cool."},
    #     ],
    #     "abilities": [
    #         {
    #             "id":        "my_ability",
    #             "name":      "My Ability",
    #             "label":     "✨ My Ability",
    #             "action":    "bonus",       # "bonus" | "action"
    #             "once_per":  "combat",      # "combat" | "rest" | None
    #             "level_req": 1,
    #             "handler":   _my_ability,
    #             "desc":      "Heals 1d8 + STR mod HP.",
    #         }
    #     ],
    #     "subclasses":    {},
    #     "level_choices": {},
    # })
    # api.on("on_turn_start", _my_passive)

    # ── Race ──────────────────────────────────────────────────────────────────
    # def _my_trait(ctx):
    #     if ctx.player.race != "my_race":
    #         return []
    #     if ctx.turn.check_type == "perception":
    #         return [Flag("advantage", True)]
    #     return []
    #
    # api.add_race({
    #     "id":           "my_race",
    #     "name":         "My Race",
    #     "emoji":        "🧝",
    #     "stat_bonuses": {"dexterity": 2, "intelligence": 1},
    #     "traits": [
    #         {"name": "Keen Senses", "desc": "Advantage on perception checks."},
    #     ],
    # })
    # api.on("on_skill_check", _my_trait)

    # ── Item (with on_hit handler) ────────────────────────────────────────────
    # def _my_sword_hit(ctx):
    #     bonus = ctx.roll("1d6")
    #     return [
    #         Modify("damage", add=bonus, damage_type="fire"),
    #         Message(f"🔥 Burns for {bonus} fire damage!"),
    #     ]
    #
    # api.add_item({
    #     "id":          "my_sword",
    #     "name":        "My Sword",
    #     "emoji":       "⚔️",
    #     "slot":        "weapon",        # weapon|armor|offhand|consumable|misc|recipe|material
    #     "weapon_type": "martial",       # simple|martial|ranged
    #     "ability":     "strength",
    #     "dmg":         "1d8",
    #     "handed":      1,
    #     "sell":        100,
    #     "description": "A sword that burns on hit.",
    #     "on_hit":      _my_sword_hit,   # auto-wired; fires only when equipped
    # })
    # api.add_shop_item({
    #     "id":          "my_sword",
    #     "name":        "My Sword",
    #     "emoji":       "⚔️",
    #     "description": "A sword that burns on hit. +1d6 fire damage.",
    #     "price":       500,
    #     "max_qty":     1,
    #     "tier":        "rare",   # common|uncommon|rare|epic|legendary
    # })

    # ── Campaign ──────────────────────────────────────────────────────────────
    # api.add_campaign({
    #     "id":              "my_campaign",
    #     "name":            "My Campaign",
    #     "emoji":           "🗺️",
    #     "min_level":       1,
    #     "min_players":     1,
    #     "max_players":     4,
    #     "difficulty":      "Medium",
    #     "intro":           "The adventure begins...",
    #     "reward_gold_min": 50,
    #     "reward_gold_max": 100,
    #     "reward_xp":       200,
    #     "encounters":      [],
    # })

    # ── Recipe ────────────────────────────────────────────────────────────────
    # api.add_recipe({
    #     "id":          "my_recipe",
    #     "name":        "My Crafted Item",
    #     "emoji":       "⚗️",
    #     "tier":        "rare",
    #     "unlock":      "recipe_my_crafted_item",   # scroll item id, or None = always known
    #     "inputs":      [("herb", 3), ("leather_scrap", 2)],
    #     "output":      ("my_crafted_item", 1),
    #     "description": "A hand-crafted item.",
    # })

    pass
