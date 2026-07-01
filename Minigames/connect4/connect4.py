import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('c4_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")

_PLAYER = 'X'
_BOT    = 'O'
_EMPTY  = ' '


# ============================================================================
# BOARD LOGIC
# ============================================================================

def _new_board() -> list[list[str]]:
    return [[_EMPTY] * var.COLS for _ in range(var.ROWS)]


def _get_drop_row(board: list, col: int) -> int | None:
    """Return the lowest empty row in this column (pieces fall down), or None if full."""
    for row in range(var.ROWS - 1, -1, -1):
        if board[row][col] == _EMPTY:
            return row
    return None


def _check_win(board: list, piece: str) -> bool:
    rows, cols = var.ROWS, var.COLS
    # Horizontal
    for r in range(rows):
        for c in range(cols - 3):
            if all(board[r][c + i] == piece for i in range(4)):
                return True
    # Vertical
    for c in range(cols):
        for r in range(rows - 3):
            if all(board[r + i][c] == piece for i in range(4)):
                return True
    # Diagonal ↘
    for r in range(rows - 3):
        for c in range(cols - 3):
            if all(board[r + i][c + i] == piece for i in range(4)):
                return True
    # Diagonal ↗
    for r in range(3, rows):
        for c in range(cols - 3):
            if all(board[r - i][c + i] == piece for i in range(4)):
                return True
    return False


def _is_full(board: list) -> bool:
    return all(board[0][c] != _EMPTY for c in range(var.COLS))


def _valid_cols(board: list) -> list[int]:
    return [c for c in range(var.COLS) if board[0][c] == _EMPTY]


# ============================================================================
# BOT AI  (win → block → positional scoring)
# ============================================================================

def _score_window(window: list, piece: str, opp: str) -> int:
    score = 0
    if window.count(piece) == 4:
        score += 100
    elif window.count(piece) == 3 and window.count(_EMPTY) == 1:
        score += 5
    elif window.count(piece) == 2 and window.count(_EMPTY) == 2:
        score += 2
    if window.count(opp) == 3 and window.count(_EMPTY) == 1:
        score -= 4
    return score


def _score_position(board: list, piece: str) -> int:
    opp   = _PLAYER if piece == _BOT else _BOT
    score = 0
    rows, cols = var.ROWS, var.COLS

    # Center column preference
    center = [board[r][cols // 2] for r in range(rows)]
    score += center.count(piece) * 3

    for r in range(rows):
        for c in range(cols - 3):
            score += _score_window([board[r][c + i] for i in range(4)], piece, opp)
    for c in range(cols):
        for r in range(rows - 3):
            score += _score_window([board[r + i][c] for i in range(4)], piece, opp)
    for r in range(rows - 3):
        for c in range(cols - 3):
            score += _score_window([board[r + i][c + i] for i in range(4)], piece, opp)
    for r in range(3, rows):
        for c in range(cols - 3):
            score += _score_window([board[r - i][c + i] for i in range(4)], piece, opp)

    return score


def _bot_move(board: list) -> int:
    valid = _valid_cols(board)
    if not valid:
        return -1

    # 1. Win immediately
    for col in valid:
        row = _get_drop_row(board, col)
        board[row][col] = _BOT
        if _check_win(board, _BOT):
            board[row][col] = _EMPTY
            return col
        board[row][col] = _EMPTY

    # 2. Block player from winning
    for col in valid:
        row = _get_drop_row(board, col)
        board[row][col] = _PLAYER
        if _check_win(board, _PLAYER):
            board[row][col] = _EMPTY
            return col
        board[row][col] = _EMPTY

    # 3. Best scored position
    best_score = -float('inf')
    best_col   = valid[len(valid) // 2]
    for col in valid:
        row = _get_drop_row(board, col)
        board[row][col] = _BOT
        score = _score_position(board, _BOT)
        board[row][col] = _EMPTY
        if score > best_score:
            best_score = score
            best_col   = col

    return best_col


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


def _render_board(board: list) -> str:
    header = ''.join(var.COL_LABELS)
    rows   = []
    for r in range(var.ROWS):
        row = ''
        for c in range(var.COLS):
            cell = board[r][c]
            row += var.PLAYER_EMOJI if cell == _PLAYER else var.BOT_EMOJI if cell == _BOT else var.EMPTY_EMOJI
        rows.append(row)
    return header + '\n' + '\n'.join(rows)


# ============================================================================
# VIEW
# ============================================================================

class Connect4View(discord.ui.View):

    def __init__(self, cog, interaction: discord.Interaction, bet: int):
        super().__init__(timeout=var.BUTTON_TIMEOUT)
        self.cog         = cog
        self.interaction = interaction
        self.bet         = bet
        self.board       = _new_board()
        self.uid         = str(interaction.user.id)
        self.gid         = str(interaction.guild_id)
        self.finished    = False

        # 7 column buttons across 2 rows (5 + 2)
        for col in range(var.COLS):
            btn = discord.ui.Button(
                label=str(col + 1),
                row=0 if col < 5 else 1,
                style=discord.ButtonStyle.primary,
            )
            btn.callback = self._make_col_callback(col)
            self.add_item(btn)

        give_up = discord.ui.Button(label="🏳️ Give up", style=discord.ButtonStyle.danger, row=1)
        give_up.callback = self._give_up_callback
        self.add_item(give_up)

    def _make_col_callback(self, col: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != int(self.uid):
                await interaction.response.send_message("This isn't your game!", ephemeral=True)
                return
            await self._handle_drop(interaction, col)
        return callback

    async def _give_up_callback(self, interaction: discord.Interaction):
        if interaction.user.id != int(self.uid):
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        await self._end_game(interaction, 'loss', gave_up=True)

    def _disable_full_cols(self):
        col_btns = [item for item in self.children if item.label.isdigit()]
        for idx, btn in enumerate(col_btns):
            if _get_drop_row(self.board, idx) is None:
                btn.disabled = True

    def _disable_all(self):
        for item in self.children:
            item.disabled = True

    def _build_embed(self, status: str = "Your turn — pick a column") -> discord.Embed:
        embed = discord.Embed(
            title=f"{var.PLAYER_EMOJI} You  vs  Bot {var.BOT_EMOJI}",
            description=_render_board(self.board) + f"\n\n*{status}*",
            color=var.COLOR_PLAYING,
        )
        embed.set_footer(text=(
            f"{self.interaction.user.display_name} · "
            f"Bet: {var.CURRENCY_SYMBOL} {self.bet:,} · {var.SERVER_NAME}"
        ))
        embed.timestamp = datetime.utcnow()
        return embed

    async def _handle_drop(self, interaction: discord.Interaction, col: int):
        row = _get_drop_row(self.board, col)
        if row is None:
            await interaction.response.send_message("That column is full!", ephemeral=True)
            return

        self.board[row][col] = _PLAYER
        if _check_win(self.board, _PLAYER):
            await self._end_game(interaction, 'win')
            return
        if _is_full(self.board):
            await self._end_game(interaction, 'draw')
            return

        bot_col = _bot_move(self.board)
        bot_row = _get_drop_row(self.board, bot_col)
        self.board[bot_row][bot_col] = _BOT
        if _check_win(self.board, _BOT):
            await self._end_game(interaction, 'loss')
            return
        if _is_full(self.board):
            await self._end_game(interaction, 'draw')
            return

        self._disable_full_cols()
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    async def _end_game(self, interaction: discord.Interaction, result: str, gave_up: bool = False):
        self.finished = True
        self._disable_all()

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
                title="🎉 You got 4 in a row!",
                description=_render_board(self.board) + f"\nWon **{sym} {profit:,}** {var.CURRENCY_NAME}!",
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
                description=_render_board(self.board) + f"\nBet of **{sym} {self.bet:,}** returned.",
                color=var.COLOR_DRAW,
            )
            embed.add_field(name="Balance", value=f"{sym} {new_bal:,}", inline=True)

        else:
            title = "🏳️ You gave up!" if gave_up else "❌ The bot got 4 in a row!"
            _record_stats(db, self.uid, self.gid, lost=self.bet)
            new_bal = db.get_balance(self.uid, self.gid)
            embed = discord.Embed(
                title=title,
                description=_render_board(self.board) + f"\nLost **{sym} {self.bet:,}** {var.CURRENCY_NAME}.",
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
        self._disable_all()
        _record_stats(self.cog.db, self.uid, self.gid, lost=self.bet)
        embed = discord.Embed(
            title="⏰ Timed out!",
            description=_render_board(self.board) + f"\nLost {var.CURRENCY_SYMBOL} **{self.bet:,}** — game abandoned.",
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

class Connect4Cog(commands.Cog):

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
        name="connect4",
        description="Drop pieces to get 4 in a row vs the bot — win 2×, draw returns bet, loss loses it!",
    )
    @app_commands.describe(amount="Amount to bet")
    async def connect4(self, interaction: discord.Interaction, amount: int):
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

        view = Connect4View(self, interaction, amount)
        await interaction.response.send_message(
            embed=view._build_embed(),
            view=view,
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Connect4Cog(bot))
    log.info("✅ Minigames/Connect4 cog loaded")
