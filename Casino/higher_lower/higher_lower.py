import discord
from discord.ext import commands
from discord import app_commands
import random
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('hl_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

# ============================================================================
# HELPERS
# ============================================================================

CARD_RANKS  = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
CARD_VALUES = {r: i + 1 for i, r in enumerate(CARD_RANKS)}
CARD_NAMES  = {"A": "Ace", "J": "Jack", "Q": "Queen", "K": "King",
               **{str(n): str(n) for n in range(2, 11)}}

def draw_card() -> tuple[str, int]:
    rank = random.choice(CARD_RANKS)
    return rank, CARD_VALUES[rank]

def card_box(rank: str) -> str:
    return f"` {CARD_NAMES.get(rank, rank)} `"

def get_multiplier(correct_rounds: int) -> float:
    if correct_rounds <= 0:
        return 1.0
    idx = min(correct_rounds - 1, len(var.ROUND_MULTIPLIERS) - 1)
    return var.ROUND_MULTIPLIERS[idx]

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

# ============================================================================
# VIEW
# ============================================================================

class HigherLowerView(discord.ui.View):

    def __init__(
        self,
        original_interaction: discord.Interaction,
        bet: int,
        user_id: int,
        current_card: str,
        current_number: int,
        correct_rounds: int = 0,
    ):
        super().__init__(timeout=var.BUTTON_TIMEOUT)
        self.db                   = ForgeDB.get()
        self.original_interaction = original_interaction
        self.bet                  = bet
        self.user_id              = str(user_id)
        self.guild_id             = str(original_interaction.guild_id)
        self.current_card         = current_card
        self.current_number       = current_number
        self.correct_rounds       = correct_rounds
        self.resolved             = False

        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.label and "Cash Out" in item.label:
                item.disabled = correct_rounds == 0

    # ── Guards ────────────────────────────────────────────────────────────────

    async def _check_user(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return False
        return True

    # ── Core guess logic ──────────────────────────────────────────────────────

    async def _process_guess(self, interaction: discord.Interaction, guess: str):
        if self.resolved:
            return

        prev_card   = self.current_card
        prev_number = self.current_number
        next_card, next_number = draw_card()

        tied = next_number == prev_number
        won  = (guess == "higher" and next_number > prev_number) or \
               (guess == "lower"  and next_number < prev_number)

        if tied:
            # Streak intact, game continues — no balance change
            embed = self._tie_embed(prev_card, next_card)
            await interaction.response.edit_message(embed=embed, view=self)
            return

        if not won:
            self.resolved = True
            for item in self.children:
                item.disabled = True
            _record_stats(self.db, self.user_id, self.guild_id, 0, self.bet)
            new_balance = self.db.get_balance(self.user_id, self.guild_id)
            embed = self._loss_embed(prev_card, next_card, guess, new_balance)
            await interaction.response.edit_message(embed=embed, view=self)
            if interaction.channel:
                await interaction.channel.send(embed=discord.Embed(
                    description=f"🎴 **{interaction.user.display_name}** lost {var.CURRENCY_SYMBOL} **{self.bet:,}** playing Higher or Lower",
                    color=var.COLOR_LOSE,
                ))
            return

        self.current_card    = next_card
        self.current_number  = next_number
        self.correct_rounds += 1

        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.label and "Cash Out" in item.label:
                item.disabled = False

        if self.correct_rounds > len(var.ROUND_MULTIPLIERS):
            await self._finish_cashout(interaction, auto=True)
            return

        embed = self._in_progress_embed(prev_card, next_card, guess)
        await interaction.response.edit_message(embed=embed, view=self)

    async def _finish_cashout(self, interaction: discord.Interaction, auto: bool = False):
        if self.resolved:
            return
        self.resolved = True
        for item in self.children:
            item.disabled = True

        multiplier  = get_multiplier(self.correct_rounds)
        payout      = int(self.bet * multiplier)
        dm_mult     = getattr(interaction.client, 'multiplier_event_mult', None) or 1.0
        if dm_mult > 1.0:
            payout = self.bet + int((payout - self.bet) * dm_mult)
        self.db.update_balance(self.user_id, self.guild_id, payout, 'win')
        _record_stats(self.db, self.user_id, self.guild_id, payout - self.bet, 0)
        new_balance = self.db.get_balance(self.user_id, self.guild_id)
        embed       = self._cashout_embed(payout, new_balance, auto=auto, dm_mult=dm_mult)
        await interaction.response.edit_message(embed=embed, view=self)
        if interaction.channel:
            profit = payout - self.bet
            await interaction.channel.send(embed=discord.Embed(
                description=f"🎴 **{interaction.user.display_name}** cashed out {var.CURRENCY_SYMBOL} **{profit:,}** profit playing Higher or Lower!"
                + (f" 💰 **{dm_mult}x** event!" if dm_mult > 1.0 else ""),
                color=var.COLOR_WIN,
            ))

    # ── Embeds ────────────────────────────────────────────────────────────────

    def _start_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎴 Higher or Lower",
            description=(
                f"**Current card: {card_box(self.current_card)}**\n\n"
                f"Will the next card be **higher** or **lower**?\n"
                f"Cards run Ace (low) → 2–10 → Jack → Queen → King (high)."
            ),
            color=var.COLOR_PLAYING,
        )
        self._add_round_fields(embed)
        embed.set_footer(text=f"Played by {self.original_interaction.user.display_name} · {var.BUTTON_TIMEOUT}s per guess")
        embed.timestamp = datetime.utcnow()
        return embed

    def _in_progress_embed(self, prev_card: str, revealed_card: str, guess: str) -> discord.Embed:
        direction = "higher" if CARD_VALUES[revealed_card] > CARD_VALUES[prev_card] else "lower"
        embed = discord.Embed(
            title="🎴 Higher or Lower",
            description=(
                f"✅ **Correct!** You guessed **{guess}** — it was {card_box(revealed_card)} "
                f"({direction} than {CARD_NAMES[prev_card]}).\n\n"
                f"**New card: {card_box(self.current_card)}**\n"
                f"Will the next be **higher** or **lower**? Or cash out?"
            ),
            color=var.COLOR_PLAYING,
        )
        self._add_round_fields(embed)
        embed.set_footer(text=f"Played by {self.original_interaction.user.display_name}")
        embed.timestamp = datetime.utcnow()
        return embed

    def _tie_embed(self, prev_card: str, tied_card: str) -> discord.Embed:
        embed = discord.Embed(
            title="🤝 Tie!",
            description=(
                f"You drew {card_box(tied_card)} — same value as {CARD_NAMES[prev_card]}!\n"
                f"Your streak is safe. Guess again on **{CARD_NAMES[self.current_card]}**."
            ),
            color=0xF1C40F,
        )
        self._add_round_fields(embed)
        embed.set_footer(text=f"Played by {self.original_interaction.user.display_name}")
        embed.timestamp = datetime.utcnow()
        return embed

    def _loss_embed(self, prev_card: str, revealed_card: str, guess: str, new_balance: int) -> discord.Embed:
        direction = "higher" if CARD_VALUES[revealed_card] > CARD_VALUES[prev_card] else "lower"
        embed = discord.Embed(
            title="❌ Wrong!",
            description=(
                f"You guessed **{guess}** but it was {card_box(revealed_card)} "
                f"({direction} than {CARD_NAMES[prev_card]}).\n\n"
                f"You lost {var.CURRENCY_SYMBOL} **{self.bet:,}** {var.CURRENCY_NAME}."
            ),
            color=var.COLOR_LOSE,
        )
        embed.add_field(name="Correct Guesses", value=str(self.correct_rounds), inline=True)
        embed.add_field(name="New Balance",     value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}", inline=False)
        embed.set_footer(text=f"Played by {self.original_interaction.user.display_name}")
        embed.timestamp = datetime.utcnow()
        return embed

    def _cashout_embed(self, payout: int, new_balance: int, auto: bool = False, dm_mult: float = 1.0) -> discord.Embed:
        multiplier = get_multiplier(self.correct_rounds)
        profit     = payout - self.bet
        title      = "🏆 Max Rounds — Auto Cash Out!" if auto else "💰 Cashed Out!"
        guesses    = f"{self.correct_rounds} correct guess{'es' if self.correct_rounds != 1 else ''}"
        embed = discord.Embed(
            title=title,
            description=f"You walked away after {guesses} at **{multiplier}x**!",
            color=var.COLOR_WIN,
        )
        embed.add_field(name="Original Bet", value=f"{var.CURRENCY_SYMBOL} {self.bet:,}",    inline=True)
        embed.add_field(name="Payout",       value=f"{var.CURRENCY_SYMBOL} {payout:,}",      inline=True)
        embed.add_field(name="Profit",       value=f"{var.CURRENCY_SYMBOL} +{profit:,}",      inline=True)
        if dm_mult > 1.0:
            embed.add_field(name="💰 Event Bonus", value=f"**{dm_mult}x** multiplier applied!", inline=False)
        embed.add_field(name="New Balance",  value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}", inline=False)
        embed.set_footer(text=f"Played by {self.original_interaction.user.display_name}")
        embed.timestamp = datetime.utcnow()
        return embed

    def _add_round_fields(self, embed: discord.Embed):
        max_rounds = len(var.ROUND_MULTIPLIERS)
        multiplier = get_multiplier(self.correct_rounds)
        potential  = int(self.bet * multiplier)
        next_mult  = var.ROUND_MULTIPLIERS[self.correct_rounds] if self.correct_rounds < max_rounds else None

        embed.add_field(name="Bet",   value=f"{var.CURRENCY_SYMBOL} {self.bet:,}", inline=True)
        embed.add_field(name="Round", value=f"{self.correct_rounds + 1} / {max_rounds + 1}", inline=True)

        if self.correct_rounds > 0:
            embed.add_field(name=f"Cash Out Now ({multiplier}x)", value=f"{var.CURRENCY_SYMBOL} {potential:,}", inline=True)
        if next_mult:
            next_payout = int(self.bet * next_mult)
            embed.add_field(name=f"Next Round ({next_mult}x)", value=f"{var.CURRENCY_SYMBOL} {next_payout:,}", inline=True)

    # ── Timeout ───────────────────────────────────────────────────────────────

    async def on_timeout(self):
        if self.resolved:
            return
        self.resolved = True
        for item in self.children:
            item.disabled = True

        if self.correct_rounds > 0:
            multiplier  = get_multiplier(self.correct_rounds)
            payout      = int(self.bet * multiplier)
            self.db.update_balance(self.user_id, self.guild_id, payout, 'win')
            _record_stats(self.db, self.user_id, self.guild_id, payout - self.bet, 0)
            new_balance = self.db.get_balance(self.user_id, self.guild_id)
            embed = discord.Embed(
                title="⏰ Timed Out — Auto Cash Out",
                description="You ran out of time. Your winnings were cashed out automatically.",
                color=var.COLOR_WIN,
            )
            embed.add_field(name="Payout",      value=f"{var.CURRENCY_SYMBOL} {payout:,} {var.CURRENCY_NAME}", inline=False)
            embed.add_field(name="New Balance", value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}", inline=False)
        else:
            self.db.update_balance(self.user_id, self.guild_id, self.bet, 'refund')
            embed = discord.Embed(
                title="⏰ Timed Out",
                description=f"You didn't make a guess. Your {var.CURRENCY_SYMBOL} {self.bet:,} {var.CURRENCY_NAME} has been refunded.",
                color=var.COLOR_ERROR,
            )

        embed.timestamp = datetime.utcnow()
        try:
            await self.original_interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            pass

    # ── Buttons ───────────────────────────────────────────────────────────────

    @discord.ui.button(label="⬆️ Higher", style=discord.ButtonStyle.success, row=0)
    async def higher(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await self._process_guess(interaction, "higher")

    @discord.ui.button(label="⬇️ Lower", style=discord.ButtonStyle.danger, row=0)
    async def lower(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await self._process_guess(interaction, "lower")

    @discord.ui.button(label="💰 Cash Out", style=discord.ButtonStyle.secondary, row=1)
    async def cash_out(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await self._finish_cashout(interaction)

# ============================================================================
# COG
# ============================================================================

log = logging.getLogger("launcher")


class HigherLowerCog(commands.Cog):

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

    @app_commands.command(name="highlow", description=f"Play Higher or Lower and stack multipliers!")
    @app_commands.describe(amount=f"Amount of {var.CURRENCY_NAME} to bet")
    async def highlow(self, interaction: discord.Interaction, amount: int):
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

        # Deduct bet upfront; refunded on round-0 timeout, paid out on cash-out/win
        self.db.update_balance(uid, gid, -amount, 'bet')

        starting_card, starting_number = draw_card()
        view  = HigherLowerView(interaction, amount, interaction.user.id, starting_card, starting_number)
        embed = view._start_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(HigherLowerCog(bot))
    logging.getLogger("launcher").info("✅ Casino/HigherLower cog loaded")
