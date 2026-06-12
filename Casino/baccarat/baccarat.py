import discord
from discord.ext import commands
from discord import app_commands
import random
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('baccarat_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

# ============================================================================
# CARD / DECK HELPERS
# ============================================================================

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

def build_deck() -> list[tuple[str, str]]:
    return [(rank, suit) for suit in var.SUITS for rank in RANKS]

def card_value(rank: str) -> int:
    if rank in ("10", "J", "Q", "K"):
        return 0
    if rank == "A":
        return 1
    return int(rank)

def hand_total(hand: list[tuple[str, str]]) -> int:
    return sum(card_value(r) for r, _ in hand) % 10

def format_hand(hand: list[tuple[str, str]]) -> str:
    return "  ".join(f"{r}{s}" for r, s in hand)

def is_natural(hand: list[tuple[str, str]]) -> bool:
    return hand_total(hand) in (8, 9)

# ============================================================================
# BACCARAT DEAL
# ============================================================================

def deal_baccarat(deck: list) -> tuple[list, list]:
    player = [deck.pop(), deck.pop()]
    banker = [deck.pop(), deck.pop()]

    if is_natural(player) or is_natural(banker):
        return player, banker

    player_drew  = False
    player_third = None
    if hand_total(player) <= 5:
        player_third = deck.pop()
        player.append(player_third)
        player_drew = True

    bt = hand_total(banker)
    if not player_drew:
        if bt <= 5:
            banker.append(deck.pop())
    else:
        tv = card_value(player_third[0])
        if bt <= 2:
            banker.append(deck.pop())
        elif bt == 3 and tv != 8:
            banker.append(deck.pop())
        elif bt == 4 and 2 <= tv <= 7:
            banker.append(deck.pop())
        elif bt == 5 and 4 <= tv <= 7:
            banker.append(deck.pop())
        elif bt == 6 and 6 <= tv <= 7:
            banker.append(deck.pop())

    return player, banker

def determine_outcome(player: list, banker: list) -> str:
    pt = hand_total(player)
    bt = hand_total(banker)
    if pt > bt:
        return "player"
    if bt > pt:
        return "banker"
    return "tie"

# ============================================================================
# BET-SELECTION VIEW
# ============================================================================

class BaccaratView(discord.ui.View):

    def __init__(self, original_interaction: discord.Interaction, bet: int, user_id: int):
        super().__init__(timeout=var.BUTTON_TIMEOUT)
        self.db                   = ForgeDB.get()
        self.original_interaction = original_interaction
        self.bet                  = bet
        self.user_id              = str(user_id)
        self.guild_id             = str(original_interaction.guild_id)
        self.resolved             = False

    async def _check_user(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return False
        return True

    async def _resolve(self, interaction: discord.Interaction, chosen_bet: str):
        if self.resolved:
            return
        self.resolved = True
        for item in self.children:
            item.disabled = True

        deck = build_deck()
        random.shuffle(deck)
        player, banker = deal_baccarat(deck)
        outcome        = determine_outcome(player, banker)

        won    = chosen_bet == outcome
        is_tie = outcome == "tie"

        if won:
            mult   = {"player": var.PLAYER_MULTIPLIER,
                      "banker": var.BANKER_MULTIPLIER,
                      "tie":    var.TIE_MULTIPLIER}[chosen_bet]
            payout = int(self.bet * mult)
            self.db.update_balance(self.user_id, self.guild_id, payout, 'win')
        elif is_tie and chosen_bet != "tie" and var.TIE_PUSHES_SIDE_BETS:
            self.db.update_balance(self.user_id, self.guild_id, self.bet, 'refund')
            payout = self.bet
        else:
            payout = 0

        new_balance = self.db.get_balance(self.user_id, self.guild_id)
        embed       = self._build_result_embed(player, banker, outcome, chosen_bet, payout, new_balance, is_tie)
        await interaction.response.edit_message(embed=embed, view=self)

    def _build_result_embed(
        self,
        player: list, banker: list,
        outcome: str, chosen_bet: str,
        payout: int, new_balance: int,
        is_tie: bool,
    ) -> discord.Embed:
        pt = hand_total(player)
        bt = hand_total(banker)

        outcome_colors = {"player": var.COLOR_PLAYER, "banker": var.COLOR_BANKER, "tie": var.COLOR_TIE}
        outcome_labels = {"player": "👤 Player Wins!", "banker": "🏦 Banker Wins!", "tie": "🤝 Tie!"}

        won    = chosen_bet == outcome
        pushed = is_tie and chosen_bet != "tie" and var.TIE_PUSHES_SIDE_BETS

        if won:
            profit      = payout - self.bet
            result_line = f"✅ **You won!** Payout: {var.CURRENCY_SYMBOL} **{payout:,}** (+{profit:,} profit)"
        elif pushed:
            result_line = f"↩️ **Push!** Your bet of {var.CURRENCY_SYMBOL} **{self.bet:,}** was refunded."
        else:
            result_line = f"❌ **You lost** {var.CURRENCY_SYMBOL} **{self.bet:,}** {var.CURRENCY_NAME}."

        embed = discord.Embed(
            title=f"🃏 Baccarat — {outcome_labels[outcome]}",
            description=result_line,
            color=outcome_colors[outcome],
        )
        embed.add_field(name=f"👤 Player Hand  ({pt})", value=format_hand(player), inline=False)
        embed.add_field(name=f"🏦 Banker Hand  ({bt})", value=format_hand(banker), inline=False)

        bet_label = {"player": "👤 Player", "banker": "🏦 Banker", "tie": "🤝 Tie"}[chosen_bet]
        embed.add_field(name="Your Bet",    value=f"{bet_label} — {var.CURRENCY_SYMBOL} {self.bet:,}", inline=True)
        embed.add_field(name="New Balance", value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}", inline=True)
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
                description=f"You didn't pick a bet. Your {var.CURRENCY_SYMBOL} {self.bet:,} {var.CURRENCY_NAME} has been refunded.",
                color=var.COLOR_ERROR,
            )
            embed.timestamp = datetime.utcnow()
            try:
                await self.original_interaction.edit_original_response(embed=embed, view=self)
            except Exception:
                pass

    # ── Bet buttons ───────────────────────────────────────────────────────────

    @discord.ui.button(label="👤 Player  (1:1)", style=discord.ButtonStyle.primary, row=0)
    async def bet_player(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await self._resolve(interaction, "player")

    @discord.ui.button(label="🏦 Banker  (0.95:1)", style=discord.ButtonStyle.danger, row=0)
    async def bet_banker(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await self._resolve(interaction, "banker")

    @discord.ui.button(label="🤝 Tie  (8:1)", style=discord.ButtonStyle.success, row=0)
    async def bet_tie(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if not await self._check_user(interaction):
            return
        await self._resolve(interaction, "tie")

# ============================================================================
# BACCARAT COG
# ============================================================================

log = logging.getLogger("launcher")


class BaccaratCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

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

    @app_commands.command(name="baccarat", description=f"Play Baccarat — bet on Player, Banker, or Tie!")
    @app_commands.describe(amount=f"Amount of {var.CURRENCY_NAME} to bet")
    async def baccarat(self, interaction: discord.Interaction, amount: int):
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

        # Deduct bet upfront; refunded on timeout or tie-push
        self.db.update_balance(uid, gid, -amount, 'bet')

        embed = discord.Embed(
            title="🃏 Baccarat — Place Your Bet",
            description=(
                f"**Wagered:** {var.CURRENCY_SYMBOL} {amount:,} {var.CURRENCY_NAME}\n\n"
                "Bet on who you think will have the highest hand (closest to 9):"
            ),
            color=var.COLOR_PLAYING,
        )
        embed.add_field(name="👤 Player", value="pays **1:1**",                          inline=True)
        embed.add_field(name="🏦 Banker", value="pays **0.95:1**\n*(5% commission)*",    inline=True)
        embed.add_field(name="🤝 Tie",    value="pays **8:1**",                          inline=True)
        embed.add_field(
            name="📖 Rules",
            value=(
                "• Cards 2–9 = face value  •  10/J/Q/K = 0  •  A = 1\n"
                "• Hand total = sum mod 10  •  Natural (8 or 9) beats all\n"
                "• Tie pushes Player/Banker bets (refunded)"
            ),
            inline=False,
        )
        embed.set_footer(text=f"Played by {interaction.user.display_name} · {var.BUTTON_TIMEOUT}s to choose")
        embed.timestamp = datetime.utcnow()

        view = BaccaratView(interaction, amount, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(BaccaratCog(bot))
    logging.getLogger("launcher").info("✅ Casino/Baccarat cog loaded")
