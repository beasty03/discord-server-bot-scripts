import asyncio
import importlib.util as _ilu
import logging
import random
from collections import Counter
from datetime import datetime
from itertools import combinations
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

_spec = _ilu.spec_from_file_location('poker_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")

# ── Card constants ────────────────────────────────────────────────────────────

_SUITS   = ['♠', '♥', '♦', '♣']
_RANKS   = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
_RANK_V  = {r: i + 2 for i, r in enumerate(_RANKS)}

HAND_NAMES = [
    'High Card', 'One Pair', 'Two Pair', 'Three of a Kind',
    'Straight', 'Flush', 'Full House', 'Four of a Kind',
    'Straight Flush', 'Royal Flush',
]


def _new_deck() -> list:
    deck = [(_RANK_V[r], s) for r in _RANKS for s in _SUITS]
    random.shuffle(deck)
    return deck


def _card_str(card) -> str:
    rn = {14: 'A', 13: 'K', 12: 'Q', 11: 'J'}
    return f"{rn.get(card[0], str(card[0]))}{card[1]}"


def _hand_str(cards) -> str:
    return '  '.join(_card_str(c) for c in cards)


# ── Hand evaluator ────────────────────────────────────────────────────────────

def _eval_five(cards) -> tuple:
    ranks = sorted([c[0] for c in cards], reverse=True)
    suits = [c[1] for c in cards]
    is_flush    = len(set(suits)) == 1
    rank_set    = set(ranks)
    is_straight = len(rank_set) == 5 and ranks[0] - ranks[4] == 4
    is_wheel    = rank_set == {14, 2, 3, 4, 5}
    if is_wheel:
        is_straight = True
        ranks = [5, 4, 3, 2, 1]
    counts  = Counter(ranks)
    groups  = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
    freq    = [g[1] for g in groups]
    ordered = [g[0] for g in groups]
    if is_straight and is_flush:
        return (9 if ranks[0] == 14 and not is_wheel else 8, tuple(ranks))
    if freq[0] == 4:         return (7, tuple(ordered))
    if freq[:2] == [3, 2]:   return (6, tuple(ordered))
    if is_flush:             return (5, tuple(ranks))
    if is_straight:          return (4, tuple(ranks))
    if freq[0] == 3:         return (3, tuple(ordered))
    if freq[:2] == [2, 2]:   return (2, tuple(ordered))
    if freq[0] == 2:         return (1, tuple(ordered))
    return (0, tuple(ranks))


def best_hand(all_cards: list) -> tuple:
    if len(all_cards) < 5:
        return (0, (0,), 'High Card', list(all_cards))
    best_score = None
    best_combo = None
    for combo in combinations(all_cards, 5):
        score = _eval_five(combo)
        if best_score is None or score > best_score:
            best_score = score
            best_combo = combo
    rank_int, tb = best_score
    return rank_int, tb, HAND_NAMES[rank_int], list(best_combo)


# ── DB helpers ────────────────────────────────────────────────────────────────

def _record_stats(db, uid: str, gid: str, won: int = 0, lost: int = 0):
    db.execute(
        """INSERT INTO casino_stats
               (user_id, guild_id, games_played, games_won, games_lost, total_won, total_lost)
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


# ── "See my cards" view — attached to each phase message ─────────────────────

class _CardsView(discord.ui.View):
    """Single ephemeral-button view that lets any player peek at their hole cards."""

    def __init__(self, player_uids: set, holes: dict, timeout: float = 600.0):
        super().__init__(timeout=timeout)
        self.player_uids = set(player_uids)
        self.holes       = holes

    @discord.ui.button(label="🃏 My Cards", style=discord.ButtonStyle.secondary)
    async def cards_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        if uid not in self.player_uids:
            await interaction.response.send_message("❌ You're not in this game!", ephemeral=True)
            return
        cards = self.holes.get(uid, [])
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🃏 Your Hole Cards",
                description=f"**{_hand_str(cards)}**",
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )


# ── Join view ─────────────────────────────────────────────────────────────────

class _JoinView(discord.ui.View):

    def __init__(self, cog: "PokerCog", creator_uid: str, gid: str, ante: int, channel):
        super().__init__(timeout=float(var.JOIN_WINDOW))
        self.cog         = cog
        self.creator_uid = creator_uid
        self.gid         = gid
        self.ante        = ante
        self.channel     = channel
        self.players: dict[str, str] = {}
        self.started     = False
        self.message: discord.Message | None = None

    @discord.ui.button(label="🃏 Join", style=discord.ButtonStyle.success)
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid  = str(interaction.user.id)
        name = interaction.user.display_name
        if uid in self.players:
            await interaction.response.send_message("✅ You're already at the table!", ephemeral=True)
            return
        if len(self.players) >= var.MAX_PLAYERS:
            await interaction.response.send_message(
                f"❌ Table is full ({var.MAX_PLAYERS} players max).", ephemeral=True
            )
            return
        db = self.cog.db
        db.ensure_user(uid, self.gid, name)
        bal = db.get_balance(uid, self.gid)
        if bal < self.ante:
            await interaction.response.send_message(
                f"❌ You need {var.CURRENCY_SYMBOL} **{self.ante:,}** to join. You have **{bal:,}**.",
                ephemeral=True,
            )
            return
        self.players[uid] = name
        await interaction.response.send_message(
            f"✅ You're in! **{len(self.players)}** player(s) at the table.", ephemeral=True
        )
        await self._update_embed()

    @discord.ui.button(label="▶️ Force Start", style=discord.ButtonStyle.primary)
    async def force_start_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.creator_uid:
            await interaction.response.send_message("❌ Only the host can force-start!", ephemeral=True)
            return
        if len(self.players) < var.MIN_PLAYERS:
            await interaction.response.send_message(
                f"❌ Need at least **{var.MIN_PLAYERS}** players to start.", ephemeral=True
            )
            return
        if self.started:
            return
        self.started = True
        self.stop()
        await interaction.response.defer()
        asyncio.create_task(
            self.cog._run_game(dict(self.players), self.gid, self.ante, self.channel, self.message)
        )

    async def on_timeout(self):
        if self.started:
            return
        if len(self.players) < var.MIN_PLAYERS:
            self.cog._active.discard(self.gid)
            for item in self.children:
                item.disabled = True
            if self.message:
                try:
                    embed = discord.Embed(
                        title="🃏 Poker — Cancelled",
                        description=(
                            f"Not enough players joined "
                            f"(need **{var.MIN_PLAYERS}**, got **{len(self.players)}**)."
                        ),
                        color=var.COLOR_ERROR,
                    )
                    await self.message.edit(embed=embed, view=self)
                except Exception:
                    pass
            return
        self.started = True
        asyncio.create_task(
            self.cog._run_game(dict(self.players), self.gid, self.ante, self.channel, self.message)
        )

    async def _update_embed(self):
        if not self.message:
            return
        player_lines = "\n".join(f"• {n}" for n in self.players.values()) or "*None yet*"
        embed = discord.Embed(
            title="🃏 Poker — Join the Table!",
            description=(
                f"**Ante:** {var.CURRENCY_SYMBOL} **{self.ante:,}** {var.CURRENCY_NAME} per player\n"
                f"**Min players:** {var.MIN_PLAYERS} · **Max:** {var.MAX_PLAYERS}\n\n"
                f"**At the table ({len(self.players)}):**\n{player_lines}\n\n"
                f"Game starts when the host force-starts or the timer expires."
            ),
            color=var.COLOR_INFO,
        )
        embed.set_footer(text=f"{var.SERVER_NAME} · {var.JOIN_WINDOW}s join window")
        try:
            await self.message.edit(embed=embed)
        except Exception:
            pass


# ── Pre-flop view ─────────────────────────────────────────────────────────────

class _PreFlopView(discord.ui.View):
    """Check / Fold / My Cards buttons shown on the public message before community cards."""

    def __init__(self, player_uids: set, holes: dict, timeout: float):
        super().__init__(timeout=timeout)
        self.player_uids = set(player_uids)
        self.holes       = holes
        self.checked: set[str] = set()
        self.folded:  set[str] = set()

    def _acted(self) -> int:
        return len(self.checked) + len(self.folded)

    @discord.ui.button(label="✅ Check — Stay In", style=discord.ButtonStyle.success)
    async def check_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        if uid not in self.player_uids:
            await interaction.response.send_message("❌ You're not in this game!", ephemeral=True)
            return
        if uid in self.checked or uid in self.folded:
            await interaction.response.send_message("✅ You've already made your decision.", ephemeral=True)
            return
        self.checked.add(uid)
        await interaction.response.send_message("✅ You stay in — good luck!", ephemeral=True)
        if self._acted() >= len(self.player_uids):
            self.stop()

    @discord.ui.button(label="❌ Fold — Lose Ante", style=discord.ButtonStyle.danger)
    async def fold_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        if uid not in self.player_uids:
            await interaction.response.send_message("❌ You're not in this game!", ephemeral=True)
            return
        if uid in self.checked or uid in self.folded:
            await interaction.response.send_message("✅ You've already made your decision.", ephemeral=True)
            return
        remaining = len(self.player_uids) - len(self.folded)
        if remaining <= 1:
            await interaction.response.send_message(
                "❌ You can't fold — you'd be the last player!", ephemeral=True
            )
            return
        self.folded.add(uid)
        await interaction.response.send_message(
            "❌ You fold. Your ante stays in the pot.", ephemeral=True
        )
        if self._acted() >= len(self.player_uids):
            self.stop()

    @discord.ui.button(label="🃏 My Cards", style=discord.ButtonStyle.secondary)
    async def cards_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        if uid not in self.player_uids:
            await interaction.response.send_message("❌ You're not in this game!", ephemeral=True)
            return
        cards = self.holes.get(uid, [])
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🃏 Your Hole Cards",
                description=f"**{_hand_str(cards)}**",
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )

    async def on_timeout(self):
        for uid in self.player_uids:
            if uid not in self.checked and uid not in self.folded:
                self.checked.add(uid)


# ── Cog ───────────────────────────────────────────────────────────────────────

class PokerCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot     = bot
        self.db      = ForgeDB.get()
        self._active: set[str] = set()

    @app_commands.command(
        name="poker",
        description="Start a multiplayer Texas Hold'em poker game — last hand standing wins the pot!",
    )
    @app_commands.describe(ante="Buy-in amount every player pays to join")
    async def poker(self, interaction: discord.Interaction, ante: int):
        gid = str(interaction.guild_id)
        uid = str(interaction.user.id)

        if gid in self._active:
            await interaction.response.send_message(
                "❌ A poker game is already running in this server!", ephemeral=True
            )
            return

        if ante < var.MIN_BET:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Ante Too Low",
                    description=f"Minimum ante is {var.CURRENCY_SYMBOL} **{var.MIN_BET:,}** {var.CURRENCY_NAME}.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        if var.MAX_BET > 0 and ante > var.MAX_BET:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Ante Too High",
                    description=f"Maximum ante is {var.CURRENCY_SYMBOL} **{var.MAX_BET:,}** {var.CURRENCY_NAME}.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        self.db.ensure_user(uid, gid, interaction.user.display_name)
        bal = self.db.get_balance(uid, gid)
        if bal < ante:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        f"You need {var.CURRENCY_SYMBOL} **{ante:,}** to host. "
                        f"You have **{bal:,}**."
                    ),
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        self._active.add(gid)

        view = _JoinView(self, uid, gid, ante, interaction.channel)
        view.players[uid] = interaction.user.display_name

        embed = discord.Embed(
            title="🃏 Poker — Join the Table!",
            description=(
                f"**Ante:** {var.CURRENCY_SYMBOL} **{ante:,}** {var.CURRENCY_NAME} per player\n"
                f"**Min players:** {var.MIN_PLAYERS} · **Max:** {var.MAX_PLAYERS}\n\n"
                f"**At the table (1):**\n• {interaction.user.display_name}\n\n"
                f"Game starts when the host force-starts or the **{var.JOIN_WINDOW}s** timer expires."
            ),
            color=var.COLOR_INFO,
        )
        embed.set_footer(text=f"Hosted by {interaction.user.display_name} · {var.SERVER_NAME}")
        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()
        view.message = msg

    # ── Game runner ───────────────────────────────────────────────────────────

    async def _run_game(
        self,
        players: dict[str, str],
        gid: str,
        ante: int,
        channel,
        msg: discord.Message,
    ):
        db      = self.db
        bot_uid = str(self.bot.user.id)
        try:
            await self._play(players, gid, ante, channel, msg, db, bot_uid)
        except Exception:
            log.exception("Poker error in guild %s", gid)
            try:
                for uid in players:
                    db.update_balance(uid, gid, ante, 'refund')
                    _house_tx(db, bot_uid, gid, -ante, 'pvp_refund')
                await channel.send(embed=discord.Embed(
                    title="❌ Poker Error",
                    description="Something went wrong. Antes have been refunded.",
                    color=var.COLOR_ERROR,
                ))
            except Exception:
                pass
        finally:
            self._active.discard(gid)

    async def _play(self, players, gid, ante, channel, msg, db, bot_uid):
        uids = list(players.keys())

        # Deduct antes
        for uid, name in players.items():
            db.ensure_user(uid, gid, name)
            db.update_balance(uid, gid, -ante, 'poker_ante')
            _house_tx(db, bot_uid, gid, ante, 'pvp_hold')
        pot = ante * len(uids)

        # Deal
        deck      = _new_deck()
        holes     = {uid: [deck.pop(), deck.pop()] for uid in uids}
        community = [deck.pop() for _ in range(5)]

        # Pre-flop: Check / Fold / My Cards
        preflop_embed = discord.Embed(
            title="🃏 Pre-Flop — Check or Fold?",
            description=(
                f"**Pot:** {var.CURRENCY_SYMBOL} **{pot:,}** · **{len(uids)} players**\n"
                f"Press **🃏 My Cards** to see your hole cards privately.\n"
                f"You have **{var.PREFLOP_TIMEOUT}s** to decide."
            ),
            color=var.COLOR_FLOP,
        )
        preflop_embed.set_footer(text=f"{var.SERVER_NAME} · No response = auto-check")
        pf_view = _PreFlopView(set(uids), holes, float(var.PREFLOP_TIMEOUT))
        try:
            await msg.edit(embed=preflop_embed, view=pf_view)
        except Exception:
            pass
        await pf_view.wait()

        remaining = {uid: name for uid, name in players.items() if uid not in pf_view.folded}

        if not remaining:
            for uid in uids:
                db.update_balance(uid, gid, ante, 'refund')
                _house_tx(db, bot_uid, gid, -ante, 'pvp_refund')
            await channel.send(embed=discord.Embed(
                description="All players folded — antes refunded.", color=var.COLOR_ERROR
            ))
            return

        # One player left after folds
        if len(remaining) == 1:
            w_uid, w_name = next(iter(remaining.items()))
            db.update_balance(w_uid, gid, pot, 'poker_win')
            _house_tx(db, bot_uid, gid, -pot, 'pvp_payout')
            _record_stats(db, w_uid, gid, pot - ante, 0)
            for uid in pf_view.folded:
                _record_stats(db, uid, gid, 0, ante)
            folds = len(pf_view.folded)
            embed = discord.Embed(
                title="🃏 Last One Standing!",
                description=(
                    f"🏆 **{w_name}** wins {var.CURRENCY_SYMBOL} **{pot:,}** — "
                    f"everyone else folded! *({folds} fold{'s' if folds != 1 else ''})*"
                ),
                color=var.COLOR_WIN,
            )
            try:
                await msg.edit(embed=embed, view=None)
            except Exception:
                await channel.send(embed=embed)
            return

        # Reveal community cards — each message includes a "My Cards" button
        remaining_uids = set(remaining.keys())
        flop   = community[:3]
        turn_c = community[3]
        river  = community[4]
        await asyncio.sleep(var.DEAL_DELAY)

        # FLOP
        flop_embed = discord.Embed(
            title="🃏 Flop",
            description=(
                f"**{_hand_str(flop)}**\n\n"
                f"**Pot:** {var.CURRENCY_SYMBOL} **{pot:,}** · **{len(remaining)} players**"
            ),
            color=var.COLOR_FLOP,
        )
        flop_embed.set_footer(text=var.SERVER_NAME)
        try:
            await msg.edit(embed=flop_embed, view=_CardsView(remaining_uids, holes))
        except Exception:
            pass
        await asyncio.sleep(var.REVEAL_DELAY)

        # TURN
        turn_embed = discord.Embed(
            title="🃏 Turn",
            description=(
                f"Flop: **{_hand_str(flop)}**\n"
                f"Turn: **{_card_str(turn_c)}**\n\n"
                f"**Pot:** {var.CURRENCY_SYMBOL} **{pot:,}** · **{len(remaining)} players**"
            ),
            color=var.COLOR_TURN,
        )
        await channel.send(embed=turn_embed, view=_CardsView(remaining_uids, holes))
        await asyncio.sleep(var.REVEAL_DELAY)

        # RIVER
        all_comm = flop + [turn_c, river]
        river_embed = discord.Embed(
            title="🃏 River",
            description=(
                f"**{_hand_str(all_comm)}**\n\n"
                f"**Pot:** {var.CURRENCY_SYMBOL} **{pot:,}** · **{len(remaining)} players**"
            ),
            color=var.COLOR_RIVER,
        )
        await channel.send(embed=river_embed, view=_CardsView(remaining_uids, holes))
        await asyncio.sleep(var.REVEAL_DELAY)

        # SHOWDOWN
        results = []
        for uid, name in remaining.items():
            rank_int, tiebreak, hand_name, best_5 = best_hand(holes[uid] + all_comm)
            results.append({
                'uid': uid, 'name': name,
                'hole': holes[uid], 'hand_name': hand_name,
                'best_5': best_5, 'score': (rank_int, tiebreak),
            })
        results.sort(key=lambda r: r['score'], reverse=True)
        best_score = results[0]['score']
        winners    = [r for r in results if r['score'] == best_score]
        losers     = [r for r in results if r['score'] != best_score]

        split    = pot // len(winners)
        leftover = pot % len(winners)
        dm_mult  = getattr(self.bot, 'multiplier_event_mult', None) or 1.0
        for i, w in enumerate(winners):
            prize = split + (leftover if i == 0 else 0)
            if dm_mult > 1.0:
                prize = int(prize * dm_mult)
            db.update_balance(w['uid'], gid, prize, 'poker_win')
            _house_tx(db, bot_uid, gid, -prize, 'pvp_payout')
            _record_stats(db, w['uid'], gid, prize - ante, 0)
        for r in losers:
            _record_stats(db, r['uid'], gid, 0, ante)
        for uid in pf_view.folded:
            _record_stats(db, uid, gid, 0, ante)

        showdown = discord.Embed(title="🃏 Showdown!", color=var.COLOR_WIN)
        showdown.add_field(
            name="Community Cards",
            value=_hand_str(all_comm),
            inline=False,
        )
        for r in results:
            is_w = r['score'] == best_score
            showdown.add_field(
                name=f"{'🏆 ' if is_w else ''}{r['name']}",
                value=f"Hole: **{_hand_str(r['hole'])}**\n*{r['hand_name']}*",
                inline=True,
            )
        if pf_view.folded:
            fold_names = ", ".join(players[u] for u in pf_view.folded)
            showdown.add_field(name="Folded Pre-Flop", value=fold_names, inline=False)

        if len(winners) == 1:
            w = winners[0]
            result_line = (
                f"🏆 **{w['name']}** wins {var.CURRENCY_SYMBOL} **{split:,}** "
                f"with **{w['hand_name']}**!"
            )
        else:
            names_str = " & ".join(w['name'] for w in winners)
            result_line = f"🤝 Split pot! **{names_str}** each win {var.CURRENCY_SYMBOL} **{split:,}**!"
        if dm_mult > 1.0:
            result_line += f"\n💰 **{dm_mult}x** Multiplier Event bonus applied!"
        showdown.add_field(name="Result", value=result_line, inline=False)
        showdown.set_footer(text=f"{len(uids)} players · {var.SERVER_NAME}")
        showdown.timestamp = datetime.utcnow()
        await channel.send(embed=showdown)


async def setup(bot: commands.Bot):
    await bot.add_cog(PokerCog(bot))
    log.info("✅ Casino/Poker cog loaded")
