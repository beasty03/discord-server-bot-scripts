import logging
import random as _random
from datetime import date
from pathlib import Path

import discord
import importlib.util as _ilu
from discord import app_commands
from discord.ext import commands

_spec = _ilu.spec_from_file_location('shop_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

_cspec = _ilu.spec_from_file_location(
    'shop_char_vars', Path(__file__).parent.parent / 'character' / 'variables.py')
char_var = _ilu.module_from_spec(_cspec)
_cspec.loader.exec_module(char_var)

from forge_db import ForgeDB

log = logging.getLogger("launcher")

# ============================================================================
# HELPERS
# ============================================================================

def _item_name(item_id: str, extra_items: list = ()) -> str:
    item = next((i for i in list(char_var.ITEMS) + list(extra_items) if i["id"] == item_id), None)
    return item["name"] if item else item_id

def _tier(data: dict) -> dict:
    return var.TIERS.get(data.get("tier", "common"), var.TIERS["common"])

def _weighted_sample(pool: list[dict], rng: _random.Random, n: int) -> list[dict]:
    """Pick up to n items from pool without replacement, weighted by tier."""
    pool    = list(pool)
    weights = [_tier(item)["weight"] for item in pool]
    result  = []
    for _ in range(min(n, len(pool))):
        total = sum(weights)
        if total == 0:
            break
        r, cumulative = rng.random() * total, 0
        for i, w in enumerate(weights):
            cumulative += w
            if r <= cumulative:
                result.append(pool[i])
                pool.pop(i)
                weights.pop(i)
                break
    return result

# ============================================================================
# VIEWS
# ============================================================================

class BuyConfirmView(discord.ui.View):
    """Confirm / cancel before deducting coins and decrementing stock."""

    def __init__(self, cog: "ShopCog", uid: str, gid: str,
                 listing: dict, is_bundle: bool):
        super().__init__(timeout=30)
        self._cog       = cog
        self._uid       = uid
        self._gid       = gid
        self._listing   = listing
        self._is_bundle = is_bundle

    @discord.ui.button(label="✅ Buy", style=discord.ButtonStyle.success)
    async def buy_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        uid, gid  = self._uid, self._gid
        today     = date.today().isoformat()
        item_id   = self._listing["id"]
        price     = self._listing["price"]

        # Re-check stock (could have sold out since the shop was opened)
        stock_row = self._cog.db.execute(
            "SELECT stock FROM dnd_shop_stock WHERE date=? AND item_id=?",
            (today, item_id))
        if not stock_row or stock_row[0][0] <= 0:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description=f"**{self._listing['name']}** just sold out!",
                    color=var.COLOR_ERROR),
                view=None)
            return

        balance = self._cog.db.get_balance(uid, gid)
        if balance < price:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description=(
                        f"Not enough {var.CURRENCY_SYMBOL}! "
                        f"You have **{balance:,}** but need **{price:,}**."
                    ),
                    color=var.COLOR_ERROR),
                view=None)
            return

        if self._is_bundle:
            for b_item_id, qty in self._listing["items"]:
                max_q   = self._listing.get("max_qty_per_item", {}).get(b_item_id, 99)
                rows    = self._cog.db.execute(
                    "SELECT qty FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id=?",
                    (uid, gid, b_item_id))
                current = rows[0][0] if rows else 0
                if current + qty > max_q:
                    await interaction.response.edit_message(
                        embed=discord.Embed(
                            description=f"You already have too many **{_item_name(b_item_id, self._cog._char_extra_items())}**.",
                            color=var.COLOR_ERROR),
                        view=None)
                    return
            for b_item_id, qty in self._listing["items"]:
                self._cog.db.execute(
                    """INSERT INTO dnd_inventory (user_id, guild_id, item_id, qty, equipped)
                       VALUES (?, ?, ?, ?, 0)
                       ON CONFLICT(user_id, guild_id, item_id) DO UPDATE SET qty=qty+?""",
                    (uid, gid, b_item_id, qty, qty))
        else:
            max_q   = self._listing.get("max_qty", 99)
            rows    = self._cog.db.execute(
                "SELECT qty FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id=?",
                (uid, gid, item_id))
            current = rows[0][0] if rows else 0
            if current >= max_q:
                await interaction.response.edit_message(
                    embed=discord.Embed(
                        description=(
                            f"You already have the max amount of "
                            f"**{self._listing['name']}** ({max_q})."
                        ),
                        color=var.COLOR_ERROR),
                    view=None)
                return
            self._cog.db.execute(
                """INSERT INTO dnd_inventory (user_id, guild_id, item_id, qty, equipped)
                   VALUES (?, ?, ?, 1, 0)
                   ON CONFLICT(user_id, guild_id, item_id) DO UPDATE SET qty=qty+1""",
                (uid, gid, item_id))

        # Decrement stock and deduct coins
        self._cog.db.execute(
            "UPDATE dnd_shop_stock SET stock=stock-1 WHERE date=? AND item_id=?",
            (today, item_id))
        self._cog.db.update_balance(uid, gid, -price, "shop_purchase")

        new_bal   = self._cog.db.get_balance(uid, gid)
        remaining = self._cog.db.execute(
            "SELECT stock FROM dnd_shop_stock WHERE date=? AND item_id=?",
            (today, item_id))
        stock_left = remaining[0][0] if remaining else 0
        stock_note = f"  ·  **{stock_left}** left in stock" if stock_left > 0 else "  ·  **Sold out!**"

        await interaction.response.edit_message(
            embed=discord.Embed(
                description=(
                    f"✅ Purchased **{self._listing['name']}**{stock_note}\n"
                    f"Balance: **{new_bal:,}** {var.CURRENCY_SYMBOL}"
                ),
                color=var.COLOR_WIN),
            view=None)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.edit_message(
            embed=discord.Embed(description="Purchase cancelled.", color=var.COLOR_INFO),
            view=None)
        self.stop()


class ShopSelectView(discord.ui.View):
    """Dropdown listing only items still in stock."""

    def __init__(self, cog: "ShopCog", uid: str, gid: str,
                 listings: list[dict]):
        super().__init__(timeout=60)
        self._cog      = cog
        self._uid      = uid
        self._gid      = gid
        self._map      = {l["id"]: l for l in listings}

        options = [
            discord.SelectOption(
                label=f"{l['emoji']} {l['name']} ×{l['_stock']}",
                value=l["id"],
                description=(
                    f"{_tier(l)['emoji']} {_tier(l)['label']}  ·  "
                    f"{l['price']:,} {var.CURRENCY_NAME}  ·  {l['description'][:60]}"
                ),
            )
            for l in listings
        ]

        sel = discord.ui.Select(placeholder="Choose something to buy…", options=options[:25])
        sel.callback = self._on_select
        self.add_item(sel)

    async def _on_select(self, interaction: discord.Interaction):
        listing   = self._map[interaction.data["values"][0]]
        is_bundle = listing.get("_is_bundle", False)

        if is_bundle:
            extra      = self._cog._char_extra_items()
            item_lines = "\n".join(
                f"• {_item_name(iid, extra)} ×{qty}"
                for iid, qty in listing["items"]
            )
            detail = f"{listing['description']}\n\n**Includes:**\n{item_lines}"
        else:
            detail = listing["description"]

        t = _tier(listing)
        embed = discord.Embed(
            title=f"{listing['emoji']} {listing['name']}",
            description=(
                f"{t['emoji']} **{t['label']}**  ·  {listing['_stock']} in stock\n\n"
                f"{detail}\n\n"
                f"**Price:** {listing['price']:,} {var.CURRENCY_SYMBOL}"
            ),
            color=var.COLOR_SHOP,
        )
        await interaction.response.send_message(
            embed=embed,
            view=BuyConfirmView(self._cog, self._uid, self._gid, listing, is_bundle),
            ephemeral=True,
        )

# ============================================================================
# COG
# ============================================================================

class ShopCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot  = bot
        self.db   = ForgeDB.get()
        self._extra_items:   list[dict] = []
        self._extra_bundles: list[dict] = []

    def _char_extra_items(self) -> list[dict]:
        char_cog = self.bot.cogs.get("CharacterCog")
        return char_cog._extra_items if char_cog else []

    async def cog_load(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS dnd_shop_stock (
                date     TEXT    NOT NULL,
                item_id  TEXT    NOT NULL,
                stock    INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (date, item_id)
            )
        """)

    # ── DLC registration ───────────────────────────────────────────────────────

    def register_item(self, data: dict):
        if not any(i["id"] == data["id"] for i in self._extra_items):
            self._extra_items.append(data)
            log.info(f"Shop: registered DLC item '{data['id']}'")

    def register_bundle(self, data: dict):
        if not any(b["id"] == data["id"] for b in self._extra_bundles):
            self._extra_bundles.append(data)
            log.info(f"Shop: registered DLC bundle '{data['id']}'")

    # ── Daily stock ────────────────────────────────────────────────────────────

    def _generate_daily_stock(self, today: str) -> dict[str, int]:
        """Pick today's items + bundles and write stock to DB. Returns {item_id: stock}."""
        rng = _random.Random(date.fromisoformat(today).toordinal())

        # Clean up stock older than 7 days
        cutoff = date.fromordinal(date.today().toordinal() - 7).isoformat()
        self.db.execute("DELETE FROM dnd_shop_stock WHERE date < ?", (cutoff,))

        all_items   = var.SHOP_ITEMS   + self._extra_items
        all_bundles = var.SHOP_BUNDLES + self._extra_bundles

        selected_items   = _weighted_sample(all_items,   rng, var.MAX_SHOP_ITEMS)
        selected_bundles = _weighted_sample(all_bundles, rng, var.MAX_SHOP_BUNDLES)

        result: dict[str, int] = {}
        for listing in selected_items + selected_bundles:
            t     = _tier(listing)
            stock = rng.randint(t["stock_min"], t["stock_max"])
            self.db.execute(
                "INSERT OR IGNORE INTO dnd_shop_stock (date, item_id, stock) VALUES (?, ?, ?)",
                (today, listing["id"], stock))
            result[listing["id"]] = stock

        return result

    def _get_today(self) -> tuple[dict[str, int], str]:
        """Return ({item_id: stock}, today_str), generating stock if needed."""
        today = date.today().isoformat()
        rows  = self.db.execute(
            "SELECT item_id, stock FROM dnd_shop_stock WHERE date=?", (today,))
        if rows:
            return {r[0]: r[1] for r in rows}, today
        return self._generate_daily_stock(today), today

    # ── /shop ──────────────────────────────────────────────────────────────────

    @app_commands.command(name="shop", description="Browse today's item shop.")
    async def shop(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        stock_map, today = self._get_today()
        all_items   = {i["id"]: i for i in var.SHOP_ITEMS   + self._extra_items}
        all_bundles = {b["id"]: b for b in var.SHOP_BUNDLES + self._extra_bundles}

        balance = self.db.get_balance(uid, gid)

        embed = discord.Embed(
            title="🏪 Item Shop",
            description=f"Your balance: **{balance:,}** {var.CURRENCY_SYMBOL}  ·  Restocks at midnight",
            color=var.COLOR_SHOP,
        )

        available: list[dict] = []  # for the dropdown
        item_lines:   list[str] = []
        bundle_lines: list[str] = []

        for item_id, stock in stock_map.items():
            t = None
            if item_id in all_items:
                listing   = dict(all_items[item_id])
                is_bundle = False
            elif item_id in all_bundles:
                listing   = dict(all_bundles[item_id])
                is_bundle = True
            else:
                continue

            t       = _tier(listing)
            listing["_stock"]     = stock
            listing["_is_bundle"] = is_bundle

            tier_badge = f"{t['emoji']} {t['label']}"
            if stock > 0:
                line = (
                    f"{listing['emoji']} **{listing['name']}** {tier_badge}  ·  "
                    f"×{stock} left  ·  {listing['price']:,} {var.CURRENCY_SYMBOL}\n"
                    f"  *{listing['description']}*"
                )
                available.append(listing)
            else:
                line = (
                    f"~~{listing['emoji']} **{listing['name']}**~~ {tier_badge}  ·  "
                    f"**SOLD OUT**"
                )

            if is_bundle:
                bundle_lines.append(line)
            else:
                item_lines.append(line)

        if item_lines:
            embed.add_field(name="🛒 Items", value="\n".join(item_lines), inline=False)
        if bundle_lines:
            embed.add_field(name="📦 Bundles", value="\n".join(bundle_lines), inline=False)

        if not item_lines and not bundle_lines:
            embed.description = "The shop is empty today. Check back tomorrow!"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed.set_footer(text=var.SERVER_NAME)

        view = ShopSelectView(self, uid, gid, available) if available else None
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ── /shop_sell ─────────────────────────────────────────────────────────────

    @app_commands.command(name="shop_sell", description="Sell items from your backpack.")
    @app_commands.describe(item="Item to sell", qty="How many to sell (default 1)")
    async def shop_sell(self, interaction: discord.Interaction, item: str, qty: int = 1):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if qty < 1:
            await interaction.response.send_message(
                embed=discord.Embed(description="Quantity must be at least 1.", color=var.COLOR_ERROR),
                ephemeral=True)
            return

        rows    = self.db.execute(
            "SELECT qty FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id=?",
            (uid, gid, item))
        have    = rows[0][0] if rows else 0
        if have < qty:
            msg = f"You only have {have}." if have else "You don't have that item."
            await interaction.response.send_message(
                embed=discord.Embed(description=msg, color=var.COLOR_ERROR), ephemeral=True)
            return

        all_items = list(char_var.ITEMS) + self._char_extra_items()
        item_data = next((i for i in all_items if i["id"] == item), None)
        if not item_data or "sell" not in item_data:
            await interaction.response.send_message(
                embed=discord.Embed(description="That item can't be sold.", color=var.COLOR_ERROR),
                ephemeral=True)
            return
        if item_data.get("slot") == "companion":
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="You can't sell your companion — they're loyal to you, not a commodity!",
                    color=var.COLOR_ERROR),
                ephemeral=True)
            return

        total = item_data["sell"] * qty
        self.db.execute(
            "UPDATE dnd_inventory SET qty=qty-? WHERE user_id=? AND guild_id=? AND item_id=?",
            (qty, uid, gid, item))
        self.db.execute(
            "DELETE FROM dnd_inventory WHERE user_id=? AND guild_id=? AND item_id=? AND qty<=0",
            (uid, gid, item))
        self.db.update_balance(uid, gid, total, "shop_sell")
        new_bal = self.db.get_balance(uid, gid)

        emoji   = item_data.get("emoji", "🎒")
        qty_txt = f"×{qty} " if qty > 1 else ""
        await interaction.response.send_message(
            embed=discord.Embed(
                description=(
                    f"{emoji} Sold {qty_txt}**{item_data['name']}** "
                    f"→ **+{total:,}** {var.CURRENCY_SYMBOL}\n"
                    f"Balance: **{new_bal:,}** {var.CURRENCY_SYMBOL}"
                ),
                color=var.COLOR_WIN),
            ephemeral=True)

    @shop_sell.autocomplete("item")
    async def _shop_sell_ac(self, interaction: discord.Interaction, current: str):
        uid, gid  = str(interaction.user.id), str(interaction.guild_id)
        rows      = self.db.execute(
            "SELECT item_id, qty FROM dnd_inventory WHERE user_id=? AND guild_id=? AND qty>0",
            (uid, gid)) or []
        all_items = list(char_var.ITEMS) + self._char_extra_items()
        choices   = []
        for iid, qty in rows:
            d = next((i for i in all_items if i["id"] == iid and "sell" in i), None)
            if not d:
                continue
            label = f"{d.get('emoji','')}{d['name']} ×{qty} — {d['sell']} {var.CURRENCY_NAME} each".strip()
            if current.lower() in label.lower():
                choices.append(app_commands.Choice(name=label[:100], value=iid))
        return choices[:25]

    @staticmethod
    def _err(msg: str) -> discord.Embed:
        return discord.Embed(description=msg, color=var.COLOR_ERROR)


async def setup(bot: commands.Bot):
    await bot.add_cog(ShopCog(bot))
    log.info("✅ DND/Shop cog loaded")
