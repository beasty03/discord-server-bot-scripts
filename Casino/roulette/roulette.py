import discord
from discord.ext import commands
from discord import app_commands
import random
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('roulette_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

# ============================================================================
# WHEEL LOGIC
# ============================================================================

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

def spin_wheel() -> int:
    return random.randint(0, 36)

def get_color(n: int) -> str:
    if n == 0:
        return "green"
    return "red" if n in RED_NUMBERS else "black"

def color_emoji(n: int) -> str:
    return {"green": "🟢", "red": "🔴", "black": "⚫"}[get_color(n)]

def check_win(result: int, bet_type: str, bet_number: int | None = None) -> tuple[bool, float]:
    c = get_color(result)
    match bet_type:
        case "red":    return c == "red",                              2.0
        case "black":  return c == "black",                            2.0
        case "odd":    return result != 0 and result % 2 == 1,         2.0
        case "even":   return result != 0 and result % 2 == 0,         2.0
        case "low":    return 1 <= result <= 18,                       2.0
        case "high":   return 19 <= result <= 36,                      2.0
        case "dozen1": return 1 <= result <= 12,                       3.0
        case "dozen2": return 13 <= result <= 24,                      3.0
        case "dozen3": return 25 <= result <= 36,                      3.0
        case "number": return result == bet_number,                    36.0
    return False, 0.0

def describe_result(n: int) -> str:
    if n == 0:
        return "0 — 🟢 Green"
    parts = [
        f"{n}",
        color_emoji(n) + (" Red" if get_color(n) == "red" else " Black"),
        "Odd" if n % 2 == 1 else "Even",
        "Low (1–18)" if n <= 18 else "High (19–36)",
        f"{['1st', '2nd', '3rd'][(n - 1) // 12]} Dozen" if 1 <= n <= 36 else "",
    ]
    return " · ".join(p for p in parts if p)

def _record_stats(db, uid: str, gid: str, won: int = 0, lost: int = 0):
    db.execute(
        """INSERT INTO casino_stats (user_id, guild_id, games_played, games_won, games_lost, total_won, total_lost)
           VALUES (?, ?, 1, ?, ?, ?, ?)
           ON CONFLICT(user_id, guild_id) DO UPDATE SET
               games_played = games_played + 1,
               games_won    = games_won    + excluded.games_won,
               games_lost   = games_lost   + excluded.games_lost,
               total_won    = total_won    + excluded.total_won,
               total_lost   = total_lost   + excluded.total_lost""",
        (uid, gid, 1 if won > 0 else 0, 1 if lost > 0 else 0, won, lost),
    )

def bet_label(bet_type: str, bet_number: int | None) -> str:
    labels = {
        "red": "🔴 Red", "black": "⚫ Black",
        "odd": "Odd", "even": "Even",
        "low": "Low (1–18)", "high": "High (19–36)",
        "dozen1": "1st Dozen (1–12)", "dozen2": "2nd Dozen (13–24)", "dozen3": "3rd Dozen (25–36)",
        "number": f"Straight Up — {bet_number}",
    }
    return labels.get(bet_type, bet_type)

# ============================================================================
# MODAL — straight-up number bet
# ============================================================================

class NumberModal(discord.ui.Modal, title="Straight Up Bet"):
    number_input = discord.ui.TextInput(
        label="Pick a number (0–36)",
        placeholder="e.g. 17",
        min_length=1,
        max_length=2,
    )

    def __init__(self, view: "RouletteView"):
        super().__init__()
        self._view = view

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.number_input.value.strip()
        if not raw.isdigit():
            await interaction.response.send_message("Please enter a whole number between 0 and 36.", ephemeral=True)
            return
        n = int(raw)
        if not 0 <= n <= 36:
            await interaction.response.send_message("Number must be between 0 and 36.", ephemeral=True)
            return
        await self._view._resolve(interaction, "number", bet_number=n, from_modal=True)

# ============================================================================
# BET-SELECTION VIEW
# ============================================================================

class RouletteView(discord.ui.View):
    def __init__(self, cog: "RouletteCog", interaction: discord.Interaction, bet: int, user_id: int):
        super().__init__(timeout=var.BUTTON_TIMEOUT)
        self.cog                  = cog
        self.db                   = cog.db
        self.original_interaction = interaction
        self.bet                  = bet
        self.user_id              = str(user_id)
        self.guild_id             = str(interaction.guild_id)
        self.resolved             = False

    async def _check_user(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return False
        return True

    async def _resolve(
        self,
        interaction: discord.Interaction,
        bet_type: str,
        bet_number: int | None = None,
        from_modal: bool = False,
    ):
        if self.resolved:
            return
        self.resolved = True
        for item in self.children:
            item.disabled = True

        result = spin_wheel()
        won, multiplier = check_win(result, bet_type, bet_number)

        dm_mult = getattr(interaction.client, 'multiplier_event_mult', None) or 1.0
        if won:
            payout = int(self.bet * multiplier)
            if dm_mult > 1.0:
                payout = self.bet + int((payout - self.bet) * dm_mult)
            self.db.update_balance(self.user_id, self.guild_id, payout, 'win')
            _record_stats(self.db, self.user_id, self.guild_id, payout - self.bet, 0)
        else:
            _record_stats(self.db, self.user_id, self.guild_id, 0, self.bet)

        new_balance = self.db.get_balance(self.user_id, self.guild_id)
        embed = self._build_result_embed(result, bet_type, bet_number, won, new_balance, dm_mult)

        if from_modal:
            await interaction.response.defer()
            await self.original_interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)
        if interaction.channel:
            pub = discord.Embed(
                description=(
                    f"🎡 **{interaction.user.display_name}** won {var.CURRENCY_SYMBOL} **{payout - self.bet:,}** playing Roulette!"
                    + (f" 💰 **{dm_mult}x** event!" if dm_mult > 1.0 else "")
                    if won else
                    f"🎡 **{interaction.user.display_name}** lost {var.CURRENCY_SYMBOL} **{self.bet:,}** playing Roulette"
                ),
                color=var.COLOR_WIN if won else var.COLOR_LOSE,
            )
            await interaction.channel.send(embed=pub)

    def _build_result_embed(
        self,
        result: int,
        bet_type: str,
        bet_number: int | None,
        won: bool,
        new_balance: int,
        dm_mult: float = 1.0,
    ) -> discord.Embed:
        emoji  = color_emoji(result)
        title  = f"🎡 {emoji} The ball landed on **{result}**!"
        payout = int(self.bet * (check_win(result, bet_type, bet_number)[1])) if won else 0
        if won and dm_mult > 1.0:
            payout = self.bet + int((payout - self.bet) * dm_mult)
        profit = payout - self.bet

        embed = discord.Embed(
            title=title,
            description=describe_result(result),
            color=var.COLOR_WIN if won else var.COLOR_LOSE,
        )
        embed.add_field(name="Your Bet", value=bet_label(bet_type, bet_number), inline=True)
        embed.add_field(name="Wagered",  value=f"{var.CURRENCY_SYMBOL} {self.bet:,}", inline=True)

        if won:
            profit_label = "Profit 💰 (boosted)" if dm_mult > 1.0 else "Profit"
            embed.add_field(name=profit_label, value=f"{var.CURRENCY_SYMBOL} +{profit:,} {var.CURRENCY_NAME}", inline=False)
        else:
            embed.add_field(name="Lost",   value=f"{var.CURRENCY_SYMBOL} -{self.bet:,} {var.CURRENCY_NAME}", inline=False)

        embed.add_field(name="New Balance", value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}", inline=False)
        embed.set_footer(text=f"Played by {self.original_interaction.user.display_name}")
        embed.timestamp = datetime.utcnow()
        return embed

    async def on_timeout(self):
        if not self.resolved:
            self.resolved = True
            self.db.update_balance(self.user_id, self.guild_id, self.bet, 'refund')
            for item in self.children:
                item.disabled = True
            embed = discord.Embed(
                title="⏰ Game Timed Out",
                description=(
                    f"You didn't pick a bet in time.\n"
                    f"Your {var.CURRENCY_SYMBOL} {self.bet:,} {var.CURRENCY_NAME} has been refunded."
                ),
                color=var.COLOR_ERROR,
            )
            embed.timestamp = datetime.utcnow()
            try:
                await self.original_interaction.edit_original_response(embed=embed, view=self)
            except Exception:
                pass

    # ── Bet buttons ───────────────────────────────────────────────────────────

    @discord.ui.button(label="🔴 Red", style=discord.ButtonStyle.danger, row=0)
    async def red(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await self._resolve(interaction, "red")

    @discord.ui.button(label="⚫ Black", style=discord.ButtonStyle.secondary, row=0)
    async def black(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await self._resolve(interaction, "black")

    @discord.ui.button(label="Odd", style=discord.ButtonStyle.primary, row=1)
    async def odd(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await self._resolve(interaction, "odd")

    @discord.ui.button(label="Even", style=discord.ButtonStyle.primary, row=1)
    async def even(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await self._resolve(interaction, "even")

    @discord.ui.button(label="Low (1–18)", style=discord.ButtonStyle.secondary, row=2)
    async def low(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await self._resolve(interaction, "low")

    @discord.ui.button(label="High (19–36)", style=discord.ButtonStyle.secondary, row=2)
    async def high(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await self._resolve(interaction, "high")

    @discord.ui.button(label="1st Dozen (1–12)", style=discord.ButtonStyle.success, row=3)
    async def dozen1(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await self._resolve(interaction, "dozen1")

    @discord.ui.button(label="2nd Dozen (13–24)", style=discord.ButtonStyle.success, row=3)
    async def dozen2(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await self._resolve(interaction, "dozen2")

    @discord.ui.button(label="3rd Dozen (25–36)", style=discord.ButtonStyle.success, row=3)
    async def dozen3(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await self._resolve(interaction, "dozen3")

    @discord.ui.button(label="🎯 Straight Up (0–36)  •  pays 35:1", style=discord.ButtonStyle.primary, row=4)
    async def straight_up(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await interaction.response.send_modal(NumberModal(self))

# ============================================================================
# ROULETTE COG
# ============================================================================

log = logging.getLogger("launcher")


class RouletteCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    async def cog_load(self):
        for col in ('games_won', 'games_lost'):
            try:
                self.db.execute(f"ALTER TABLE casino_stats ADD COLUMN {col} INTEGER DEFAULT 0")
            except Exception:
                pass

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        try:
            msg = f"❌ An error occurred: {error}"
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
        except Exception:
            pass
        raise error

    @app_commands.command(name="roulette", description=f"Spin the roulette wheel with your {var.CURRENCY_NAME}!")
    @app_commands.describe(amount=f"Amount of {var.CURRENCY_NAME} to bet")
    async def roulette(self, interaction: discord.Interaction, amount: int):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)
        self.db.ensure_user(uid, gid, interaction.user.display_name)

        if amount <= 0:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ Invalid Bet", description=var.MESSAGE_INVALID_BET, color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        if amount < var.MIN_BET:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Bet Too Low",
                    description=var.MESSAGE_BET_TOO_LOW.format(min_bet=var.MIN_BET, currency=var.CURRENCY_NAME),
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        if var.MAX_BET > 0 and amount > var.MAX_BET:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Bet Too High",
                    description=var.MESSAGE_BET_TOO_HIGH.format(max_bet=var.MAX_BET, currency=var.CURRENCY_NAME),
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        balance = self.db.get_balance(uid, gid)
        if balance < amount:
            embed = discord.Embed(
                title="❌ Insufficient Funds",
                description=var.MESSAGE_INSUFFICIENT_FUNDS.format(currency=var.CURRENCY_NAME),
                color=var.COLOR_ERROR,
            )
            embed.add_field(name="Your Balance", value=f"{var.CURRENCY_SYMBOL} {balance:,} {var.CURRENCY_NAME}", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Deduct bet upfront; refunded on timeout, paid out on win
        self.db.update_balance(uid, gid, -amount, 'bet')

        embed = discord.Embed(
            title="🎡 Roulette — Place Your Bet",
            description=(
                f"**Wagered:** {var.CURRENCY_SYMBOL} {amount:,} {var.CURRENCY_NAME}\n\n"
                "Choose a bet type below:"
            ),
            color=var.COLOR_PLAYING,
        )
        embed.add_field(name="🔴 Red / ⚫ Black",       value="pays **1:1**",  inline=True)
        embed.add_field(name="Odd / Even",                value="pays **1:1**",  inline=True)
        embed.add_field(name="Low (1–18) / High (19–36)", value="pays **1:1**",  inline=True)
        embed.add_field(name="Dozens",                    value="pays **2:1**",  inline=True)
        embed.add_field(name="🎯 Straight Up",            value="pays **35:1**", inline=True)
        embed.set_footer(text=f"Played by {interaction.user.display_name} · {var.BUTTON_TIMEOUT}s to choose")
        embed.timestamp = datetime.utcnow()

        view = RouletteView(self, interaction, amount, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(RouletteCog(bot))
    logging.getLogger("launcher").info("✅ Casino/Roulette cog loaded")
