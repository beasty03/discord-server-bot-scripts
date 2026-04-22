import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # for local variables.py
import variables as var
from cogs.Database_management.database_manager import DatabaseManager

db_manager = DatabaseManager(starting_balance=var.STARTING_BALANCE)

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
    aces = sum(1 for rank, _ in hand if rank == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

def format_hand(hand: list[tuple[str, str]], hide_second: bool = False) -> str:
    if hide_second:
        first = f"{hand[0][0]}{hand[0][1]}"
        return f"{first}  🂠"
    return "  ".join(f"{rank}{suit}" for rank, suit in hand)

def is_blackjack(hand: list[tuple[str, str]]) -> bool:
    return len(hand) == 2 and hand_value(hand) == 21

# ============================================================================
# HIT / STAND VIEW
# ============================================================================

class BlackjackView(discord.ui.View):
    def __init__(self, cog: "BlackjackCog", interaction: discord.Interaction,
                 bet: int, deck: list, player_hand: list, dealer_hand: list):
        super().__init__(timeout=var.BUTTON_TIMEOUT)
        self.cog = cog
        self.original_interaction = interaction
        self.bet = bet
        self.deck = deck
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.game_over = False

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
                user_id = self.original_interaction.user.id
                db_manager.update_balance(user_id, self.bet, won=False)
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
            user_id = interaction.user.id
            db_manager.update_balance(user_id, self.bet, won=False)
            new_balance = db_manager.get_user_balance(user_id)

            embed = self._build_embed(
                title="💥 BUST!",
                description=var.MESSAGE_BUST.format(amount=f"{self.bet:,}", currency=var.CURRENCY_NAME),
                color=var.COLOR_LOSE,
                reveal_dealer=True,
                new_balance=new_balance,
            )
            await interaction.response.edit_message(embed=embed, view=self)
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

        # Dealer draws until reaching DEALER_STAND_VALUE
        while hand_value(self.dealer_hand) < var.DEALER_STAND_VALUE:
            self.dealer_hand.append(draw_card(self.deck))

        player_total = hand_value(self.player_hand)
        dealer_total = hand_value(self.dealer_hand)
        user_id = interaction.user.id

        if dealer_total > 21:
            profit = self.bet
            db_manager.update_balance(user_id, profit, won=True)
            new_balance = db_manager.get_user_balance(user_id)
            embed = self._build_embed(
                title="💥 Dealer Busted!",
                description=var.MESSAGE_DEALER_BUST.format(amount=f"{profit:,}", currency=var.CURRENCY_NAME),
                color=var.COLOR_WIN,
                reveal_dealer=True,
                new_balance=new_balance,
            )
        elif player_total > dealer_total:
            profit = self.bet
            db_manager.update_balance(user_id, profit, won=True)
            new_balance = db_manager.get_user_balance(user_id)
            embed = self._build_embed(
                title="🎉 You Win!",
                description=var.MESSAGE_WIN.format(amount=f"{profit:,}", currency=var.CURRENCY_NAME),
                color=var.COLOR_WIN,
                reveal_dealer=True,
                new_balance=new_balance,
            )
        elif player_total < dealer_total:
            db_manager.update_balance(user_id, self.bet, won=False)
            new_balance = db_manager.get_user_balance(user_id)
            embed = self._build_embed(
                title="💸 Dealer Wins!",
                description=var.MESSAGE_LOSE.format(amount=f"{self.bet:,}", currency=var.CURRENCY_NAME),
                color=var.COLOR_LOSE,
                reveal_dealer=True,
                new_balance=new_balance,
            )
        else:
            # Push — refund bet (no change to balance needed)
            new_balance = db_manager.get_user_balance(user_id)
            embed = self._build_embed(
                title="🤝 Push — Tie!",
                description=var.MESSAGE_PUSH.format(amount=f"{self.bet:,}", currency=var.CURRENCY_NAME),
                color=var.COLOR_PUSH,
                reveal_dealer=True,
                new_balance=new_balance,
            )

        await interaction.response.edit_message(embed=embed, view=self)

    def _build_embed(self, title: str, description: str, color: int,
                     reveal_dealer: bool = False, new_balance: int | None = None) -> discord.Embed:
        embed = discord.Embed(title=title, description=description, color=color)
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
    """Blackjack card game commands for Discord."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="blackjack",
        description=f"Play blackjack with your {var.CURRENCY_NAME}!"
    )
    @app_commands.describe(amount=f"Amount of {var.CURRENCY_NAME} to bet")
    async def blackjack(self, interaction: discord.Interaction, amount: int):
        """Blackjack command — beat the dealer without going over 21."""

        user_id = interaction.user.id

        if amount <= 0:
            embed = discord.Embed(
                title="❌ Invalid Bet",
                description=var.MESSAGE_INVALID_BET,
                color=var.COLOR_ERROR,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if amount < var.MIN_BET:
            embed = discord.Embed(
                title="❌ Bet Too Low",
                description=var.MESSAGE_BET_TOO_LOW.format(min_bet=var.MIN_BET, currency=var.CURRENCY_NAME),
                color=var.COLOR_ERROR,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if var.MAX_BET > 0 and amount > var.MAX_BET:
            embed = discord.Embed(
                title="❌ Bet Too High",
                description=var.MESSAGE_BET_TOO_HIGH.format(max_bet=var.MAX_BET, currency=var.CURRENCY_NAME),
                color=var.COLOR_ERROR,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        balance = db_manager.get_user_balance(user_id)
        if balance < amount:
            embed = discord.Embed(
                title="❌ Insufficient Funds",
                description=var.MESSAGE_INSUFFICIENT_FUNDS.format(currency=var.CURRENCY_NAME),
                color=var.COLOR_ERROR,
            )
            embed.add_field(
                name="Your Balance",
                value=f"{var.CURRENCY_SYMBOL} {balance:,} {var.CURRENCY_NAME}",
                inline=False,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Deduct bet upfront; refund/pay out after hand is resolved
        db_manager.update_balance(user_id, amount, won=False)

        deck = build_deck()
        random.shuffle(deck)
        player_hand = [draw_card(deck), draw_card(deck)]
        dealer_hand = [draw_card(deck), draw_card(deck)]

        # Natural blackjack check
        if is_blackjack(player_hand):
            winnings = int(amount * var.BLACKJACK_MULTIPLIER)
            profit = winnings - amount
            db_manager.update_balance(user_id, winnings, won=True)
            new_balance = db_manager.get_user_balance(user_id)

            embed = discord.Embed(
                title="🃏 BLACKJACK!",
                description=var.MESSAGE_BLACKJACK,
                color=var.COLOR_WIN,
            )
            embed.add_field(
                name=f"Your Hand (21)",
                value=format_hand(player_hand),
                inline=False,
            )
            embed.add_field(
                name=f"Dealer's Hand ({hand_value(dealer_hand)})",
                value=format_hand(dealer_hand),
                inline=False,
            )
            embed.add_field(name="Bet", value=f"{var.CURRENCY_SYMBOL} {amount:,}", inline=True)
            embed.add_field(name="Winnings", value=f"{var.CURRENCY_SYMBOL} {winnings:,}", inline=True)
            embed.add_field(
                name="New Balance",
                value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}",
                inline=False,
            )
            embed.set_footer(text=f"Played by {interaction.user.display_name}")
            embed.timestamp = datetime.utcnow()
            await interaction.response.send_message(embed=embed)
            return

        player_total = hand_value(player_hand)
        dealer_shown = hand_value([dealer_hand[0]])

        view = BlackjackView(self, interaction, amount, deck, player_hand, dealer_hand)

        embed = discord.Embed(
            title="🃏 Blackjack",
            description=f"Your turn — you have **{player_total}**. Hit or Stand?",
            color=var.COLOR_PLAYING,
        )
        embed.add_field(
            name=f"Your Hand ({player_total})",
            value=format_hand(player_hand),
            inline=False,
        )
        embed.add_field(
            name=f"Dealer's Hand ({dealer_shown}+?)",
            value=format_hand(dealer_hand, hide_second=True),
            inline=False,
        )
        embed.add_field(name="Bet", value=f"{var.CURRENCY_SYMBOL} {amount:,}", inline=True)
        embed.set_footer(text=f"Played by {interaction.user.display_name}")
        embed.timestamp = datetime.utcnow()

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(
        name="bj_balance",
        description=f"Check your {var.CURRENCY_NAME} balance"
    )
    async def bj_balance(self, interaction: discord.Interaction):
        """Check user balance and statistics."""

        user_id = interaction.user.id
        stats = db_manager.get_user_stats(user_id)

        if not stats:
            db_manager.get_user_balance(user_id)
            stats = db_manager.get_user_stats(user_id)

        net_profit = stats['total_won'] - stats['total_lost']

        embed = discord.Embed(
            title=f"{var.CURRENCY_SYMBOL} Balance",
            description=f"**{interaction.user.display_name}'s** statistics",
            color=var.COLOR_INFO,
        )
        embed.add_field(
            name="Current Balance",
            value=f"{var.CURRENCY_SYMBOL} {stats['balance']:,} {var.CURRENCY_NAME}",
            inline=False,
        )
        embed.add_field(name="Games Played", value=f"{stats['games_played']:,}", inline=True)
        embed.add_field(name="Total Won", value=f"{var.CURRENCY_SYMBOL} {stats['total_won']:,}", inline=True)
        embed.add_field(name="Total Lost", value=f"{var.CURRENCY_SYMBOL} {stats['total_lost']:,}", inline=True)

        profit_emoji = "📈" if net_profit >= 0 else "📉"
        embed.add_field(
            name=f"{profit_emoji} Net Profit/Loss",
            value=f"{var.CURRENCY_SYMBOL} {net_profit:+,} {var.CURRENCY_NAME}",
            inline=False,
        )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        embed.timestamp = datetime.utcnow()

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="bj_daily",
        description=f"Claim your daily {var.CURRENCY_NAME} bonus"
    )
    async def bj_daily(self, interaction: discord.Interaction):
        """Claim daily bonus."""

        user_id = interaction.user.id
        success, time_remaining = db_manager.claim_daily_bonus(user_id, bonus=var.DAILY_BONUS_AMOUNT, cooldown=var.DAILY_BONUS_COOLDOWN)

        if success:
            new_balance = db_manager.get_user_balance(user_id)
            embed = discord.Embed(
                title="🎁 Daily Bonus Claimed!",
                description=f"You received **{var.CURRENCY_SYMBOL} {var.DAILY_BONUS_AMOUNT:,} {var.CURRENCY_NAME}**!",
                color=var.COLOR_WIN,
            )
            embed.add_field(
                name="New Balance",
                value=f"{var.CURRENCY_SYMBOL} {new_balance:,} {var.CURRENCY_NAME}",
                inline=False,
            )
            embed.set_footer(text="Come back tomorrow for another bonus!")
        else:
            hours = time_remaining // 3600
            minutes = (time_remaining % 3600) // 60
            embed = discord.Embed(
                title="⏰ Daily Bonus Not Ready",
                description=f"You can claim your next daily bonus in **{hours}h {minutes}m**",
                color=var.COLOR_ERROR,
            )

        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="bj_leaderboard",
        description="View the top blackjack players"
    )
    async def bj_leaderboard(self, interaction: discord.Interaction):
        """Display leaderboard."""

        top_users = db_manager.get_leaderboard(var.LEADERBOARD_TOP_COUNT)

        embed = discord.Embed(
            title=f"🏆 {var.CURRENCY_NAME} Leaderboard",
            description="Top 10 richest players",
            color=var.COLOR_INFO,
        )

        if not top_users:
            embed.description = "No users found. Start playing to appear here!"
        else:
            leaderboard_text = ""
            for i, (user_id, balance, games) in enumerate(top_users, 1):
                try:
                    user = await self.bot.fetch_user(user_id)
                    username = user.display_name
                except Exception:
                    username = f"User {user_id}"

                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                leaderboard_text += f"{medal} **{username}** - {var.CURRENCY_SYMBOL} {balance:,} ({games} games)\n"

            embed.description = leaderboard_text

        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

# ============================================================================
# COG SETUP FUNCTION
# ============================================================================

async def setup(bot: commands.Bot):
    """
    Setup function to load this cog.
    Required for the launcher to load this module.
    """
    await bot.add_cog(BlackjackCog(bot))

    print("✅ Casino/Blackjack cog loaded successfully")
