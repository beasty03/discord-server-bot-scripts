import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('qe_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")
_SETTINGS_FILE = Path(__file__).parent / "quotes_event_settings.json"

_MAX_LABEL = 70


def _load_settings() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            return json.loads(_SETTINGS_FILE.read_text("utf-8"))
        except Exception:
            pass
    return {}


def _save_settings(data: dict):
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2), "utf-8")


def _truncate(text: str, max_len: int = _MAX_LABEL) -> str:
    return text[:max_len - 1] + "…" if len(text) > max_len else text


def _build_question(db, gid: str) -> dict | None:
    rows = db.execute(
        "SELECT id, quote_text, quoted_user_name, quoter_user_name "
        "FROM quotes WHERE guild_id = ? ORDER BY RANDOM() LIMIT 1",
        (gid,),
    )
    if not rows:
        return None
    quote_id, text, quoted_name, quoter_name = rows[0]

    available: list[str] = []
    wrong_said: list[str] = []
    wrong_quoted: list[str] = []
    wrong_complete: list[str] = []

    # ── who_said: need 3 other distinct quoted_user_names ─────────────────────
    w = db.execute(
        "SELECT DISTINCT quoted_user_name FROM quotes "
        "WHERE guild_id = ? AND quoted_user_name != ? "
        "ORDER BY RANDOM() LIMIT 3",
        (gid, quoted_name),
    )
    if len(w) >= 3:
        wrong_said = [r[0] for r in w]
        available.append("who_said")

    # ── who_quoted: need 3 other distinct quoter_user_names ───────────────────
    w = db.execute(
        "SELECT DISTINCT quoter_user_name FROM quotes "
        "WHERE guild_id = ? AND quoter_user_name != ? "
        "ORDER BY RANDOM() LIMIT 3",
        (gid, quoter_name),
    )
    if len(w) >= 3:
        wrong_quoted = [r[0] for r in w]
        available.append("who_quoted")

    # ── complete: quote must have 6+ words + 3 other quotes for endings ───────
    words = text.split()
    if len(words) >= 6:
        w = db.execute(
            "SELECT quote_text FROM quotes "
            "WHERE guild_id = ? AND id != ? "
            "ORDER BY RANDOM() LIMIT 6",
            (gid, quote_id),
        )
        if len(w) >= 3:
            wrong_complete = [r[0] for r in w]
            available.append("complete")

    if not available:
        return None

    q_type = random.choice(available)

    if q_type == "who_said":
        choices = [quoted_name] + wrong_said
        random.shuffle(choices)
        return {
            "type":     "who_said",
            "question": "🎙️ Who said this?",
            "display":  _truncate(f'"{text}"', 512),
            "correct":  quoted_name,
            "choices":  choices,
            "reveal":   f'Said by **{quoted_name}** · Submitted by **{quoter_name}**',
        }

    if q_type == "who_quoted":
        choices = [quoter_name] + wrong_quoted
        random.shuffle(choices)
        return {
            "type":     "who_quoted",
            "question": "📸 Who submitted this quote?",
            "display":  _truncate(f'"{text}"\n\n*— {quoted_name}*', 512),
            "correct":  quoter_name,
            "choices":  choices,
            "reveal":   f'Submitted by **{quoter_name}** · Said by **{quoted_name}**',
        }

    # complete
    mid         = len(words) // 2
    first_half  = " ".join(words[:mid])
    correct_end = " ".join(words[mid:])
    correct_lbl = _truncate(correct_end)

    wrong_ends: list[str] = []
    for (wtext,) in wrong_complete:
        wwords = wtext.split()
        wmid   = max(1, len(wwords) // 2)
        ending = " ".join(wwords[wmid:]) if len(wwords) >= 4 else wtext
        lbl    = _truncate(ending)
        if lbl != correct_lbl and lbl not in wrong_ends:
            wrong_ends.append(lbl)
        if len(wrong_ends) == 3:
            break

    if len(wrong_ends) < 3:
        # Fall back to who_said if we couldn't make 3 distinct endings
        if "who_said" in available:
            choices = [quoted_name] + wrong_said
            random.shuffle(choices)
            return {
                "type":     "who_said",
                "question": "🎙️ Who said this?",
                "display":  _truncate(f'"{text}"', 512),
                "correct":  quoted_name,
                "choices":  choices,
                "reveal":   f'Said by **{quoted_name}** · Submitted by **{quoter_name}**',
            }
        return None

    choices = [correct_lbl] + wrong_ends
    random.shuffle(choices)
    return {
        "type":     "complete",
        "question": "✍️ Complete the quote:",
        "display":  f'"{first_half}…"',
        "correct":  correct_lbl,
        "choices":  choices,
        "reveal":   f'Full quote: "{text}" — **{quoted_name}**',
    }


# ── Event quiz view ────────────────────────────────────────────────────────────

class _QuizEventView(discord.ui.View):

    def __init__(self, question: dict, timeout: float):
        super().__init__(timeout=timeout)
        self.question           = question
        self.answered:          dict[str, str] = {}   # uid -> chosen label
        self.first_correct:     str | None     = None
        self.first_correct_sec: float          = 0.0  # seconds after question posted
        self._start             = time.monotonic()
        self._build_buttons()

    def _build_buttons(self):
        for i, choice in enumerate(self.question["choices"]):
            btn = discord.ui.Button(
                label=_truncate(choice),
                style=discord.ButtonStyle.primary,
                custom_id=f"quizevent_{i}",
                row=i // 2,
            )
            btn.callback = self._make_callback(choice)
            self.add_item(btn)

    def _make_callback(self, choice: str):
        async def cb(interaction: discord.Interaction):
            uid = str(interaction.user.id)
            if uid in self.answered:
                await interaction.response.send_message("You already answered!", ephemeral=True)
                return
            self.answered[uid] = choice
            correct = choice == self.question["correct"]
            if correct and self.first_correct is None:
                self.first_correct     = uid
                self.first_correct_sec = time.monotonic() - self._start
            await interaction.response.send_message(
                "✅ Correct! You're first!" if (correct and self.first_correct == uid)
                else ("✅ Correct — but someone was faster!" if correct else "❌ Wrong!"),
                ephemeral=True,
            )
        return cb

    def disable_all(self):
        for item in self.children:
            item.disabled = True
            if not hasattr(item, "label"):
                continue
            if item.label == _truncate(self.question["correct"]):
                item.style = discord.ButtonStyle.success
            else:
                item.style = discord.ButtonStyle.secondary


# ── Cog ────────────────────────────────────────────────────────────────────────

class QuotesEventCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot          = bot
        self.db           = ForgeDB.get()
        self.event_active = False
        self._event_task: asyncio.Task | None = None

    async def cog_load(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id           TEXT NOT NULL,
                quoted_user_id     TEXT NOT NULL,
                quoted_user_name   TEXT NOT NULL,
                quoted_user_avatar TEXT,
                quoter_user_id     TEXT NOT NULL,
                quoter_user_name   TEXT NOT NULL,
                quote_text         TEXT NOT NULL,
                embed_message_id   TEXT,
                gif_url            TEXT,
                channel_id         TEXT NOT NULL,
                created_at         TEXT NOT NULL
            )
        """)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_event_channel(self) -> discord.TextChannel | None:
        cid = _load_settings().get("quiz_channel_id")
        if cid:
            ch = self.bot.get_channel(int(cid))
            if ch:
                return ch
        return None

    async def _run_quiz_event(self, channel: discord.TextChannel, n_questions: int):
        gid    = str(channel.guild.id)
        scores: dict[str, int] = {}
        names:  dict[str, str] = {}
        sym    = var.CURRENCY_SYMBOL
        bot_uid = str(self.bot.user.id) if self.bot.user else ""

        await channel.send(embed=discord.Embed(
            title="🧠 Quote Quiz Event Starting!",
            description=(
                f"**{n_questions} question{'s' if n_questions != 1 else ''}** "
                f"· {var.EVENT_QUESTION_TIMEOUT}s per question\n\n"
                f"Only the **first correct answer** wins!\n"
                f"🥇 Instant: {sym} **{var.EVENT_REWARD_FIRST:,}** → "
                f"⏱️ Last second: {sym} **{var.EVENT_REWARD_MIN:,}**"
            ),
            color=var.COLOR_EVENT,
        ))
        await asyncio.sleep(3)

        for q_num in range(1, n_questions + 1):
            question = _build_question(self.db, gid)
            if question is None:
                await channel.send(embed=discord.Embed(
                    description="⚠️ Not enough quotes in the database — ending early.",
                    color=var.COLOR_LOSE,
                ))
                break

            view  = _QuizEventView(question, timeout=var.EVENT_QUESTION_TIMEOUT)
            embed = discord.Embed(
                title=f"❓ Question {q_num}/{n_questions}",
                color=var.COLOR_QUIZ,
            )
            embed.add_field(name=question["question"], value=question["display"], inline=False)
            embed.set_footer(text=f"{var.EVENT_QUESTION_TIMEOUT}s to answer · {var.SERVER_NAME}")
            embed.timestamp = datetime.utcnow()

            msg = await channel.send(embed=embed, view=view)
            await asyncio.sleep(var.EVENT_QUESTION_TIMEOUT)
            view.stop()
            view.disable_all()

            winner_uid = view.first_correct

            # Time-based reward: linear decay from EVENT_REWARD_FIRST → EVENT_REWARD_MIN
            if winner_uid:
                frac   = max(0.0, 1.0 - view.first_correct_sec / var.EVENT_QUESTION_TIMEOUT)
                reward = int(var.EVENT_REWARD_MIN + (var.EVENT_REWARD_FIRST - var.EVENT_REWARD_MIN) * frac)
                self.db.ensure_user(winner_uid, gid, winner_uid)
                self.db.update_balance(winner_uid, gid, reward, "quiz_event_win")
                if bot_uid:
                    self.db.ensure_user(bot_uid, gid, "House")
                    self.db.update_balance(bot_uid, gid, -reward, "house_payout")
                scores[winner_uid] = scores.get(winner_uid, 0) + reward

            # Resolve display names and build result lines
            result_lines: list[str] = []
            if winner_uid:
                try:
                    user = await self.bot.fetch_user(int(winner_uid))
                    name = user.display_name
                except Exception:
                    name = f"<@{winner_uid}>"
                names[winner_uid] = name
                answered_in = f"{view.first_correct_sec:.1f}s"
                result_lines.append(f"🥇 **{name}** answered in **{answered_in}** → +{sym} {reward:,}")

            if not result_lines:
                result_lines.append("❌ Nobody got it right in time!")

            result_embed = discord.Embed(
                title=f"Q{q_num} — Answer Revealed",
                description=(
                    f"**{question['question']}**\n"
                    f"✔ **{question['correct']}**\n"
                    f"*{question['reveal']}*\n\n"
                    + "\n".join(result_lines)
                ),
                color=var.COLOR_WIN if winner_uid else var.COLOR_LOSE,
            )
            result_embed.timestamp = datetime.utcnow()
            await msg.edit(embed=result_embed, view=view)

            if q_num < n_questions:
                await asyncio.sleep(3)

        # Final scoreboard
        if scores:
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            medals = ["🥇", "🥈", "🥉"]
            lines  = []
            for i, (uid, total) in enumerate(sorted_scores[:10]):
                name   = names.get(uid, f"<@{uid}>")
                prefix = medals[i] if i < 3 else f"**{i + 1}.**"
                lines.append(f"{prefix} **{name}** — {sym} {total:,}")
            await channel.send(embed=discord.Embed(
                title="🏆 Quiz Event — Final Scores",
                description="\n".join(lines),
                color=var.COLOR_EVENT,
            ))
        else:
            await channel.send(embed=discord.Embed(
                title="Quiz Event Over",
                description="Nobody scored any points!",
                color=var.COLOR_LOSE,
            ))

        self.event_active = False

    async def _start_event(self, n_questions: int) -> str | None:
        if self.event_active:
            return "A quiz event is already running."
        channel = self._get_event_channel()
        if channel is None:
            return "No event channel configured. Use `/set_quiz_channel` first."
        if n_questions < 1:
            return "Need at least 1 question."
        self.event_active = True
        self._event_task  = asyncio.create_task(self._run_quiz_event(channel, n_questions))
        return None

    # ── Commands ───────────────────────────────────────────────────────────────

    @app_commands.command(
        name="start_quiz_event",
        description="Start a public Quote Quiz event in the event channel.",
    )
    @app_commands.describe(questions="Number of questions (default 5)")
    @app_commands.default_permissions(administrator=True)
    async def start_quiz_event(self, interaction: discord.Interaction, questions: int = 5):
        await interaction.response.defer(ephemeral=True)
        err = await self._start_event(questions)
        if err:
            await interaction.followup.send(
                embed=discord.Embed(description=f"❌ {err}", color=var.COLOR_LOSE),
                ephemeral=True,
            )
        else:
            await interaction.followup.send("✅ Quiz event started!", ephemeral=True)

    @app_commands.command(
        name="set_quiz_channel",
        description="Set the channel where quote quiz events are posted.",
    )
    @app_commands.describe(channel="Channel to post quiz events in")
    @app_commands.default_permissions(administrator=True)
    async def set_quiz_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        data = _load_settings()
        data["quiz_channel_id"] = str(channel.id)
        _save_settings(data)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Quiz events will be posted in {channel.mention}.",
                color=var.COLOR_WIN,
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(QuotesEventCog(bot))
    log.info("✅ Events/QuotesEvent cog loaded")
