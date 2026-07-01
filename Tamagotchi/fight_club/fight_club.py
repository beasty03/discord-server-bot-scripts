from __future__ import annotations

import random
import time
import logging
import importlib.util as _ilu
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from forge_db import ForgeDB

_is_log_enabled = lambda cat: True
try:
    _lpath = Path(__file__).parent.parent.parent / "Admin" / "panel" / "log_config.py"
    if not _lpath.exists():
        _lpath = Path(__file__).parent.parent / "panel" / "log_config.py"
    if _lpath.exists():
        _ls = _ilu.spec_from_file_location("_log_cfg", _lpath)
        _lm = _ilu.module_from_spec(_ls); _ls.loader.exec_module(_lm)
        _is_log_enabled = _lm.is_log_enabled
except Exception:
    pass

_spec = _ilu.spec_from_file_location("fc_variables", Path(__file__).parent / "variables.py")
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

_tspec = _ilu.spec_from_file_location("tvar", Path(__file__).parent.parent / "tamagotchi" / "variables.py")
tvar = _ilu.module_from_spec(_tspec)
_tspec.loader.exec_module(tvar)

log = logging.getLogger(__name__)

coin = lambda n: f"{var.CURRENCY_SYMBOL} **{n:,}** {var.CURRENCY_NAME}"


# ============================================================================
# FIGHT ENGINE
# ============================================================================

def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _fight_stats(p: dict) -> tuple[int, int, int]:
    """Convert tamagotchi stats → (max_hp, attack, defense)."""
    hp = int(_clamp(p["health"] * var.STAT_HP_MULT, var.STAT_HP_MIN, var.STAT_HP_MAX))
    atk = int(_clamp(
        p["weight"] * var.STAT_ATK_WEIGHT
        + p["energy"] * var.STAT_ATK_ENERGY
        + p["happiness"] * var.STAT_ATK_HAPPY,
        var.STAT_ATK_MIN, var.STAT_ATK_MAX,
    ))
    def_ = int(_clamp(p["health"] * var.STAT_DEF_HEALTH, var.STAT_DEF_MIN, var.STAT_DEF_MAX))
    return hp, atk, def_


def _run_fight(pet1: dict, pet2: dict) -> tuple[int, list[dict], int, int]:
    """
    Simulate the fight between two pets.
    Returns (winner: 1|2|0, rounds: list, hp1_max: int, hp2_max: int).
    winner=0 means draw.
    """
    hp1_max, atk1, def1 = _fight_stats(pet1)
    hp2_max, atk2, def2 = _fight_stats(pet2)
    hp1, hp2 = hp1_max, hp2_max
    rounds = []

    for rnd in range(1, var.MAX_ROUNDS + 1):
        crit1  = random.random() < var.CRIT_CHANCE
        dodge2 = random.random() < var.DODGE_CHANCE
        if dodge2:
            dmg1 = 0
        else:
            base1 = max(1, atk1 - def2 + random.randint(var.DMG_VARIANCE_MIN, var.DMG_VARIANCE_MAX))
            dmg1  = int(base1 * var.CRIT_MULTIPLIER) if crit1 else base1

        crit2  = random.random() < var.CRIT_CHANCE
        dodge1 = random.random() < var.DODGE_CHANCE
        if dodge1:
            dmg2 = 0
        else:
            base2 = max(1, atk2 - def1 + random.randint(var.DMG_VARIANCE_MIN, var.DMG_VARIANCE_MAX))
            dmg2  = int(base2 * var.CRIT_MULTIPLIER) if crit2 else base2

        hp2 -= dmg1
        hp1 -= dmg2

        rounds.append({
            "round":  rnd,
            "dmg1":   dmg1,  "dmg2":   dmg2,
            "crit1":  crit1, "crit2":  crit2,
            "dodge1": dodge1,"dodge2": dodge2,
            "hp1":    max(0, hp1), "hp2": max(0, hp2),
        })

        if hp1 <= 0 or hp2 <= 0:
            break

    winner = 1 if hp1 > hp2 else (2 if hp2 > hp1 else 0)
    return winner, rounds, hp1_max, hp2_max


def _build_log(rounds: list[dict], pet1: dict, pet2: dict) -> str:
    e1 = tvar.PET_TYPES.get(pet1["pet_type"], {}).get("emoji", "🐾")
    e2 = tvar.PET_TYPES.get(pet2["pet_type"], {}).get("emoji", "🐾")
    n1, n2 = pet1["name"], pet2["name"]

    shown = rounds[:4] + ([rounds[-1]] if len(rounds) > 4 else [])
    parts = []

    for i, r in enumerate(shown):
        if i == 4 and len(rounds) > 5:
            parts.append(f"*... {len(rounds) - 5} more rounds ...*")

        hits = []
        if r["dodge2"]:
            hits.append(f"{e1} **{n1}** → 💨 {n2} dodged!")
        elif r["crit1"]:
            hits.append(f"{e1} **{n1}** → ⚡ **CRIT** `{r['dmg1']}` dmg → {n2} HP `{r['hp2']}`")
        else:
            hits.append(f"{e1} **{n1}** → `{r['dmg1']}` dmg → {n2} HP `{r['hp2']}`")

        if r["dodge1"]:
            hits.append(f"{e2} **{n2}** → 💨 {n1} dodged!")
        elif r["crit2"]:
            hits.append(f"{e2} **{n2}** → ⚡ **CRIT** `{r['dmg2']}` dmg → {n1} HP `{r['hp1']}`")
        else:
            hits.append(f"{e2} **{n2}** → `{r['dmg2']}` dmg → {n1} HP `{r['hp1']}`")

        parts.append(f"**Round {r['round']}**\n" + "\n".join(hits))

    return "\n\n".join(parts)


# ============================================================================
# DB HELPERS
# ============================================================================

_PET_COLS = [
    "user_id", "guild_id", "name", "pet_type",
    "hunger", "happiness", "health", "energy", "weight",
    "born_at", "last_updated",
    "last_fed", "last_played", "last_cleaned", "last_rested",
    "alive", "total_fed", "total_played",
]


def _get_pet(db, uid: str, gid: str) -> dict | None:
    rows = db.execute(
        f"SELECT {', '.join(_PET_COLS)} FROM tamagotchi WHERE user_id=? AND guild_id=?",
        (uid, gid),
    )
    if not rows:
        return None
    return dict(zip(_PET_COLS, rows[0]))


def _apply_post_fight(db, pet: dict, won: bool):
    if won:
        new_happy  = min(100.0, pet["happiness"] + var.WIN_HAPPINESS_GAIN)
        new_health = min(100.0, pet["health"]    + var.WIN_HEALTH_GAIN)
    else:
        new_happy  = max(0.0,  pet["happiness"] - var.LOSE_HAPPINESS_LOSS)
        new_health = max(1.0,  pet["health"]    - var.LOSE_HEALTH_LOSS)

    db.execute(
        "UPDATE tamagotchi SET happiness=?, health=?, last_updated=? WHERE user_id=? AND guild_id=?",
        (new_happy, new_health, time.time(), pet["user_id"], pet["guild_id"]),
    )


def _record_fight(db, uid: str, gid: str, won: bool, earnings: int):
    db.execute(
        "INSERT OR IGNORE INTO tamagotchi_fights (user_id, guild_id) VALUES (?, ?)",
        (uid, gid),
    )
    if won:
        db.execute(
            "UPDATE tamagotchi_fights SET wins=wins+1, earnings=earnings+? WHERE user_id=? AND guild_id=?",
            (earnings, uid, gid),
        )
    else:
        db.execute(
            "UPDATE tamagotchi_fights SET losses=losses+1 WHERE user_id=? AND guild_id=?",
            (uid, gid),
        )


# ============================================================================
# CHALLENGE VIEW
# ============================================================================

class ChallengeView(discord.ui.View):

    def __init__(self, cog, challenger: discord.Member, opponent: discord.Member, bet: int, guild_id: int):
        super().__init__(timeout=var.CHALLENGE_TIMEOUT)
        self.cog        = cog
        self.challenger = challenger
        self.opponent   = opponent
        self.bet        = bet
        self.guild_id   = guild_id
        self.resolved   = False

    # ── guards ────────────────────────────────────────────────────────────────

    def _is_opponent(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.opponent.id

    def _disable_all(self):
        for item in self.children:
            item.disabled = True

    # ── accept ────────────────────────────────────────────────────────────────

    @discord.ui.button(label="⚔️ Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._is_opponent(interaction):
            await interaction.response.send_message("This challenge isn't for you!", ephemeral=True)
            return
        if self.resolved:
            await interaction.response.send_message("This challenge is no longer active.", ephemeral=True)
            return
        self.resolved = True
        self.stop()
        await self._run(interaction)

    # ── decline ───────────────────────────────────────────────────────────────

    @discord.ui.button(label="🏳️ Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._is_opponent(interaction):
            await interaction.response.send_message("This challenge isn't for you!", ephemeral=True)
            return
        if self.resolved:
            await interaction.response.send_message("This challenge is no longer active.", ephemeral=True)
            return
        self.resolved = True
        self.stop()
        self.cog._unlock(interaction.guild_id, self.challenger.id)
        self.cog._unlock(interaction.guild_id, self.opponent.id)
        self._disable_all()
        embed = discord.Embed(
            description=f"🏳️ **{self.opponent.display_name}** declined the challenge.",
            color=var.COLOR_ERROR,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    # ── fight logic ───────────────────────────────────────────────────────────

    async def _run(self, interaction: discord.Interaction):
        db    = self.cog.db
        gid   = str(interaction.guild_id)
        c_uid = str(self.challenger.id)
        o_uid = str(self.opponent.id)
        bet   = self.bet

        # Fresh pet data
        cpet = _get_pet(db, c_uid, gid)
        opet = _get_pet(db, o_uid, gid)

        def _err(msg: str):
            self._disable_all()
            self.cog._unlock(interaction.guild_id, self.challenger.id)
            self.cog._unlock(interaction.guild_id, self.opponent.id)
            return discord.Embed(description=f"❌ {msg}", color=var.COLOR_ERROR)

        if not cpet or cpet["alive"] != 1:
            return await interaction.response.edit_message(
                embed=_err(f"{self.challenger.mention}'s pet is no longer alive."), view=self
            )
        if not opet or opet["alive"] != 1:
            return await interaction.response.edit_message(
                embed=_err(f"{self.opponent.mention}'s pet is no longer alive."), view=self
            )

        db.ensure_user(c_uid, gid, self.challenger.display_name)
        db.ensure_user(o_uid, gid, self.opponent.display_name)

        c_bal = db.get_balance(c_uid, gid)
        o_bal = db.get_balance(o_uid, gid)

        if c_bal < bet:
            return await interaction.response.edit_message(
                embed=_err(f"{self.challenger.mention} no longer has enough {var.CURRENCY_NAME}."), view=self
            )
        if o_bal < bet:
            return await interaction.response.edit_message(
                embed=_err(f"{self.opponent.mention} doesn't have enough {var.CURRENCY_NAME}."), view=self
            )

        # Deduct bets
        db.update_balance(c_uid, gid, -bet, "fight_bet")
        db.update_balance(o_uid, gid, -bet, "fight_bet")

        # Run fight
        winner, rounds, hp1_max, hp2_max = _run_fight(cpet, opet)
        battle_log = _build_log(rounds, cpet, opet)

        e1 = tvar.PET_TYPES.get(cpet["pet_type"], {}).get("emoji", "🐾")
        e2 = tvar.PET_TYPES.get(opet["pet_type"], {}).get("emoji", "🐾")
        n1, n2 = cpet["name"], opet["name"]

        if winner == 1:
            db.update_balance(c_uid, gid, bet * 2, "fight_win")
            _apply_post_fight(db, cpet, won=True)
            _apply_post_fight(db, opet, won=False)
            _record_fight(db, c_uid, gid, True,  bet)
            _record_fight(db, o_uid, gid, False, 0)
            color  = var.COLOR_WIN
            title  = f"⚔️ {n1} defeats {n2}!"
            result = (
                f"🎉 {self.challenger.mention} wins {coin(bet)}!\n"
                f"💔 {self.opponent.mention} loses {coin(bet)}\n\n"
                f"{e1} **{n1}**: +{var.WIN_HAPPINESS_GAIN} happiness, +{var.WIN_HEALTH_GAIN} health\n"
                f"{e2} **{n2}**: -{var.LOSE_HAPPINESS_LOSS} happiness, -{var.LOSE_HEALTH_LOSS} health"
            )
        elif winner == 2:
            db.update_balance(o_uid, gid, bet * 2, "fight_win")
            _apply_post_fight(db, cpet, won=False)
            _apply_post_fight(db, opet, won=True)
            _record_fight(db, c_uid, gid, False, 0)
            _record_fight(db, o_uid, gid, True,  bet)
            color  = var.COLOR_LOSE
            title  = f"⚔️ {n2} defeats {n1}!"
            result = (
                f"🎉 {self.opponent.mention} wins {coin(bet)}!\n"
                f"💔 {self.challenger.mention} loses {coin(bet)}\n\n"
                f"{e2} **{n2}**: +{var.WIN_HAPPINESS_GAIN} happiness, +{var.WIN_HEALTH_GAIN} health\n"
                f"{e1} **{n1}**: -{var.LOSE_HAPPINESS_LOSS} happiness, -{var.LOSE_HEALTH_LOSS} health"
            )
        else:
            # Draw — refund both
            db.update_balance(c_uid, gid, bet, "fight_draw_refund")
            db.update_balance(o_uid, gid, bet, "fight_draw_refund")
            _apply_post_fight(db, cpet, won=False)
            _apply_post_fight(db, opet, won=False)
            color  = var.COLOR_DRAW
            title  = f"🤝 {n1} vs {n2} — Draw!"
            result = (
                f"Both pets fought to a standstill — bets refunded.\n"
                f"{e1} **{n1}**: -{var.LOSE_HAPPINESS_LOSS} happiness, -{var.LOSE_HEALTH_LOSS} health\n"
                f"{e2} **{n2}**: -{var.LOSE_HAPPINESS_LOSS} happiness, -{var.LOSE_HEALTH_LOSS} health"
            )

        self.cog._unlock(interaction.guild_id, self.challenger.id)
        self.cog._unlock(interaction.guild_id, self.opponent.id)

        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="⚔️ Battle Log", value=battle_log or "—", inline=False)
        embed.add_field(name="🏆 Result",     value=result,            inline=False)

        hp1_final = rounds[-1]["hp1"]
        hp2_final = rounds[-1]["hp2"]
        embed.set_footer(text=f"Final HP — {n1}: {hp1_final}/{hp1_max}  |  {n2}: {hp2_final}/{hp2_max}")

        # Post summary to #bot-logs if enabled
        if _is_log_enabled("fight_results"):
            bot_logs = discord.utils.get(interaction.guild.text_channels, name="bot-logs")
            if bot_logs:
                try:
                    log_embed = discord.Embed(title=f"⚔️ {title}", color=color)
                    log_embed.add_field(name="Challenger", value=self.challenger.mention, inline=True)
                    log_embed.add_field(name="Opponent",   value=self.opponent.mention,   inline=True)
                    log_embed.add_field(name="Bet",        value=coin(self.bet),          inline=True)
                    log_embed.add_field(name="Rounds",     value=str(len(rounds)),        inline=True)
                    await bot_logs.send(embed=log_embed)
                except Exception:
                    pass

        self._disable_all()
        await interaction.response.edit_message(embed=embed, view=self)

    # ── timeout ───────────────────────────────────────────────────────────────

    async def on_timeout(self):
        if not self.resolved:
            self.resolved = True
            self.cog._unlock(self.guild_id, self.challenger.id)
            self.cog._unlock(self.guild_id, self.opponent.id)
            self._disable_all()


# ============================================================================
# COG
# ============================================================================

class FightClubCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()
        self._pending: set[tuple[int, int]] = set()   # (guild_id, user_id)

    def _lock(self, guild_id: int, user_id: int) -> bool:
        key = (guild_id, user_id)
        if key in self._pending:
            return False
        self._pending.add(key)
        return True

    def _unlock(self, guild_id, user_id: int):
        self._pending.discard((guild_id, user_id))

    async def cog_load(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS tamagotchi_fights (
                user_id  TEXT NOT NULL,
                guild_id TEXT NOT NULL,
                wins     INTEGER NOT NULL DEFAULT 0,
                losses   INTEGER NOT NULL DEFAULT 0,
                earnings INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

    # ── /challenge ────────────────────────────────────────────────────────────

    @app_commands.command(name="challenge", description="Challenge another user's tamagotchi to a fight")
    @app_commands.describe(
        opponent="The user you want to challenge",
        bet=f"Coins to bet (minimum {var.BET_MIN:,})",
    )
    async def challenge(self, interaction: discord.Interaction, opponent: discord.Member, bet: int):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if opponent.id == interaction.user.id:
            return await interaction.response.send_message("You can't challenge yourself.", ephemeral=True)
        if opponent.bot:
            return await interaction.response.send_message("You can't challenge a bot.", ephemeral=True)
        if bet < var.BET_MIN:
            return await interaction.response.send_message(
                f"Minimum bet is {coin(var.BET_MIN)}.", ephemeral=True
            )

        cpet = _get_pet(self.db, uid, gid)
        if not cpet or cpet["alive"] != 1:
            return await interaction.response.send_message(
                "You don't have a living tamagotchi to fight with.", ephemeral=True
            )

        opet = _get_pet(self.db, str(opponent.id), gid)
        if not opet or opet["alive"] != 1:
            return await interaction.response.send_message(
                f"{opponent.display_name} doesn't have a living tamagotchi.", ephemeral=True
            )

        self.db.ensure_user(uid, gid, interaction.user.display_name)
        c_bal = self.db.get_balance(uid, gid)
        if c_bal < bet:
            return await interaction.response.send_message(
                f"You only have {coin(c_bal)}.", ephemeral=True
            )

        if not self._lock(interaction.guild_id, interaction.user.id):
            return await interaction.response.send_message(
                "You already have an active challenge pending.", ephemeral=True
            )
        if not self._lock(interaction.guild_id, opponent.id):
            self._unlock(interaction.guild_id, interaction.user.id)
            return await interaction.response.send_message(
                f"{opponent.display_name} is already involved in a challenge.", ephemeral=True
            )

        e1 = tvar.PET_TYPES.get(cpet["pet_type"], {}).get("emoji", "🐾")
        e2 = tvar.PET_TYPES.get(opet["pet_type"], {}).get("emoji", "🐾")
        hp1, atk1, def1 = _fight_stats(cpet)
        hp2, atk2, def2 = _fight_stats(opet)

        embed = discord.Embed(
            title="⚔️ Fight Challenge!",
            color=var.COLOR_CHALLENGE,
        )
        embed.add_field(
            name=f"{e1} {cpet['name']} — {interaction.user.display_name}",
            value=(
                f"Type: {tvar.PET_TYPES.get(cpet['pet_type'], {}).get('name', cpet['pet_type'])}\n"
                f"HP: `{hp1}` | ATK: `{atk1}` | DEF: `{def1}`"
            ),
            inline=True,
        )
        embed.add_field(name="vs", value="⚔️", inline=True)
        embed.add_field(
            name=f"{e2} {opet['name']} — {opponent.display_name}",
            value=(
                f"Type: {tvar.PET_TYPES.get(opet['pet_type'], {}).get('name', opet['pet_type'])}\n"
                f"HP: `{hp2}` | ATK: `{atk2}` | DEF: `{def2}`"
            ),
            inline=True,
        )
        embed.add_field(
            name="💰 Stakes",
            value=f"Bet: {coin(bet)} each\nPrize pool: {coin(bet * 2)}",
            inline=False,
        )
        embed.set_footer(text=f"{opponent.display_name} has {var.CHALLENGE_TIMEOUT}s to respond.")

        view = ChallengeView(self, interaction.user, opponent, bet, interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view)
        await view.wait()

        if not view.resolved:
            view._disable_all()
            self._unlock(interaction.guild_id, interaction.user.id)
            self._unlock(interaction.guild_id, opponent.id)
            try:
                await interaction.edit_original_response(
                    embed=discord.Embed(
                        description=f"⌛ Challenge timed out — {opponent.display_name} didn't respond.",
                        color=var.COLOR_ERROR,
                    ),
                    view=view,
                )
            except discord.NotFound:
                pass

    # ── /fight_stats ──────────────────────────────────────────────────────────

    @app_commands.command(name="fight_stats", description="View your tamagotchi's fight record")
    async def fight_stats(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        rows = self.db.execute(
            "SELECT wins, losses, earnings FROM tamagotchi_fights WHERE user_id=? AND guild_id=?",
            (uid, gid),
        )
        if not rows:
            return await interaction.response.send_message(
                "Your tamagotchi hasn't fought anyone yet.", ephemeral=True
            )

        try:
            wins, losses, earnings = rows[0][0], rows[0][1], rows[0][2]
        except (IndexError, TypeError):
            wins, losses, earnings = 0, 0, 0

        total  = wins + losses
        ratio  = f"{wins}/{total}" if total else "—"
        pet    = _get_pet(self.db, uid, gid)
        name   = pet["name"] if pet else "Your pet"
        emoji  = tvar.PET_TYPES.get(pet["pet_type"], {}).get("emoji", "🐾") if pet else "🐾"

        embed = discord.Embed(
            title=f"{emoji} {name}'s Fight Record",
            color=var.COLOR_WIN if wins >= losses else var.COLOR_LOSE,
        )
        embed.add_field(name="⚔️ Fights",   value=str(total), inline=True)
        embed.add_field(name="🏆 Wins",     value=str(wins),  inline=True)
        embed.add_field(name="💔 Losses",   value=str(losses),inline=True)
        embed.add_field(name="📊 Win Rate", value=ratio,      inline=True)
        embed.add_field(name="💰 Earned",   value=coin(earnings), inline=True)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    cog = FightClubCog(bot)
    if var.GUILD_ID:
        try:
            await bot.add_cog(cog, guilds=[discord.Object(id=var.GUILD_ID)])
            log.info("FightClubCog registered as guild-specific (id=%s)", var.GUILD_ID)
            return
        except TypeError:
            log.warning("guilds= not supported by this discord.py version; falling back to global")
    await bot.add_cog(cog)
