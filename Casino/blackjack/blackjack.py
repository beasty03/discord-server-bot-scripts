import discord
from discord.ext import commands
from discord import app_commands
import random
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('blackjack_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

# ============================================================================
# CARD / DECK HELPERS
# ============================================================================

CARD_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6,
    "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10, "A": 11,
}

def build_deck() -> list[tuple[str, str]]:
    ranks = list(CARD_VALUES.keys())
    return [(rank, suit) for suit in var.SUITS for rank in ranks]

def draw_card(deck: list) -> tuple[str, str]:
    return deck.pop(random.randrange(len(deck)))

def hand_value(hand: list[tuple[str, str]]) -> int:
    total = sum(CARD_VALUES[rank] for rank, _ in hand)
    aces  = sum(1 for rank, _ in hand if rank == "A")
    while total > 21 and aces:
        total -= 10
        aces  -= 1
    return total

def format_hand(hand: list[tuple[str, str]], hide_second: bool = False) -> str:
    if hide_second:
        first = f"{hand[0][0]}{hand[0][1]}"
        return f"{first}  🂠"
    return "  ".join(f"{rank}{suit}" for rank, suit in hand)

def is_blackjack(hand: list[tuple[str, str]]) -> bool:
    return len(hand) == 2 and hand_value(hand) == 21

def _record_stats(db, uid: str, gid: str, won: int = 0, lost: int = 0):
    db.execute(
        """INSERT INTO casino_stats (user_id, guild_id, games_played, total_won, total_lost)
           VALUES (?, ?, 1, ?, ?)
           ON CONFLICT(user_id, guild_id) DO UPDATE SET
               games_played = games_played + 1,
               total_won    = total_won    + excluded.total_won,
               total_lost   = total_lost   + excluded.total_lost""",
        (uid, gid, won, lost),
    )

# ============================================================================
# HIT / STAND VIEW
# ============================================================================

class BlackjackView(discord.ui.View):
    def __init__(self, cog: "BlackjackCog", interaction: discord.Interaction,
                 bet: int, deck: list, player_hand: list, dealer_hand: list):
        super().__init__(timeout=var.BUTTON_TIMEOUT)
        self.cog = cog
        self.original_interaction = interaction
        self.bet         = bet
        self.deck        = deck
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.game_over   = False
        self.uid         = str(interaction.user.id)
        self.gid         = str(interaction.guild_id)

    def _uid_gid(self, interaction: discord.Interaction) -> tuple[str, str]:
        return str(interaction.user.id), str(self.original_interaction.guild_id)

    async def on_timeout(self):
        if not self.game_over:
            self.game_over = True
            for item in self.children:
                item.disabled = True
            embed = discord.Embed(
                title="⏰ Game Timed Out",
                description=f"You took too long! Your bet of {var.CURRENCY_SYMBOL} {self.bet:,} {var.CURRENCY_NAME} is lost.",
                color=var.COLOR_ERROR,
            )
            embed.timestamp = datetime.utcnow()
            try:
                await self.original_interaction.edit_original_response(embed=embed, view=self)
            except Exception:
                pass

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary, emoji="👊")
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return

        self.player_hand.append(draw_card(self.deck))
        player_total = hand_value(self.player_hand)

        if player_total > 21:
            self.game_over = True
            for item in self.children:
                item.disabled = True
            uid, gid = self._uid_gid(interaction)
            _record_stats(self.cog.db, uid, gid, 0, self.bet)
            new_balance = self.cog.db.get_balance(uid, gid)

            embed = self._build_embed(
                title="💥 BUST!",
                description=var.MESSAGE_BUST.format(amount=f"{self.bet:,}", currency=var.CURRENCY_NAME),
                color=var.COLOR_LOSE,
                reveal_dealer=True,
                new_balance=new_balance,
            )
            await interaction.response.edit_message(embed=embed, view=self)
            if interaction.channel:
                await interaction.channel.send(embed=discord.Embed(
                    description=f"🃏 **{interaction.user.display_name}** busted and lost {var.CURRENCY_SYMBOL} **{self.bet:,}** playing Blackjack",
                    color=var.COLOR_LOSE,
                ))
            return

        if player_total == 21:
            await self._stand(interaction)
            return

        embed = self._build_embed(
            title="🃏 Blackjack",
            description=f"Your turn — you have **{player_total}**",
            color=var.COLOR_PLAYING,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary, emoji="✋")
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("This is not your game!", ephemeral=True)
            return
        await self._stand(interaction)

    async def _stand(self, interaction: discord.Interaction):
        self.game_over = True
        for item in self.children:
            item.disabled = True

        while hand_value(self.dealer_hand) < var.DEALER_STAND_VALUE:
            self.dealer_hand.append(draw_card(self.deck))

        player_total = hand_value(self.player_hand)
        dealer_total = hand_value(self.dealer_hand)
        uid, gid     = self._uid_gid(interaction)
        dm_mult      = getattr(self.original_interaction.client, 'double_money_multiplier', None) or 1.0

        if dealer_total > 21 or player_total > dealer_total:
            raw_payout = int(self.bet * var.WIN_MULTIPLIER)
            profit     = raw_payout - self.bet
            if dm_mult > 1.0:
                profit     = int(profit * dm_mult)
                raw_payout = self.bet + profit
            self.cog.db.update_balance(uid, gid, raw_payout, 'win')
            _record_stats(self.cog.db, uid, gid, profit, 0)
            new_balance = self.cog.db.get_balance(uid, gid)
            title = "💥 Dealer Busted!" if dealer_total > 21 else "🎉 You Win!"
            desc  = (var.MESSAGE_DEALER_BUST if dealer_total > 21 else var.MESSAGE_WIN).format(
                amount=f"{self.bet:,}", currency=var.CURRENCY_NAME
            )
            embed = self._build_embed(title=title, description=desc, color=var.COLOR_WIN,
                                      reveal_dealer=True, new_balance=new_balance)
            if dm_mult > 1.0:
                embed.add_field(name="💰 Event Bonus", value=f"**{dm_mult}x** multiplier applied!", inline=False)
        elif player_total < dealer_total:
            _record_stats(self.cog.db, uid, gid, 0, self.bet)
            new_balance = self.cog.db.get_balance(uid, gid)
            embed = self._build_embed(
                title="💸 Dealer Wins!",
                description=var.MESSAGE_LOSE.format(amount=f"{self.bet:,}", currency=var.CURRENCY_NAME),
                color=var.COLOR_LOSE,
                reveal_dealer=True,
                new_balance=new_balance,
            )
        else:
            self.cog.db.update_balance(uid, gid, self.bet, 'refund')
            _record_stats(self.cog.db, uid, gid, 0, 0)
            new_balance = self.cog.db.get_balance(uid, gid)
            embed = self._build_embed(
                title="🤝 Push — Tie!",
                description=var.MESSAGE_PUSH.format(amount=f"{self.bet:,}", currency=var.CURRENCY_NAME),
                color=var.COLOR_PUSH,
                reveal_dealer=True,
                new_balance=new_balance,
            )

        await interaction.response.edit_message(embed=embed, view=self)
        if interaction.channel:
            name = interaction.user.display_name
            sym  = var.CURRENCY_SYMBOL
            if dealer_total > 21 or player_total > dealer_total:
                await interaction.channel.send(embed=discord.Embed(
                    description=f"🃏 **{name}** won {sym} **{profit:,}** playing Blackjack!"
                    + (f" 💰 **{dm_mult}x** event!" if dm_mult > 1.0 else ""),
                    color=var.COLOR_WIN,
                ))
            elif player_total < dealer_total:
                await interaction.channel.send(embed=discord.Embed(
                    description=f"🃏 **{name}** lost {sym} **{self.bet:,}** playing Blackjack",
                    color=var.COLOR_LOSE,
                ))

    def _build_embed(self, title: str, description: str, color: int,
                     reveal_dealer: bool = False, new_balance: int | None = None) -> discord.Embed:
        embed        = discord.Embed(title=title, description=description, color=color)
        player_total = hand_value(self.player_hand)
        dealer_shown = hand_value(self.dealer_hand) if reveal_dealer else hand_value([self.dealer_hand[0]])

        embed.add_field(
            name=f"Your Hand ({player_total})",
            value=format_hand(self.player_hand),
            inline=False,
        )
        if reveal_dealer:
            embed.add_field(
                name=f"Dealer's Hand ({hand_value(self.dealer_hand)})",
                value=format_hand(self.dealer_hand),
                inline=False,
            )
        else:
            embed.add_field(
                name=f"Dealer's Hand ({dealer_shown}+?)",
                value=format_hand(self.dealer_hand, hide_second=True),
                inline=False,
            )

        embed.add_field(name="Bet", value=f"{var.CURRENCY_SYMBOL} {self.bet:,}", inline=True)

        if new_balance is not None:
            embed.add_field(
                name="New Balance",
                value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}",
                inline=False,
            )

        embed.set_footer(text=f"Played by {self.original_interaction.user.display_name}")
        embed.timestamp = datetime.utcnow()
        return embed

# ============================================================================
# BLACKJACK COG CLASS
# ============================================================================

class BlackjackCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ An error occurred: {error}", ephemeral=True)
        except Exception:
            pass
        raise error

    @app_commands.command(name="blackjack", description=f"Play blackjack with your {var.CURRENCY_NAME}!")
    @app_commands.describe(amount=f"Amount of {var.CURRENCY_NAME} to bet")
    async def blackjack(self, interaction: discord.Interaction, amount: int):
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

        # Deduct bet upfront; refund/pay out after hand is resolved
        self.db.update_balance(uid, gid, -amount, 'bet')

        deck = build_deck()
        random.shuffle(deck)
        player_hand = [draw_card(deck), draw_card(deck)]
        dealer_hand = [draw_card(deck), draw_card(deck)]

        if is_blackjack(player_hand):
            dm_mult  = getattr(interaction.client, 'double_money_multiplier', None) or 1.0
            winnings = int(amount * var.BLACKJACK_MULTIPLIER)
            profit   = winnings - amount
            if dm_mult > 1.0:
                profit   = int(profit * dm_mult)
                winnings = amount + profit
            self.db.update_balance(uid, gid, winnings, 'win')
            _record_stats(self.db, uid, gid, profit, 0)
            new_balance = self.db.get_balance(uid, gid)

            embed = discord.Embed(title="🃏 BLACKJACK!", description=var.MESSAGE_BLACKJACK, color=var.COLOR_WIN)
            embed.add_field(name="Your Hand (21)",       value=format_hand(player_hand),             inline=False)
            embed.add_field(name=f"Dealer's Hand ({hand_value(dealer_hand)})", value=format_hand(dealer_hand), inline=False)
            embed.add_field(name="Bet",      value=f"{var.CURRENCY_SYMBOL} {amount:,}",   inline=True)
            embed.add_field(name="Winnings", value=f"{var.CURRENCY_SYMBOL} {winnings:,}", inline=True)
            if dm_mult > 1.0:
                embed.add_field(name="💰 Event Bonus", value=f"**{dm_mult}x** multiplier applied!", inline=False)
            embed.add_field(name="New Balance", value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}", inline=False)
            embed.set_footer(text=f"Played by {interaction.user.display_name}")
            embed.timestamp = datetime.utcnow()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            if interaction.channel:
                await interaction.channel.send(embed=discord.Embed(
                    description=f"🃏 **{interaction.user.display_name}** hit BLACKJACK and won {var.CURRENCY_SYMBOL} **{profit:,}** playing Blackjack!"
                    + (f" 💰 **{dm_mult}x** event!" if dm_mult > 1.0 else ""),
                    color=var.COLOR_WIN,
                ))
            return

        player_total = hand_value(player_hand)
        dealer_shown = hand_value([dealer_hand[0]])
        view = BlackjackView(self, interaction, amount, deck, player_hand, dealer_hand)

        embed = discord.Embed(
            title="🃏 Blackjack",
            description=f"Your turn — you have **{player_total}**. Hit or Stand?",
            color=var.COLOR_PLAYING,
        )
        embed.add_field(name=f"Your Hand ({player_total})",     value=format_hand(player_hand),                      inline=False)
        embed.add_field(name=f"Dealer's Hand ({dealer_shown}+?)", value=format_hand(dealer_hand, hide_second=True), inline=False)
        embed.add_field(name="Bet", value=f"{var.CURRENCY_SYMBOL} {amount:,}", inline=True)
        embed.set_footer(text=f"Played by {interaction.user.display_name}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(BlackjackCog(bot))
    logging.getLogger("launcher").info("✅ Casino/Blackjack cog loaded")
