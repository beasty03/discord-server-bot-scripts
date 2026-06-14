import asyncio
import random
import time
from datetime import datetime
from pathlib import Path
import sys

import discord
from discord import app_commands
from discord.ext import commands

sys.path.insert(0, str(Path(__file__).parent))
import variables as var
from forge_db import ForgeDB


# ── Game constants ────────────────────────────────────────────────────────────

_MOVES = {"rock": "✊ Rock", "paper": "📄 Paper", "scissors": "✂️ Scissors"}
# key beats value
_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def _house_tx(db, bot_uid: str, gid: str, amount: int, tx_type: str):
    db.ensure_user(bot_uid, gid, "House")
    db.update_balance(bot_uid, gid, amount, tx_type)


def _validate_bet(db, uid: str, gid: str, amount: int) -> str | None:
    if amount <= 0:
        return "Please enter a valid bet amount."
    if amount < var.MIN_BET:
        return f"Minimum bet is {var.CURRENCY_SYMBOL} **{var.MIN_BET:,}** {var.CURRENCY_NAME}."
    if var.MAX_BET > 0 and amount > var.MAX_BET:
        return f"Maximum bet is {var.CURRENCY_SYMBOL} **{var.MAX_BET:,}** {var.CURRENCY_NAME}."
    balance = db.get_balance(uid, gid)
    if balance < amount:
        return f"You only have {var.CURRENCY_SYMBOL} **{balance:,}** {var.CURRENCY_NAME}."
    return None


# ── vs-bot pick view ──────────────────────────────────────────────────────────

class _BotPickView(discord.ui.View):
    """Rock / Paper / Scissors buttons for vs-bot play (ephemeral)."""

    def __init__(self, cog: "RPSCog", uid: str, gid: str, amount: int):
        super().__init__(timeout=30.0)
        self.cog    = cog
        self.uid    = uid
        self.gid    = gid
        self.amount = amount
        self.done   = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.uid:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return False
        if self.done:
            await interaction.response.send_message("✅ Already resolved.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✊ Rock",     style=discord.ButtonStyle.primary)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, "rock")

    @discord.ui.button(label="📄 Paper",    style=discord.ButtonStyle.success)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, "paper")

    @discord.ui.button(label="✂️ Scissors", style=discord.ButtonStyle.danger)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._resolve(interaction, "scissors")

    async def _resolve(self, interaction: discord.Interaction, player_move: str):
        self.done = True
        self.stop()

        db      = self.cog.db
        bot_uid = str(self.cog.bot.user.id)
        name    = interaction.user.display_name
        dm_mult = getattr(self.cog.bot, 'multiplier_event_mult', None) or 1.0

        bot_move = random.choice(list(_MOVES.keys()))

        if _BEATS[player_move] == bot_move:
            # Player wins
            profit = self.amount
            if dm_mult > 1.0:
                profit = int(profit * dm_mult)
            db.update_balance(self.uid, self.gid, profit, 'win')
            _house_tx(db, bot_uid, self.gid, -profit, 'house_payout')
            _record_stats(db, self.uid, self.gid, profit, 0)
            new_bal = db.get_balance(self.uid, self.gid)
            embed = discord.Embed(title="✂️ Rock Paper Scissors — You Won! 🎉", color=var.COLOR_WIN)
            result_line = f"🏆 You win {var.CURRENCY_SYMBOL} **{profit:,}**!"
            pub_desc = f"✂️ **{name}** won {var.CURRENCY_SYMBOL} **{profit:,}** at Rock Paper Scissors!"
            if dm_mult > 1.0:
                pub_desc += f" *(💰 {dm_mult}x event!)*"
        elif _BEATS[bot_move] == player_move:
            # Bot wins
            db.update_balance(self.uid, self.gid, -self.amount, 'loss')
            _house_tx(db, bot_uid, self.gid, self.amount, 'house_gain')
            _record_stats(db, self.uid, self.gid, 0, self.amount)
            new_bal = db.get_balance(self.uid, self.gid)
            profit  = 0
            embed   = discord.Embed(title="✂️ Rock Paper Scissors — You Lost! 💸", color=var.COLOR_LOSE)
            result_line = f"💸 You lost {var.CURRENCY_SYMBOL} **{self.amount:,}**."
            pub_desc = f"✂️ **{name}** lost {var.CURRENCY_SYMBOL} **{self.amount:,}** at Rock Paper Scissors."
        else:
            # Tie — refund
            new_bal = db.get_balance(self.uid, self.gid)
            profit  = 0
            embed   = discord.Embed(title="✂️ Rock Paper Scissors — Tie! 🤝", color=var.COLOR_TIE)
            result_line = "🤝 It's a tie — your bet has been refunded."
            pub_desc = f"✂️ **{name}** tied the bot at Rock Paper Scissors."

        embed.add_field(name=f"You",  value=_MOVES[player_move], inline=True)
        embed.add_field(name="vs",    value="⚔️",                 inline=True)
        embed.add_field(name="Bot",   value=_MOVES[bot_move],     inline=True)
        embed.add_field(name="Result", value=result_line,         inline=False)
        embed.add_field(name="New Balance", value=f"{var.CURRENCY_SYMBOL} {new_bal:,} {var.CURRENCY_NAME}", inline=False)
        if dm_mult > 1.0 and profit > 0:
            embed.add_field(name="💰 Event Bonus", value=f"**{dm_mult}x** multiplier applied!", inline=False)
        embed.set_footer(text=f"Played by {name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

        if interaction.channel:
            color = var.COLOR_WIN if (_BEATS[player_move] == bot_move) else (var.COLOR_LOSE if _BEATS[bot_move] == player_move else var.COLOR_TIE)
            await interaction.channel.send(embed=discord.Embed(description=pub_desc, color=color))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


# ── PvP challenge view ────────────────────────────────────────────────────────

class _PvPChallengeView(discord.ui.View):
    """Accept / Decline buttons shown to the challenged user."""

    def __init__(self, cog: "RPSCog", challenger: discord.Member,
                 challengee: discord.Member, amount: int, gid: str):
        super().__init__(timeout=float(var.CHALLENGE_TIMEOUT))
        self.cog        = cog
        self.challenger = challenger
        self.challengee = challengee
        self.amount     = amount
        self.gid        = gid
        self.resolved   = False
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.challengee.id:
            await interaction.response.send_message(
                "❌ This challenge isn't for you!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.resolved:
            return
        db  = self.cog.db
        uid = str(interaction.user.id)
        err = _validate_bet(db, uid, self.gid, self.amount)
        if err:
            await interaction.response.send_message(f"❌ {err}", ephemeral=True)
            return

        self.resolved = True
        self.stop()

        # Deduct challengee
        db.update_balance(uid, self.gid, -self.amount, 'rps_bet')
        _house_tx(db, str(self.cog.bot.user.id), self.gid, self.amount, 'pvp_hold')

        # Switch to pick view
        pick_view   = _PvPPickView(
            self.cog, self.challenger, self.challengee, self.amount, self.gid
        )
        pick_end_ts = int(time.time()) + var.PICK_TIMEOUT
        embed = discord.Embed(
            title="✂️ Rock Paper Scissors — Pick your move!",
            description=(
                f"Your pick is hidden until both players have chosen.\n"
                f"**Pot:** {var.CURRENCY_SYMBOL} **{self.amount * 2:,}** {var.CURRENCY_NAME}\n"
                f"Picks close <t:{pick_end_ts}:R>"
            ),
            color=var.COLOR_INFO,
        )
        embed.add_field(name=self.challenger.display_name, value="⏳ Picking…", inline=True)
        embed.add_field(name=self.challengee.display_name, value="⏳ Picking…", inline=True)
        embed.set_footer(text=f"{self.challenger.display_name} vs {self.challengee.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        pick_view.pick_end_ts = pick_end_ts
        await interaction.response.edit_message(embed=embed, view=pick_view)
        pick_view.message = interaction.message

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.resolved:
            return
        self.resolved = True
        self.stop()
        self._refund_challenger()
        for item in self.children:
            item.disabled = True
        embed = discord.Embed(
            description=(
                f"❌ **{self.challengee.display_name}** declined the RPS challenge.\n"
                f"{var.CURRENCY_SYMBOL} **{self.amount:,}** refunded to {self.challenger.mention}."
            ),
            color=var.COLOR_ERROR,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        if self.resolved:
            return
        self.resolved = True
        self._refund_challenger()
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                embed = discord.Embed(
                    description=(
                        f"⏰ Challenge expired — **{self.challengee.display_name}** didn't respond.\n"
                        f"{var.CURRENCY_SYMBOL} **{self.amount:,}** refunded to {self.challenger.mention}."
                    ),
                    color=var.COLOR_ERROR,
                )
                await self.message.edit(embed=embed, view=self)
            except Exception:
                pass

    def _refund_challenger(self):
        db      = self.cog.db
        c_uid   = str(self.challenger.id)
        bot_uid = str(self.cog.bot.user.id)
        db.update_balance(c_uid, self.gid, self.amount, 'refund')
        _house_tx(db, bot_uid, self.gid, -self.amount, 'pvp_refund')


# ── PvP pick view ─────────────────────────────────────────────────────────────

class _PvPPickView(discord.ui.View):
    """Rock / Paper / Scissors buttons visible to both PvP players."""

    def __init__(self, cog: "RPSCog", challenger: discord.Member,
                 challengee: discord.Member, amount: int, gid: str):
        super().__init__(timeout=float(var.PICK_TIMEOUT))
        self.cog        = cog
        self.challenger = challenger
        self.challengee = challengee
        self.amount     = amount
        self.gid        = gid
        self.picks: dict[str, str] = {}   # uid -> move
        self.resolved   = False
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        uid = str(interaction.user.id)
        if interaction.user.id not in (self.challenger.id, self.challengee.id):
            await interaction.response.send_message("❌ You're not part of this game!", ephemeral=True)
            return False
        if uid in self.picks:
            await interaction.response.send_message(
                f"✅ You already picked **{_MOVES[self.picks[uid]]}** — waiting for the other player!",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="✊ Rock",     style=discord.ButtonStyle.primary)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_pick(interaction, "rock")

    @discord.ui.button(label="📄 Paper",    style=discord.ButtonStyle.success)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_pick(interaction, "paper")

    @discord.ui.button(label="✂️ Scissors", style=discord.ButtonStyle.danger)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_pick(interaction, "scissors")

    async def _handle_pick(self, interaction: discord.Interaction, move: str):
        uid = str(interaction.user.id)
        self.picks[uid] = move
        await interaction.response.send_message(
            f"✅ You picked **{_MOVES[move]}**! Waiting for the other player…",
            ephemeral=True,
        )
        # Update waiting embed to show one player has picked
        await self._update_waiting_embed()
        if len(self.picks) == 2:
            await self._resolve()

    async def _update_waiting_embed(self):
        """Refresh the public message to show which players have picked (not what)."""
        if not self.message:
            return
        c_uid     = str(self.challenger.id)
        e_uid     = str(self.challengee.id)
        c_status  = "✅ Ready!" if c_uid in self.picks else "⏳ Picking…"
        e_status  = "✅ Ready!" if e_uid in self.picks else "⏳ Picking…"
        end_ts    = getattr(self, 'pick_end_ts', 0)
        timer_str = f"\nPicks close <t:{end_ts}:R>" if end_ts else ""
        embed = discord.Embed(
            title="✂️ Rock Paper Scissors — Pick your move!",
            description=(
                f"Your pick is hidden until both players have chosen.\n"
                f"**Pot:** {var.CURRENCY_SYMBOL} **{self.amount * 2:,}** {var.CURRENCY_NAME}"
                f"{timer_str}"
            ),
            color=var.COLOR_INFO,
        )
        embed.add_field(name=self.challenger.display_name, value=c_status, inline=True)
        embed.add_field(name=self.challengee.display_name, value=e_status, inline=True)
        embed.set_footer(text=f"{self.challenger.display_name} vs {self.challengee.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        try:
            await self.message.edit(embed=embed)
        except Exception:
            pass

    async def _resolve(self):
        if self.resolved:
            return
        self.resolved = True
        self.stop()

        db      = self.cog.db
        bot_uid = str(self.cog.bot.user.id)
        c_uid   = str(self.challenger.id)
        e_uid   = str(self.challengee.id)
        c_move  = self.picks[c_uid]
        e_move  = self.picks[e_uid]

        if c_move == e_move:
            # Tie — refund both
            db.update_balance(c_uid, self.gid, self.amount, 'refund')
            db.update_balance(e_uid, self.gid, self.amount, 'refund')
            _house_tx(db, bot_uid, self.gid, -(self.amount * 2), 'pvp_refund')
            color       = var.COLOR_TIE
            result_line = "🤝 It's a tie! Both players have been refunded."
            winner_member = None
        elif _BEATS[c_move] == e_move:
            # Challenger wins
            db.update_balance(c_uid, self.gid, self.amount * 2, 'rps_win')
            _house_tx(db, bot_uid, self.gid, -(self.amount * 2), 'pvp_payout')
            _record_stats(db, c_uid, self.gid, self.amount, 0)
            _record_stats(db, e_uid, self.gid, 0, self.amount)
            color         = var.COLOR_WIN
            result_line   = f"🏆 **{self.challenger.display_name}** wins {var.CURRENCY_SYMBOL} **{self.amount:,}**!"
            winner_member = self.challenger
        else:
            # Challengee wins
            db.update_balance(e_uid, self.gid, self.amount * 2, 'rps_win')
            _house_tx(db, bot_uid, self.gid, -(self.amount * 2), 'pvp_payout')
            _record_stats(db, e_uid, self.gid, self.amount, 0)
            _record_stats(db, c_uid, self.gid, 0, self.amount)
            color         = var.COLOR_WIN
            result_line   = f"🏆 **{self.challengee.display_name}** wins {var.CURRENCY_SYMBOL} **{self.amount:,}**!"
            winner_member = self.challengee

        embed = discord.Embed(title="✂️ Rock Paper Scissors — Result!", color=color)
        embed.add_field(name=self.challenger.display_name, value=_MOVES[c_move], inline=True)
        embed.add_field(name="vs",                         value="⚔️",            inline=True)
        embed.add_field(name=self.challengee.display_name, value=_MOVES[e_move], inline=True)
        embed.add_field(name="Result", value=result_line,  inline=False)
        embed.set_footer(text=f"{self.challenger.display_name} vs {self.challengee.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()

        for item in self.children:
            item.disabled = True

        if self.message:
            try:
                await self.message.edit(embed=embed, view=self)
            except Exception:
                pass

    async def on_timeout(self):
        if self.resolved:
            return
        self.resolved = True
        self.stop()

        db      = self.cog.db
        bot_uid = str(self.cog.bot.user.id)
        c_uid   = str(self.challenger.id)
        e_uid   = str(self.challengee.id)

        # Refund everyone regardless of who picked
        db.update_balance(c_uid, self.gid, self.amount, 'refund')
        db.update_balance(e_uid, self.gid, self.amount, 'refund')
        _house_tx(db, bot_uid, self.gid, -(self.amount * 2), 'pvp_refund')

        for item in self.children:
            item.disabled = True

        if self.message:
            try:
                embed = discord.Embed(
                    description=(
                        f"⏰ Time's up! Not all players picked in time.\n"
                        f"Both players refunded {var.CURRENCY_SYMBOL} **{self.amount:,}**."
                    ),
                    color=var.COLOR_ERROR,
                )
                await self.message.edit(embed=embed, view=self)
            except Exception:
                pass


# ── Cog ───────────────────────────────────────────────────────────────────────

class RPSCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    @app_commands.command(name="rps", description="Play Rock Paper Scissors — against the bot or challenge another user!")
    @app_commands.describe(
        amount="Amount to bet",
        user="User to challenge (leave empty to play against the bot)",
    )
    async def rps(
        self,
        interaction: discord.Interaction,
        amount: int,
        user: discord.Member | None = None,
    ):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)
        self.db.ensure_user(uid, gid, interaction.user.display_name)

        if user is not None and user.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ You can't challenge yourself!", ephemeral=True
            )
            return

        if user is not None and user.bot:
            await interaction.response.send_message(
                "❌ You can't challenge a bot — use `/rps` without a user to play against me!",
                ephemeral=True,
            )
            return

        err = _validate_bet(self.db, uid, gid, amount)
        if err:
            await interaction.response.send_message(
                embed=discord.Embed(title="❌ Invalid Bet", description=err, color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        if user is None:
            await self._vs_bot(interaction, uid, gid, amount)
        else:
            await self._vs_user(interaction, uid, gid, amount, user)

    async def _vs_bot(self, interaction: discord.Interaction, uid: str, gid: str, amount: int):
        view = _BotPickView(self, uid, gid, amount)
        embed = discord.Embed(
            title="✂️ Rock Paper Scissors — Pick your move!",
            description=f"**Bet:** {var.CURRENCY_SYMBOL} **{amount:,}** {var.CURRENCY_NAME}",
            color=var.COLOR_INFO,
        )
        embed.set_footer(text=f"Played by {interaction.user.display_name} · {var.SERVER_NAME}")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def _vs_user(
        self,
        interaction: discord.Interaction,
        uid: str,
        gid: str,
        amount: int,
        target: discord.Member,
    ):
        bot_uid = str(self.bot.user.id)
        self.db.ensure_user(uid, gid, interaction.user.display_name)

        # Deduct challenger immediately
        self.db.update_balance(uid, gid, -amount, 'rps_bet')
        _house_tx(self.db, bot_uid, gid, amount, 'pvp_hold')

        view = _PvPChallengeView(self, interaction.user, target, amount, gid)
        end_ts = int(time.time()) + var.CHALLENGE_TIMEOUT
        embed  = discord.Embed(
            title="✂️ Rock Paper Scissors Challenge!",
            description=(
                f"{target.mention}, **{interaction.user.display_name}** challenges you to RPS!\n\n"
                f"**Bet:** {var.CURRENCY_SYMBOL} **{amount:,}** {var.CURRENCY_NAME} each\n"
                f"**Winner takes:** {var.CURRENCY_SYMBOL} **{amount * 2:,}**\n\n"
                f"Expires <t:{end_ts}:R>"
            ),
            color=var.COLOR_INFO,
        )
        embed.set_footer(text=f"Challenge by {interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()
        view.message = msg


async def setup(bot: commands.Bot):
    await bot.add_cog(RPSCog(bot))
    print("✅ Casino/RockPaperScissors cog loaded successfully")
