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
from utils.config_loader import load_config

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
    available: list[str] = []
    pool: dict = {}

    # ── Text-based types (single random quote as subject) ─────────────────────
    rows = db.execute(
        "SELECT id, quote_text, quoted_user_name, quoter_user_name "
        "FROM quotes WHERE guild_id = ? ORDER BY RANDOM() LIMIT 1",
        (gid,),
    )
    if rows:
        quote_id, text, quoted_name, quoter_name = rows[0]
        pool["main"] = (quote_id, text, quoted_name, quoter_name)

        w = db.execute(
            "SELECT DISTINCT quoted_user_name FROM quotes "
            "WHERE guild_id = ? AND quoted_user_name != ? ORDER BY RANDOM() LIMIT 3",
            (gid, quoted_name),
        )
        if len(w) >= 3:
            pool["wrong_said"] = [r[0] for r in w]
            available.append("who_said")

        w = db.execute(
            "SELECT DISTINCT quoter_user_name FROM quotes "
            "WHERE guild_id = ? AND quoter_user_name != ? ORDER BY RANDOM() LIMIT 3",
            (gid, quoter_name),
        )
        if len(w) >= 3:
            pool["wrong_quoted"] = [r[0] for r in w]
            available.append("who_quoted")

        words = text.split()
        if len(words) >= 6:
            w = db.execute(
                "SELECT quote_text FROM quotes "
                "WHERE guild_id = ? AND id != ? ORDER BY RANDOM() LIMIT 6",
                (gid, quote_id),
            )
            if len(w) >= 3:
                pool["wrong_complete"] = [r[0] for r in w]
                available.append("complete")

    # ── GIF type (separate quote that must have a gif_url) ────────────────────
    gif_rows = db.execute(
        "SELECT id, quote_text, gif_url, quoted_user_name, quoter_user_name "
        "FROM quotes WHERE guild_id = ? "
        "AND (gif_url LIKE '%tenor.com%' OR gif_url LIKE '%giphy.com%') "
        "ORDER BY RANDOM() LIMIT 1",
        (gid,),
    )
    if gif_rows:
        gq_id, gq_text, gif_url, gq_qname, gq_rname = gif_rows[0]
        w = db.execute(
            "SELECT quote_text FROM quotes "
            "WHERE guild_id = ? AND id != ? ORDER BY RANDOM() LIMIT 6",
            (gid, gq_id),
        )
        if len(w) >= 3:
            pool["gif"] = (gq_id, gq_text, gif_url, gq_qname, gq_rname, [r[0] for r in w])
            available.append("gif")

    if not available:
        return None

    q_type = random.choice(available)
    quote_id, text, quoted_name, quoter_name = pool.get("main", (None, None, None, None))

    if q_type == "who_said":
        choices = [quoted_name] + pool["wrong_said"]
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
        choices = [quoter_name] + pool["wrong_quoted"]
        random.shuffle(choices)
        return {
            "type":     "who_quoted",
            "question": "📸 Who submitted this quote?",
            "display":  _truncate(f'"{text}"\n\n*— {quoted_name}*', 512),
            "correct":  quoter_name,
            "choices":  choices,
            "reveal":   f'Submitted by **{quoter_name}** · Said by **{quoted_name}**',
        }

    if q_type == "complete":
        words      = text.split()
        mid        = len(words) // 2
        first_half = " ".join(words[:mid])
        correct_lbl = _truncate(" ".join(words[mid:]))

        wrong_ends: list[str] = []
        for wtext in pool["wrong_complete"]:
            wwords = wtext.split()
            wmid   = max(1, len(wwords) // 2)
            ending = " ".join(wwords[wmid:]) if len(wwords) >= 4 else wtext
            lbl    = _truncate(ending)
            if lbl != correct_lbl and lbl not in wrong_ends:
                wrong_ends.append(lbl)
            if len(wrong_ends) == 3:
                break

        if len(wrong_ends) < 3:
            if "who_said" in available:
                choices = [quoted_name] + pool["wrong_said"]
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

    # gif
    gq_id, gq_text, gif_url, gq_qname, gq_rname, wrong_texts = pool["gif"]
    correct_lbl = _truncate(gq_text)
    seen        = {correct_lbl}
    wrong_lbls: list[str] = []
    for wt in wrong_texts:
        lbl = _truncate(wt)
        if lbl not in seen:
            seen.add(lbl)
            wrong_lbls.append(lbl)
        if len(wrong_lbls) == 3:
            break

    if len(wrong_lbls) < 3:
        if "who_said" in available:
            choices = [quoted_name] + pool["wrong_said"]
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

    choices = [correct_lbl] + wrong_lbls
    random.shuffle(choices)
    return {
        "type":     "gif",
        "question": "🖼️ Which quote does this GIF belong to?",
        "display":  "Match the GIF above to the correct quote.",
        "gif_url":  gif_url,
        "correct":  correct_lbl,
        "choices":  choices,
        "reveal":   f'Said by **{gq_qname}** · Submitted by **{gq_rname}**',
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
                self.stop()  # end immediately — winner found
            await interaction.response.send_message(
                "✅ Correct! You won!" if (correct and self.first_correct == uid)
                else "❌ Wrong!",
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
        self._loop_task:  asyncio.Task | None = None
        self._next_event_ts: int | None = None

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
        shared = load_config().get('quiz_announcement_channel_id')
        if shared:
            ch = self.bot.get_channel(int(shared))
            if ch:
                return ch
        cid = _load_settings().get("quiz_channel_id") or var.EVENT_CHANNEL_ID
        return self.bot.get_channel(int(cid)) if cid else None

    # ── Auto-loop ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self):
        if self._loop_task is None or self._loop_task.done():
            self._loop_task = asyncio.create_task(self._event_loop())

    def cog_unload(self):
        if self._loop_task:
            self._loop_task.cancel()
        if self._event_task:
            self._event_task.cancel()

    async def _event_loop(self):
        await self.bot.wait_until_ready()
        while True:
            cfg   = _load_settings()
            min_m = cfg.get("interval_min", var.EVENT_INTERVAL_MIN)
            max_m = cfg.get("interval_max", var.EVENT_INTERVAL_MAX)
            wait  = random.randint(min_m, max_m)
            self._next_event_ts = int(time.time()) + wait * 60
            log.info("QuotesEvent: next event in %d minutes", wait)
            await asyncio.sleep(wait * 60)
            self._next_event_ts = None
            if not self.event_active:
                await self._start_event()

    def set_interval(self, min_minutes: int, max_minutes: int):
        data = _load_settings()
        data["interval_min"] = min_minutes
        data["interval_max"] = max_minutes
        _save_settings(data)
        if not self.event_active:
            if self._loop_task and not self._loop_task.done():
                self._loop_task.cancel()
            self._loop_task = asyncio.create_task(self._event_loop())

    # Called by /startevent's "Quote Quiz" choice in casino_event.py
    async def start_from_startevent(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        err = await self._start_event()
        if err:
            await interaction.followup.send(
                embed=discord.Embed(description=f"❌ {err}", color=var.COLOR_LOSE),
                ephemeral=True,
            )
        else:
            await interaction.followup.send("✅ Quote Quiz event started!", ephemeral=True)

    async def _run_quiz_event(self, channel: discord.TextChannel):
        gid     = str(channel.guild.id)
        sym     = var.CURRENCY_SYMBOL
        bot_uid = str(self.bot.user.id) if self.bot.user else ""

        question = _build_question(self.db, gid)
        if question is None:
            await channel.send(embed=discord.Embed(
                description="⚠️ Not enough quotes in the database to run a quiz.",
                color=var.COLOR_LOSE,
            ))
            self.event_active = False
            return

        view  = _QuizEventView(question, timeout=var.EVENT_QUESTION_TIMEOUT)
        embed = discord.Embed(title="🧠 Quote Quiz!", color=var.COLOR_QUIZ)
        embed.add_field(name=question["question"], value=question["display"], inline=False)
        embed.set_footer(
            text=(
                f"First correct wins — instant: {sym} {var.EVENT_REWARD_FIRST:,} → "
                f"last second: {sym} {var.EVENT_REWARD_MIN:,} · {var.EVENT_QUESTION_TIMEOUT}s · {var.SERVER_NAME}"
            )
        )
        embed.timestamp = datetime.utcnow()

        gif_url = question.get("gif_url")
        msg = await channel.send(
            content=gif_url if gif_url else None,
            embed=embed,
            view=view,
        )
        await view.wait()   # returns early if stop() called (winner found), or on timeout
        view.disable_all()

        winner_uid = view.first_correct

        if winner_uid:
            frac   = max(0.0, 1.0 - view.first_correct_sec / var.EVENT_QUESTION_TIMEOUT)
            reward = int(var.EVENT_REWARD_MIN + (var.EVENT_REWARD_FIRST - var.EVENT_REWARD_MIN) * frac)
            self.db.ensure_user(winner_uid, gid, winner_uid)
            self.db.update_balance(winner_uid, gid, reward, "quiz_event_win")
            if bot_uid:
                self.db.ensure_user(bot_uid, gid, "House")
                self.db.update_balance(bot_uid, gid, -reward, "house_payout")
            try:
                user = await self.bot.fetch_user(int(winner_uid))
                name = user.display_name
            except Exception:
                name = f"<@{winner_uid}>"
            result_line = f"🥇 **{name}** answered in **{view.first_correct_sec:.1f}s** → +{sym} {reward:,}"
        else:
            result_line = "❌ Nobody got it right in time!"

        result_embed = discord.Embed(
            title="Answer Revealed",
            description=(
                f"**{question['question']}**\n"
                f"✔ **{question['correct']}**\n"
                f"*{question['reveal']}*\n\n"
                f"{result_line}"
            ),
            color=var.COLOR_WIN if winner_uid else var.COLOR_LOSE,
        )
        result_embed.timestamp = datetime.utcnow()
        await msg.edit(embed=result_embed, view=view)

        self.event_active = False

    async def _start_event(self) -> str | None:
        if self.event_active:
            return "A quiz event is already running."
        channel = self._get_event_channel()
        if channel is None:
            return "No event channel configured. Use `/set_eventannouncement_channel` first."
        self.event_active = True
        self._event_task  = asyncio.create_task(self._run_quiz_event(channel))
        return None

    # ── Commands ───────────────────────────────────────────────────────────────

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
