import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
import logging
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('hangman_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB
from utils.config_loader import load_config, save_config

log = logging.getLogger("launcher")

# ============================================================================
# HANGMAN STAGES  (0 wrong → 6 wrong)
# ============================================================================

_STAGES = [
    "```\n  +---+\n  |   |\n      |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n  |   |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|   |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n /    |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n / \\  |\n      |\n=========```",
]


async def _fetch_word() -> str:
    """Fetch a random word from Wordnik. Falls back to the static list on any error."""
    if not var.WORDNIK_API_KEY:
        return random.choice(var.WORDS).upper()
    try:
        params = {
            "hasDictionaryDef":  "true",
            "includePartOfSpeech": var.WORDNIK_PART_OF_SPEECH,
            "minCorpusCount":    var.WORDNIK_MIN_CORPUS,
            "minLength":         var.WORDNIK_MIN_LENGTH,
            "maxLength":         var.WORDNIK_MAX_LENGTH,
            "api_key":           var.WORDNIK_API_KEY,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                var.WORDNIK_API_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    word = data.get("word", "").upper()
                    if word.isalpha() and var.WORDNIK_MIN_LENGTH <= len(word) <= var.WORDNIK_MAX_LENGTH:
                        return word
    except Exception:
        log.warning("Hangman: Wordnik fetch failed — using static word list")
    return random.choice(var.WORDS).upper()


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
# API KEY SETUP  (shared with Wordle — whichever cog loads first registers the command)
# ============================================================================

class ApiKeyModal(discord.ui.Modal, title="Set Wordnik API Key"):
    key = discord.ui.TextInput(
        label="Wordnik API Key",
        placeholder="Paste your key here — only you can see this",
        min_length=1,
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction):
        cfg = load_config()
        cfg["wordnik_api_key"] = self.key.value.strip()
        save_config(cfg)
        await interaction.response.send_message(
            embed=discord.Embed(
                description="✅ Wordnik API key saved. Restart the bot for it to take effect.",
                color=0x57F287,
            ),
            ephemeral=True,
        )


def _make_set_api_key_cmd():
    @app_commands.command(
        name="set_api_key",
        description="Set an external API key used by bot features.",
    )
    @app_commands.describe(service="Which service to configure")
    @app_commands.choices(service=[
        app_commands.Choice(name="Wordnik — Hangman & Wordle word source", value="wordnik"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def set_api_key(interaction: discord.Interaction, service: str):
        await interaction.response.send_modal(ApiKeyModal())
    return set_api_key


# ============================================================================
# MODAL
# ============================================================================

class LetterModal(discord.ui.Modal, title="Guess a Letter"):
    letter = discord.ui.TextInput(
        label="Enter a single letter (A–Z)",
        min_length=1,
        max_length=1,
        placeholder="e.g. E",
    )

    def __init__(self, view: "HangmanView"):
        super().__init__()
        self._view = view

    async def on_submit(self, interaction: discord.Interaction):
        await self._view.process_guess(interaction, self.letter.value.upper())


# ============================================================================
# VIEW
# ============================================================================

class HangmanView(discord.ui.View):

    def __init__(self, cog, interaction: discord.Interaction, bet: int, word: str):
        super().__init__(timeout=var.BUTTON_TIMEOUT)
        self.cog         = cog
        self.interaction = interaction
        self.bet         = bet
        self.word        = word.upper()
        self.uid         = str(interaction.user.id)
        self.gid         = str(interaction.guild_id)
        self.guessed:    set[str] = set()
        self.wrong:      set[str] = set()
        self.finished    = False

    @property
    def _display_word(self) -> str:
        return "  ".join(c if c in self.guessed else "\_" for c in self.word)

    @property
    def _won(self) -> bool:
        return all(c in self.guessed for c in self.word)

    @property
    def _lost(self) -> bool:
        return len(self.wrong) >= var.MAX_WRONG

    def _build_embed(self) -> discord.Embed:
        wrong_count = len(self.wrong)
        remaining   = var.MAX_WRONG - wrong_count

        if self._won:
            title = "✅ You guessed it!"
            color = var.COLOR_WIN
        elif self._lost:
            title = "💀 Game over!"
            color = var.COLOR_LOSE
        else:
            title = f"🎯 Hangman — {remaining} guess{'es' if remaining != 1 else ''} left"
            color = var.COLOR_PLAYING

        correct_str = "  ".join(sorted(self.guessed - self.wrong)) or "—"
        wrong_str   = "  ".join(sorted(self.wrong)) or "—"

        embed = discord.Embed(title=title, color=color)
        embed.description = (
            f"{_STAGES[wrong_count]}\n"
            f"**{self._display_word}**\n\n"
            f"🟩 Correct: `{correct_str}`\n"
            f"🟥 Wrong:   `{wrong_str}`"
        )
        embed.set_footer(
            text=f"{self.interaction.user.display_name} · Bet: {var.CURRENCY_SYMBOL} {self.bet:,} · {var.SERVER_NAME}"
        )
        embed.timestamp = datetime.utcnow()
        return embed

    # ── Buttons ───────────────────────────────────────────────────────────────

    @discord.ui.button(label="🔤 Guess a letter", style=discord.ButtonStyle.primary)
    async def guess_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != int(self.uid):
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        await interaction.response.send_modal(LetterModal(self))

    @discord.ui.button(label="🏳️ Give up", style=discord.ButtonStyle.danger)
    async def giveup_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != int(self.uid):
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        # Reveal all letters so the display shows the full word
        for c in self.word:
            self.guessed.add(c)
        await self._end_game(interaction, won=False, gave_up=True)

    # ── Game logic ────────────────────────────────────────────────────────────

    async def process_guess(self, interaction: discord.Interaction, letter: str):
        if not letter.isalpha():
            await interaction.response.send_message("Enter a single letter A–Z.", ephemeral=True)
            return
        if letter in self.guessed:
            await interaction.response.send_message(f"You already guessed **{letter}**!", ephemeral=True)
            return

        self.guessed.add(letter)
        if letter not in self.word:
            self.wrong.add(letter)

        if self._won:
            await self._end_game(interaction, won=True)
        elif self._lost:
            # Reveal the word on loss
            for c in self.word:
                self.guessed.add(c)
            await self._end_game(interaction, won=False)
        else:
            await interaction.response.edit_message(embed=self._build_embed(), view=self)

    async def _end_game(self, interaction: discord.Interaction, won: bool, gave_up: bool = False):
        self.finished = True
        for item in self.children:
            item.disabled = True

        db      = self.cog.db
        sym     = var.CURRENCY_SYMBOL
        bot_uid = str(interaction.client.user.id)

        if won:
            payout  = int(self.bet * var.WIN_MULTIPLIER)
            profit  = payout - self.bet
            ev_mult = getattr(interaction.client, 'multiplier_event_mult', None) or 1.0
            if ev_mult > 1.0:
                profit = int(profit * ev_mult)
                payout = self.bet + profit
            db.update_balance(self.uid, self.gid, payout, 'win')
            _house_tx(db, bot_uid, self.gid, -payout, 'house_payout')
            _record_stats(db, self.uid, self.gid, won=profit)
            new_bal = db.get_balance(self.uid, self.gid)

            embed = discord.Embed(
                title="✅ You guessed it!",
                description=f"The word was **{self.word}**!\n\nWon {sym} **{profit:,}** {var.CURRENCY_NAME}!",
                color=var.COLOR_WIN,
            )
            embed.add_field(name="Payout",        value=f"{sym} {payout:,}",         inline=True)
            embed.add_field(name="Balance",        value=f"{sym} {new_bal:,}",        inline=True)
            embed.add_field(name="Wrong guesses",  value=str(len(self.wrong)),        inline=True)
            if ev_mult > 1.0:
                embed.add_field(name="💰 Event bonus", value=f"**{ev_mult}×** applied!", inline=False)
        else:
            _record_stats(db, self.uid, self.gid, lost=self.bet)
            new_bal = db.get_balance(self.uid, self.gid)

            title = "🏳️ You gave up!" if gave_up else "💀 Game over!"
            embed = discord.Embed(
                title=title,
                description=f"The word was **{self.word}**.\n\nLost {sym} **{self.bet:,}** {var.CURRENCY_NAME}.",
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
        for item in self.children:
            item.disabled = True
        _record_stats(self.cog.db, self.uid, self.gid, lost=self.bet)
        embed = discord.Embed(
            title="⏰ Timed out!",
            description=f"The word was **{self.word}**.\nLost {var.CURRENCY_SYMBOL} **{self.bet:,}**.",
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

class HangmanCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot                 = bot
        self.db                  = ForgeDB.get()
        self._owns_set_api_key   = False

    async def cog_load(self):
        for col in ('games_won', 'games_lost'):
            try:
                self.db.execute(f"ALTER TABLE casino_stats ADD COLUMN {col} INTEGER DEFAULT 0")
            except Exception:
                pass
        if self.bot.tree.get_command("set_api_key") is None:
            self._owns_set_api_key = True
            self.bot.tree.add_command(_make_set_api_key_cmd())

    def cog_unload(self):
        if self._owns_set_api_key:
            self.bot.tree.remove_command("set_api_key")

    async def _check_api_key(self, guild: discord.Guild):
        if not hasattr(self.bot, '_wordnik_warned_guilds'):
            self.bot._wordnik_warned_guilds = set()
        if guild.id in self.bot._wordnik_warned_guilds:
            return
        if load_config().get("wordnik_api_key"):
            return
        bot_logs = discord.utils.get(guild.text_channels, name="bot-logs")
        if bot_logs:
            try:
                await bot_logs.send(embed=discord.Embed(
                    title="⚠️ Wordnik API Key Missing",
                    description=(
                        "Required for `/hangman` and `/wordle` to fetch real words.\n\n"
                        "**→** `/set_api_key service:Wordnik`"
                    ),
                    color=0xED4245,
                ))
                self.bot._wordnik_warned_guilds.add(guild.id)
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self._check_api_key(guild)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self._check_api_key(guild)

    @app_commands.command(
        name="hangman",
        description="Guess the hidden word letter by letter — don't get hanged!",
    )
    @app_commands.describe(amount="Amount to bet")
    async def hangman(self, interaction: discord.Interaction, amount: int):
        uid  = str(interaction.user.id)
        gid  = str(interaction.guild_id)
        name = interaction.user.display_name

        self.db.ensure_user(uid, gid, name)

        if amount < var.MIN_BET:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Minimum bet is {var.CURRENCY_SYMBOL} **{var.MIN_BET:,} {var.CURRENCY_NAME}**.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
        if var.MAX_BET > 0 and amount > var.MAX_BET:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Maximum bet is {var.CURRENCY_SYMBOL} **{var.MAX_BET:,} {var.CURRENCY_NAME}**.",
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

        word = await _fetch_word()
        view = HangmanView(self, interaction, amount, word)

        await interaction.response.send_message(
            embed=view._build_embed(),
            view=view,
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(HangmanCog(bot))
    log.info("✅ Minigames/Hangman cog loaded")
