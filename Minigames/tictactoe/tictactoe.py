import discord
from discord.ext import commands
from discord import app_commands
import random
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('ttt_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")

_PLAYER = 'X'
_BOT    = 'O'
_EMPTY  = ' '
_WINS   = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]


# ============================================================================
# BOT AI  (minimax with configurable mistake chance)
# ============================================================================

def _winner(board: list) -> str | None:
    for a, b, c in _WINS:
        if board[a] == board[b] == board[c] != _EMPTY:
            return board[a]
    return None


def _minimax(board: list, is_bot_turn: bool, depth: int = 0) -> int:
    w = _winner(board)
    if w == _BOT:           return 10 - depth
    if w == _PLAYER:        return depth - 10
    if _EMPTY not in board: return 0

    moves = [i for i, c in enumerate(board) if c == _EMPTY]
    if is_bot_turn:
        best = -99
        for i in moves:
            board[i] = _BOT
            best = max(best, _minimax(board, False, depth + 1))
            board[i] = _EMPTY
        return best
    else:
        best = 99
        for i in moves:
            board[i] = _PLAYER
            best = min(best, _minimax(board, True, depth + 1))
            board[i] = _EMPTY
        return best


def _bot_move(board: list) -> int:
    empty = [i for i, c in enumerate(board) if c == _EMPTY]
    if not empty:
        return -1
    if var.BOT_MISTAKE_CHANCE > 0 and random.random() < var.BOT_MISTAKE_CHANCE:
        return random.choice(empty)
    best_val  = -99
    best_move = empty[0]
    for i in empty:
        board[i] = _BOT
        val = _minimax(board, False)
        board[i] = _EMPTY
        if val > best_val:
            best_val  = val
            best_move = i
    return best_move


# ============================================================================
# HELPERS
# ============================================================================

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


# ============================================================================
# VIEW  (9-button 3×3 grid)
# ============================================================================

class TicTacToeView(discord.ui.View):

    def __init__(self, cog, interaction: discord.Interaction, bet: int):
        super().__init__(timeout=var.BUTTON_TIMEOUT)
        self.cog         = cog
        self.interaction = interaction
        self.bet         = bet
        self.board       = [_EMPTY] * 9
        self.uid         = str(interaction.user.id)
        self.gid         = str(interaction.guild_id)
        self.finished    = False

        for i in range(9):
            btn = discord.ui.Button(label='​', row=i // 3, style=discord.ButtonStyle.secondary)
            btn.callback = self._make_callback(i)
            self.add_item(btn)

    def _make_callback(self, idx: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != int(self.uid):
                await interaction.response.send_message("This isn't your game!", ephemeral=True)
                return
            await self._handle_move(interaction, idx)
        return callback

    def _refresh_buttons(self, winning_line: tuple | None = None):
        for idx, btn in enumerate(self.children):
            cell      = self.board[idx]
            btn.label = var.PLAYER_EMOJI if cell == _PLAYER else var.BOT_EMOJI if cell == _BOT else '​'
            btn.style = (
                discord.ButtonStyle.danger    if cell == _PLAYER else
                discord.ButtonStyle.primary   if cell == _BOT    else
                discord.ButtonStyle.secondary
            )
            btn.disabled = self.finished or cell != _EMPTY
            if winning_line and idx in winning_line:
                btn.style = discord.ButtonStyle.success

    def _build_embed(self, status: str = "Your turn — pick a square") -> discord.Embed:
        embed = discord.Embed(
            title=f"{var.PLAYER_EMOJI} You  vs  Bot {var.BOT_EMOJI}",
            description=status,
            color=var.COLOR_PLAYING,
        )
        embed.set_footer(text=(
            f"{self.interaction.user.display_name} · "
            f"Bet: {var.CURRENCY_SYMBOL} {self.bet:,} · {var.SERVER_NAME}"
        ))
        embed.timestamp = datetime.utcnow()
        return embed

    async def _handle_move(self, interaction: discord.Interaction, idx: int):
        if self.board[idx] != _EMPTY:
            await interaction.response.send_message("That square is already taken!", ephemeral=True)
            return

        self.board[idx] = _PLAYER
        if _winner(self.board) == _PLAYER:
            await self._end_game(interaction, 'win')
            return
        if _EMPTY not in self.board:
            await self._end_game(interaction, 'draw')
            return

        bot_idx = _bot_move(self.board)
        self.board[bot_idx] = _BOT
        if _winner(self.board) == _BOT:
            await self._end_game(interaction, 'loss')
            return
        if _EMPTY not in self.board:
            await self._end_game(interaction, 'draw')
            return

        self._refresh_buttons()
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    async def _end_game(self, interaction: discord.Interaction, result: str):
        self.finished = True
        winning_line  = None

        if result == 'win':
            for line in _WINS:
                if all(self.board[i] == _PLAYER for i in line):
                    winning_line = line
                    break
        elif result == 'loss':
            for line in _WINS:
                if all(self.board[i] == _BOT for i in line):
                    winning_line = line
                    break

        self._refresh_buttons(winning_line=winning_line)

        db      = self.cog.db
        sym     = var.CURRENCY_SYMBOL
        bot_uid = str(interaction.client.user.id)

        if result == 'win':
            payout  = int(self.bet * var.WIN_MULTIPLIER)
            profit  = payout - self.bet
            db.update_balance(self.uid, self.gid, payout, 'win')
            _house_tx(db, bot_uid, self.gid, -payout, 'house_payout')
            _record_stats(db, self.uid, self.gid, won=profit)
            new_bal = db.get_balance(self.uid, self.gid)
            embed = discord.Embed(
                title="🎉 You won!",
                description=f"Won **{sym} {profit:,}** {var.CURRENCY_NAME}!",
                color=var.COLOR_WIN,
            )
            embed.add_field(name="Payout",  value=f"{sym} {payout:,}",  inline=True)
            embed.add_field(name="Balance", value=f"{sym} {new_bal:,}", inline=True)

        elif result == 'draw':
            db.update_balance(self.uid, self.gid, self.bet, 'refund')
            _house_tx(db, bot_uid, self.gid, -self.bet, 'house_payout')
            new_bal = db.get_balance(self.uid, self.gid)
            embed = discord.Embed(
                title="🤝 It's a draw!",
                description=f"Bet of **{sym} {self.bet:,}** returned.",
                color=var.COLOR_DRAW,
            )
            embed.add_field(name="Balance", value=f"{sym} {new_bal:,}", inline=True)

        else:
            _record_stats(db, self.uid, self.gid, lost=self.bet)
            new_bal = db.get_balance(self.uid, self.gid)
            embed = discord.Embed(
                title="❌ You lost!",
                description=f"Lost **{sym} {self.bet:,}** {var.CURRENCY_NAME}.",
                color=var.COLOR_LOSE,
            )
            embed.add_field(name="Lost",    value=f"{sym} {self.bet:,}", inline=True)
            embed.add_field(name="Balance", value=f"{sym} {new_bal:,}", inline=True)

        embed.set_footer(text=f"{self.interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        if self.finished:
            return
        self.finished = True
        for btn in self.children:
            btn.disabled = True
        _record_stats(self.cog.db, self.uid, self.gid, lost=self.bet)
        embed = discord.Embed(
            title="⏰ Timed out!",
            description=f"Lost {var.CURRENCY_SYMBOL} **{self.bet:,}** — game abandoned.",
            color=var.COLOR_LOSE,
        )
        embed.set_footer(text=f"{self.interaction.user.display_name} · {var.SERVER_NAME}")
        try:
            await self.interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            pass


# ============================================================================
# COG
# ============================================================================

class TicTacToeCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    async def cog_load(self):
        for col in ('games_won', 'games_lost'):
            try:
                self.db.execute(f"ALTER TABLE casino_stats ADD COLUMN {col} INTEGER DEFAULT 0")
            except Exception:
                pass

    @app_commands.command(
        name="tictactoe",
        description="Play Tic-Tac-Toe vs the bot — win 2×, draw returns bet, loss loses it!",
    )
    @app_commands.describe(amount="Amount to bet")
    async def tictactoe(self, interaction: discord.Interaction, amount: int):
        uid  = str(interaction.user.id)
        gid  = str(interaction.guild_id)
        name = interaction.user.display_name

        self.db.ensure_user(uid, gid, name)

        if amount < var.MIN_BET:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Minimum bet is {var.CURRENCY_SYMBOL} **{var.MIN_BET:,}**.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
        if var.MAX_BET > 0 and amount > var.MAX_BET:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Maximum bet is {var.CURRENCY_SYMBOL} **{var.MAX_BET:,}**.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
        balance = self.db.get_balance(uid, gid)
        if balance < amount:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Not enough {var.CURRENCY_NAME}. Balance: {var.CURRENCY_SYMBOL} {balance:,}",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )

        bot_uid = str(interaction.client.user.id)
        self.db.update_balance(uid, gid, -amount, 'bet')
        _house_tx(self.db, bot_uid, gid, amount, 'house_gain')

        view = TicTacToeView(self, interaction, amount)
        await interaction.response.send_message(
            embed=view._build_embed(),
            view=view,
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(TicTacToeCog(bot))
    log.info("✅ Minigames/TicTacToe cog loaded")
