import logging
from pathlib import Path

import discord
import importlib.util as _ilu
from discord import app_commands
from discord.ext import commands

_spec = _ilu.spec_from_file_location('recipes_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

_cspec = _ilu.spec_from_file_location(
    'recipes_char_vars', Path(__file__).parent.parent / 'character' / 'variables.py')
char_var = _ilu.module_from_spec(_cspec)
_cspec.loader.exec_module(char_var)

from forge_db import ForgeDB

log = logging.getLogger("launcher")

# ============================================================================
# HELPERS
# ============================================================================

def _get_inv(db, uid: str, gid: str) -> dict[str, int]:
    rows = db.execute(
        "SELECT item_id, qty FROM dnd_inventory WHERE user_id=? AND guild_id=? AND qty>0",
        (uid, gid))
    return {r[0]: r[1] for r in rows}

def _item(item_id: str) -> dict | None:
    return next((i for i in char_var.ITEMS if i["id"] == item_id), None)

def _ing_label(inputs: list[tuple[str, int]]) -> str:
    parts = []
    for iid, qty in inputs:
        d = _item(iid)
        emoji = d.get("emoji", "📦") if d else "📦"
        parts.append(f"{emoji} ×{qty}")
    return "  ·  ".join(parts)

# ============================================================================
# VIEWS
# ============================================================================

class CraftConfirmView(discord.ui.View):
    """Step 2 of crafting: show ingredient status and confirm."""

    def __init__(self, cog: "RecipesCog", uid: str, gid: str,
                 recipe: dict, inv: dict[str, int]):
        super().__init__(timeout=30)
        self._cog    = cog
        self._uid    = uid
        self._gid    = gid
        self._recipe = recipe
        can_craft    = all(inv.get(iid, 0) >= qty for iid, qty in recipe["inputs"])

        craft_btn = discord.ui.Button(
            label="🔨 Craft",
            style=discord.ButtonStyle.success if can_craft else discord.ButtonStyle.secondary,
            disabled=not can_craft,
        )
        craft_btn.callback = self._do_craft
        self.add_item(craft_btn)

        back_btn = discord.ui.Button(label="← Back", style=discord.ButtonStyle.secondary)
        back_btn.callback = self._go_back
        self.add_item(back_btn)

    async def _do_craft(self, interaction: discord.Interaction):
        uid, gid, r = self._uid, self._gid, self._recipe
        inv = _get_inv(self._cog.db, uid, gid)
        if not all(inv.get(iid, 0) >= qty for iid, qty in r["inputs"]):
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description="You no longer have all the required materials.",
                    color=var.COLOR_ERROR),
                view=None)
            return
        for iid, qty in r["inputs"]:
            self._cog.db.execute(
                "UPDATE dnd_inventory SET qty=qty-? WHERE user_id=? AND guild_id=? AND item_id=?",
                (qty, uid, gid, iid))
            self._cog.db.execute(
                "DELETE FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id=? AND qty<=0",
                (uid, gid, iid))
        out_id, out_qty = r["output"]
        self._cog.db.execute(
            """INSERT INTO dnd_inventory (user_id, guild_id, item_id, qty, equipped)
               VALUES (?,?,?,?,0)
               ON CONFLICT(user_id,guild_id,item_id) DO UPDATE SET qty=qty+?""",
            (uid, gid, out_id, out_qty, out_qty))
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🔨 Crafted!",
                description=(
                    f"You crafted **{r['emoji']} {r['name']} ×{out_qty}**!\n\n"
                    f"*{r['description']}*"
                ),
                color=var.COLOR_WIN),
            view=None)
        self.stop()

    async def _go_back(self, interaction: discord.Interaction):
        known = self._cog._get_known_recipes(self._uid, self._gid)
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🔨 Craft an Item",
                description="Choose a recipe to craft:",
                color=var.COLOR_RECIPES),
            view=CraftSelectView(self._cog, self._uid, self._gid, known))


class CraftSelectView(discord.ui.View):
    """Step 1 of crafting: pick a recipe from the dropdown."""

    def __init__(self, cog: "RecipesCog", uid: str, gid: str, known_recipes: list[dict]):
        super().__init__(timeout=60)
        self._cog = cog
        self._uid = uid
        self._gid = gid
        self._all = var.RECIPES + cog._extra_recipes

        options = [
            discord.SelectOption(
                label=f"{r['emoji']} {r['name']}",
                value=r["id"],
                description=_ing_label(r["inputs"])[:100],
            )
            for r in known_recipes
        ]
        sel = discord.ui.Select(placeholder="Choose a recipe…", options=options[:25])
        sel.callback = self._on_pick
        self.add_item(sel)

    async def _on_pick(self, interaction: discord.Interaction):
        recipe_id = interaction.data["values"][0]
        recipe = next(r for r in self._all if r["id"] == recipe_id)
        inv    = _get_inv(self._cog.db, self._uid, self._gid)

        lines = []
        for iid, qty in recipe["inputs"]:
            d      = _item(iid)
            emoji  = d.get("emoji", "📦") if d else "📦"
            name   = d["name"] if d else iid
            have   = inv.get(iid, 0)
            status = "✅" if have >= qty else "❌"
            lines.append(f"{status} {emoji} **{name}** ×{qty} — you have: {have}")

        out_id, out_qty = recipe["output"]
        out_d    = _item(out_id)
        out_name = out_d["name"] if out_d else out_id

        embed = discord.Embed(
            title=f"🔨 Craft {recipe['emoji']} {recipe['name']}",
            description="\n".join(lines) + f"\n\n→ **{recipe['emoji']} {out_name} ×{out_qty}**",
            color=var.COLOR_RECIPES,
        )
        await interaction.response.edit_message(
            embed=embed,
            view=CraftConfirmView(self._cog, self._uid, self._gid, recipe, inv))


class LearnSelectView(discord.ui.View):
    """Pick which recipe scroll in your backpack to consume."""

    def __init__(self, cog: "RecipesCog", uid: str, gid: str,
                 scrolls: list[tuple[str, int]]):
        super().__init__(timeout=60)
        self._cog  = cog
        self._uid  = uid
        self._gid  = gid
        all_recipes = var.RECIPES + cog._extra_recipes

        options = []
        for iid, qty in scrolls:
            d = _item(iid)
            if not d:
                continue
            recipe = next((r for r in all_recipes if r.get("unlock") == iid), None)
            options.append(discord.SelectOption(
                label=f"{d.get('emoji','📜')} {d['name']} ×{qty}",
                value=iid,
                description=f"Unlocks: {recipe['name']}" if recipe else "Unknown recipe",
            ))

        sel = discord.ui.Select(placeholder="Which scroll to use?", options=options[:25])
        sel.callback = self._on_scroll
        self.add_item(sel)

    async def _on_scroll(self, interaction: discord.Interaction):
        scroll_id   = interaction.data["values"][0]
        uid, gid    = self._uid, self._gid
        all_recipes = var.RECIPES + self._cog._extra_recipes

        recipe = next((r for r in all_recipes if r.get("unlock") == scroll_id), None)
        if not recipe:
            await interaction.response.edit_message(
                embed=discord.Embed(description="No recipe found for that scroll.", color=var.COLOR_ERROR),
                view=None)
            return

        if self._cog._is_unlocked(uid, gid, recipe["id"]):
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description=f"You already know how to craft **{recipe['name']}**!",
                    color=var.COLOR_INFO),
                view=None)
            return

        rows = self._cog.db.execute(
            "SELECT qty FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id=?",
            (uid, gid, scroll_id))
        if not rows or rows[0][0] <= 0:
            await interaction.response.edit_message(
                embed=discord.Embed(description="You no longer have that scroll.", color=var.COLOR_ERROR),
                view=None)
            return

        self._cog.db.execute(
            "UPDATE dnd_inventory SET qty=qty-1 WHERE user_id=? AND guild_id=? AND item_id=?",
            (uid, gid, scroll_id))
        self._cog.db.execute(
            "DELETE FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id=? AND qty<=0",
            (uid, gid, scroll_id))
        self._cog.db.execute(
            "INSERT OR IGNORE INTO dnd_recipes_unlocked (user_id, guild_id, recipe_id) VALUES (?,?,?)",
            (uid, gid, recipe["id"]))

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="📖 Recipe Learned!",
                description=(
                    f"You now know how to craft **{recipe['emoji']} {recipe['name']}**!\n\n"
                    f"*{recipe['description']}*\n\n"
                    "Use `/craft` to make it."
                ),
                color=var.COLOR_WIN),
            view=None)
        self.stop()

# ============================================================================
# COG
# ============================================================================

class RecipesCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot            = bot
        self.db             = ForgeDB.get()
        self._extra_recipes: list[dict] = []

    async def cog_load(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS dnd_recipes_unlocked (
                user_id   TEXT NOT NULL,
                guild_id  TEXT NOT NULL,
                recipe_id TEXT NOT NULL,
                PRIMARY KEY (user_id, guild_id, recipe_id)
            )
        """)

    # ── DLC registration ───────────────────────────────────────────────────────

    def register_recipe(self, data: dict):
        if not any(r["id"] == data["id"] for r in self._extra_recipes):
            self._extra_recipes.append(data)
            log.info(f"Recipes: registered DLC recipe '{data['id']}'")

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _is_unlocked(self, uid: str, gid: str, recipe_id: str) -> bool:
        return bool(self.db.execute(
            "SELECT 1 FROM dnd_recipes_unlocked WHERE user_id=? AND guild_id=? AND recipe_id=?",
            (uid, gid, recipe_id)))

    def unlock_recipe(self, uid: str, gid: str, recipe_id: str) -> bool:
        """External call (e.g. from /backpack_use on a scroll). Returns True if newly unlocked."""
        all_recipes = var.RECIPES + self._extra_recipes
        if not any(r["id"] == recipe_id for r in all_recipes):
            return False
        if self._is_unlocked(uid, gid, recipe_id):
            return False
        self.db.execute(
            "INSERT OR IGNORE INTO dnd_recipes_unlocked (user_id, guild_id, recipe_id) VALUES (?,?,?)",
            (uid, gid, recipe_id))
        return True

    def _get_known_recipes(self, uid: str, gid: str) -> list[dict]:
        all_recipes = var.RECIPES + self._extra_recipes
        return [
            r for r in all_recipes
            if r.get("unlock") is None or self._is_unlocked(uid, gid, r["id"])
        ]

    # ── /recipes ───────────────────────────────────────────────────────────────

    @app_commands.command(name="recipes", description="Browse all crafting recipes and their unlock status.")
    async def recipes(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)
        inv = _get_inv(self.db, uid, gid)
        all_recipes = var.RECIPES + self._extra_recipes

        embed = discord.Embed(title="📖 Recipes", color=var.COLOR_RECIPES)

        tier_order = ["common", "uncommon", "rare", "epic"]
        for tier_id in tier_order:
            tier_emoji = var.TIER_EMOJI.get(tier_id, "⚪")
            tier_label = tier_id.title()
            lines = []

            for r in all_recipes:
                if r.get("tier") != tier_id:
                    continue
                unlocked = r.get("unlock") is None or self._is_unlocked(uid, gid, r["id"])
                ing      = _ing_label(r["inputs"])

                if unlocked:
                    can     = all(inv.get(iid, 0) >= qty for iid, qty in r["inputs"])
                    mat_ico = "✅" if can else "⚠️"
                    lines.append(
                        f"{mat_ico} {r['emoji']} **{r['name']}**\n"
                        f"  *{ing}*\n"
                        f"  {r['description']}"
                    )
                else:
                    scroll_d    = _item(r.get("unlock", ""))
                    scroll_name = scroll_d["name"] if scroll_d else r.get("unlock", "?")
                    lines.append(
                        f"🔒 {r['emoji']} **{r['name']}**\n"
                        f"  *{ing}*\n"
                        f"  Requires: 📜 {scroll_name}"
                    )

            if lines:
                embed.add_field(
                    name=f"{tier_emoji} {tier_label}",
                    value="\n\n".join(lines),
                    inline=False,
                )

        if not embed.fields:
            embed.description = "No recipes available yet."
        else:
            embed.set_footer(text="✅ known & materials ready  ⚠️ known but missing materials  🔒 locked")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /craft ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="craft", description="Craft an item from materials in your backpack.")
    async def craft(self, interaction: discord.Interaction):
        uid   = str(interaction.user.id)
        gid   = str(interaction.guild_id)
        known = self._get_known_recipes(uid, gid)
        if not known:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "You don't know any crafting recipes yet.\n"
                        "Find 📜 recipe scrolls in campaigns or buy them from the shop, "
                        "then use `/learn_recipe` to unlock them."
                    ),
                    color=var.COLOR_INFO),
                ephemeral=True)
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="🔨 Craft an Item",
                description="Choose a recipe to craft:",
                color=var.COLOR_RECIPES),
            view=CraftSelectView(self, uid, gid, known),
            ephemeral=True)

    # ── /learn_recipe ──────────────────────────────────────────────────────────

    @app_commands.command(name="learn_recipe", description="Use a recipe scroll from your backpack to unlock a new recipe.")
    async def learn_recipe(self, interaction: discord.Interaction):
        uid         = str(interaction.user.id)
        gid         = str(interaction.guild_id)
        all_recipes = var.RECIPES + self._extra_recipes

        rows   = self.db.execute(
            "SELECT item_id, qty FROM dnd_inventory WHERE user_id=? AND guild_id=? AND qty>0",
            (uid, gid))
        scrolls: list[tuple[str, int]] = []
        for iid, qty in rows:
            d = _item(iid)
            if not d or d.get("slot") != "recipe":
                continue
            recipe = next((r for r in all_recipes if r.get("unlock") == iid), None)
            if recipe and not self._is_unlocked(uid, gid, recipe["id"]):
                scrolls.append((iid, qty))

        if not scrolls:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "You have no recipe scrolls, or you already know all "
                        "the recipes they unlock.\n\n"
                        "Find scrolls during campaigns or buy them from the 🏪 shop."
                    ),
                    color=var.COLOR_INFO),
                ephemeral=True)
            return

        await interaction.response.send_message(
            embed=discord.Embed(
                title="📖 Learn a Recipe",
                description="Choose a scroll to use:",
                color=var.COLOR_RECIPES),
            view=LearnSelectView(self, uid, gid, scrolls),
            ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(RecipesCog(bot))
    log.info("✅ DND/Recipes cog loaded")
