import time
import logging
from datetime import datetime
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('tama_var', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

log = logging.getLogger("launcher")


# ============================================================================
# STAT HELPERS
# ============================================================================

def _bar(value: float, length: int = 8) -> str:
    """Emoji progress bar — green filled, grey empty."""
    filled = max(0, min(length, round((value / 100) * length)))
    return "🟩" * filled + "⬜" * (length - filled)


def _hunger_bar(hunger: float, length: int = 8) -> str:
    """Inverted bar — full stomach = green."""
    return _bar(100 - hunger, length)


_MOOD_FACES = {
    "default": {
        "dead":    "💀",
        "critical":"😵",
        "sick":    "🤒",
        "ecstatic":"(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧",
        "happy":   "(^▽^)",
        "content": "(￣ω￣)",
        "sad":     "(´；ω；｀)",
        "miserable":"(╥_╥)",
    },
    "waifu": {
        "dead":    "💀",
        "critical":"(＞﹏＜)",
        "sick":    "(｡•́︿•̀｡)",
        "ecstatic":"(≧◡≦) ♡",
        "happy":   "UwU ♡",
        "content": "(｡♥‿♥｡)",
        "sad":     "(╯︵╰,)",
        "miserable":"(T▽T) p-please notice me...",
    },
    "goth_mommy": {
        "dead":    "☠️",
        "critical":"(ᗒᗣᗕ)՞",
        "sick":    "✞ ( ͠° ʖ°) ✞",
        "ecstatic":"✦ (◉‿◉) ✦ yesss",
        "happy":   "( ˘ ³˘)♥ good.",
        "content": "¬_¬  ...fine.",
        "sad":     "( ._.) ...disappointing.",
        "miserable":"(ಠ_ಠ) you neglected me.",
    },
}


def _mood_face(happiness: float, health: float, pet_type: str = "default") -> str:
    faces = _MOOD_FACES.get(pet_type, _MOOD_FACES["default"])
    if health <= 0:   return faces["dead"]
    if health < 20:   return faces["critical"]
    if health < 50:   return faces["sick"]
    if happiness >= 90: return faces["ecstatic"]
    if happiness >= 70: return faces["happy"]
    if happiness >= 50: return faces["content"]
    if happiness >= 30: return faces["sad"]
    return faces["miserable"]


def _get_stage(born_at: float) -> tuple[str, str]:
    """Return (stage_label, stage_emoji)."""
    age = (time.time() - born_at) / 86400
    if age < var.STAGE_EGG_DAYS:
        return "Egg",   "🥚"
    if age < var.STAGE_BABY_DAYS:
        return "Baby",  "🐣"
    if age < var.STAGE_CHILD_DAYS:
        return "Child", ""
    if age < var.STAGE_TEEN_DAYS:
        return "Teen",  "✨"
    return "Adult", "⭐"


def _embed_color(health: float, happiness: float) -> int:
    if health <= 0:
        return var.COLOR_DEAD
    if health < 30:
        return var.COLOR_SICK
    if happiness < 30:
        return var.COLOR_SAD
    if happiness >= 70 and health >= 70:
        return var.COLOR_HAPPY
    return var.COLOR_NEUTRAL


# ============================================================================
# DECAY ENGINE
# ============================================================================

def _apply_decay(row: dict) -> dict:
    """Apply time-based stat decay and return updated dict (not saved yet)."""
    now     = time.time()
    elapsed = (now - row["last_updated"]) / 3600   # hours

    p = dict(row)

    p["hunger"]    = min(100.0, p["hunger"]    + var.DECAY_HUNGER    * elapsed)
    p["happiness"] = max(0.0,   p["happiness"] - var.DECAY_HAPPINESS * elapsed)
    p["energy"]    = max(0.0,   p["energy"]    - var.DECAY_ENERGY    * elapsed)

    health_delta = 0.0
    if p["hunger"] >= 80:
        health_delta -= var.HEALTH_LOSS_STARVING  * elapsed
    elif p["hunger"] >= 60:
        health_delta -= var.HEALTH_LOSS_HUNGRY    * elapsed
    if p["happiness"] <= 20:
        health_delta -= var.HEALTH_LOSS_UNHAPPY   * elapsed
    elif p["happiness"] <= 40:
        health_delta -= var.HEALTH_LOSS_LOW_HAPPY * elapsed
    if p["energy"] <= 10:
        health_delta -= var.HEALTH_LOSS_TIRED     * elapsed
    if p["hunger"] <= 30 and p["happiness"] >= 60 and p["energy"] >= 50:
        health_delta += var.HEALTH_GAIN_THRIVING  * elapsed

    p["health"]       = max(0.0, min(100.0, p["health"] + health_delta))
    p["last_updated"] = now

    if p["health"] <= 0:
        p["alive"] = 0

    return p


# ============================================================================
# DB HELPERS
# ============================================================================

_COLS = (
    "user_id", "guild_id", "name", "pet_type",
    "hunger", "happiness", "health", "energy", "weight",
    "born_at", "last_updated", "last_fed", "last_played", "last_cleaned", "last_rested",
    "alive", "total_fed", "total_played",
)


def _row_to_dict(row: tuple) -> dict:
    return dict(zip(_COLS, row))


def _get_pet(db, uid: str, gid: str) -> dict | None:
    rows = db.execute(
        f"SELECT {', '.join(_COLS)} FROM tamagotchi WHERE user_id = ? AND guild_id = ?",
        (uid, gid),
    )
    return _row_to_dict(rows[0]) if rows else None


def _save_pet(db, p: dict):
    db.execute(
        """UPDATE tamagotchi SET
               hunger=?, happiness=?, health=?, energy=?, weight=?,
               last_updated=?, last_fed=?, last_played=?, last_cleaned=?, last_rested=?,
               alive=?, total_fed=?, total_played=?, name=?
           WHERE user_id=? AND guild_id=?""",
        (
            round(p["hunger"], 4), round(p["happiness"], 4),
            round(p["health"], 4), round(p["energy"], 4),
            round(p["weight"], 2),
            p["last_updated"], p["last_fed"], p["last_played"],
            p["last_cleaned"], p["last_rested"],
            p["alive"], p["total_fed"], p["total_played"], p["name"],
            p["user_id"], p["guild_id"],
        ),
    )


def _cooldown_remaining(last_ts: float, cooldown_mins: float) -> int:
    """Return remaining seconds on a cooldown, or 0 if ready."""
    elapsed = time.time() - last_ts
    remaining = cooldown_mins * 60 - elapsed
    return max(0, int(remaining))


# ============================================================================
# EMBED BUILDER
# ============================================================================

def _build_embed(p: dict, user: discord.User | discord.Member) -> discord.Embed:
    ptype     = var.PET_TYPES.get(p["pet_type"], {"emoji": "🐾", "name": p["pet_type"].title()})
    stage, stage_emoji = _get_stage(p["born_at"])
    age_days  = (time.time() - p["born_at"]) / 86400
    pet_emoji = stage_emoji or ptype["emoji"]
    face      = _mood_face(p["happiness"], p["health"], p["pet_type"])

    color = _embed_color(p["health"], p["happiness"])

    if not p["alive"]:
        embed = discord.Embed(
            title=f"🪦 {p['name']} has passed away",
            description=(
                f"{ptype['emoji']} *{p['name']} lived for **{age_days:.1f}** days.*\n\n"
                f"Use `/adopt` to get a new pet."
            ),
            color=var.COLOR_DEAD,
        )
        embed.set_footer(text=f"{user.display_name} · {var.SERVER_NAME}")
        return embed

    embed = discord.Embed(
        title=f"{pet_emoji} {p['name']}  {face}",
        color=color,
    )
    embed.add_field(
        name="🍖 Hunger",
        value=f"{_hunger_bar(p['hunger'])} `{int(100 - p['hunger'])}/100`",
        inline=False,
    )
    embed.add_field(
        name="😊 Happiness",
        value=f"{_bar(p['happiness'])} `{int(p['happiness'])}/100`",
        inline=False,
    )
    embed.add_field(
        name="❤️ Health",
        value=f"{_bar(p['health'])} `{int(p['health'])}/100`",
        inline=False,
    )
    embed.add_field(
        name="⚡ Energy",
        value=f"{_bar(p['energy'])} `{int(p['energy'])}/100`",
        inline=False,
    )
    embed.add_field(name="🐾 Type",    value=f"{ptype['emoji']} {ptype['name']}", inline=True)
    embed.add_field(name="📅 Stage",   value=f"{stage_emoji} {stage}",            inline=True)
    embed.add_field(name="📆 Age",     value=f"{age_days:.1f} days",              inline=True)
    embed.add_field(name="⚖️ Weight",  value=f"{p['weight']:.1f} kg",             inline=True)
    embed.add_field(name="🍽️ Fed",    value=f"{p['total_fed']} times",            inline=True)
    embed.add_field(name="🎮 Played",  value=f"{p['total_played']} times",        inline=True)
    embed.set_footer(text=f"{user.display_name} · {var.SERVER_NAME}")
    embed.timestamp = datetime.utcnow()
    return embed


# ============================================================================
# VIEW
# ============================================================================

class PetView(discord.ui.View):

    def __init__(self, cog, interaction: discord.Interaction, pet: dict):
        super().__init__(timeout=var.VIEW_TIMEOUT)
        self.cog         = cog
        self.interaction = interaction
        self.uid         = str(interaction.user.id)
        self.gid         = str(interaction.guild_id)
        self._refresh_button_states(pet)

    def _refresh_button_states(self, pet: dict):
        for item in self.children:
            if not isinstance(item, discord.ui.Button):
                continue
            if item.custom_id == "feed":
                item.disabled = _cooldown_remaining(pet["last_fed"], var.FEED_COOLDOWN_MINS) > 0
            elif item.custom_id == "play":
                item.disabled = _cooldown_remaining(pet["last_played"], var.PLAY_COOLDOWN_MINS) > 0
            elif item.custom_id == "clean":
                item.disabled = _cooldown_remaining(pet["last_cleaned"], var.CLEAN_COOLDOWN_MINS) > 0
            elif item.custom_id == "rest":
                item.disabled = _cooldown_remaining(pet["last_rested"], var.REST_COOLDOWN_MINS) > 0

    async def _guard(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != int(self.uid):
            await interaction.response.send_message("This isn't your pet!", ephemeral=True)
            return False
        return True

    async def _act(self, interaction: discord.Interaction, action: str):
        p = _get_pet(self.cog.db, self.uid, self.gid)
        if not p:
            await interaction.response.send_message("You don't have a pet!", ephemeral=True)
            return
        p = _apply_decay(p)

        if not p["alive"]:
            _save_pet(self.cog.db, p)
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(
                embed=_build_embed(p, interaction.user), view=self,
            )
            return

        now = time.time()
        msg = ""

        if action == "feed":
            cd = _cooldown_remaining(p["last_fed"], var.FEED_COOLDOWN_MINS)
            if cd:
                await interaction.response.send_message(
                    f"⏰ Feed cooldown: **{cd // 60}m {cd % 60}s** remaining.", ephemeral=True,
                )
                return
            if var.FEED_COST > 0:
                bal = self.cog.db.get_balance(self.uid, self.gid)
                if bal < var.FEED_COST:
                    await interaction.response.send_message(
                        f"Not enough {var.CURRENCY_NAME} — feeding costs {var.CURRENCY_SYMBOL} **{var.FEED_COST:,}**.",
                        ephemeral=True,
                    )
                    return
                self.cog.db.update_balance(self.uid, self.gid, -var.FEED_COST, "pet_feed")
            p["hunger"]    = max(0.0, p["hunger"] - var.FEED_HUNGER_REDUCE)
            p["weight"]    = min(var.WEIGHT_MAX, p["weight"] + var.FEED_WEIGHT_GAIN)
            p["last_fed"]  = now
            p["total_fed"] += 1
            msg = f"🍖 You fed **{p['name']}**!"

        elif action == "play":
            cd = _cooldown_remaining(p["last_played"], var.PLAY_COOLDOWN_MINS)
            if cd:
                await interaction.response.send_message(
                    f"⏰ Play cooldown: **{cd // 60}m {cd % 60}s** remaining.", ephemeral=True,
                )
                return
            p["happiness"]   = min(100.0, p["happiness"] + var.PLAY_HAPPINESS_GAIN)
            p["energy"]      = max(0.0,   p["energy"]    - var.PLAY_ENERGY_COST)
            p["weight"]      = max(var.WEIGHT_MIN, p["weight"] - var.PLAY_WEIGHT_LOSS)
            p["last_played"] = now
            p["total_played"] += 1
            msg = f"🎮 You played with **{p['name']}**!"

        elif action == "clean":
            cd = _cooldown_remaining(p["last_cleaned"], var.CLEAN_COOLDOWN_MINS)
            if cd:
                await interaction.response.send_message(
                    f"⏰ Clean cooldown: **{cd // 60}m {cd % 60}s** remaining.", ephemeral=True,
                )
                return
            p["health"]       = min(100.0, p["health"]    + var.CLEAN_HEALTH_GAIN)
            p["happiness"]    = min(100.0, p["happiness"] + var.CLEAN_HAPPINESS_GAIN)
            p["last_cleaned"] = now
            msg = f"🛁 You cleaned **{p['name']}**!"

        elif action == "rest":
            cd = _cooldown_remaining(p["last_rested"], var.REST_COOLDOWN_MINS)
            if cd:
                await interaction.response.send_message(
                    f"⏰ Rest cooldown: **{cd // 60}m {cd % 60}s** remaining.", ephemeral=True,
                )
                return
            p["energy"]      = min(100.0, p["energy"]    + var.REST_ENERGY_GAIN)
            p["happiness"]   = min(100.0, p["happiness"] + var.REST_HAPPINESS_GAIN)
            p["last_rested"] = now
            msg = f"💤 **{p['name']}** had a rest!"

        _save_pet(self.cog.db, p)
        self._refresh_button_states(p)
        embed = _build_embed(p, interaction.user)
        if msg:
            embed.description = f"*{msg}*"
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🍖 Feed",  style=discord.ButtonStyle.success,  custom_id="feed",  row=0)
    async def feed_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._guard(interaction): return
        await self._act(interaction, "feed")

    @discord.ui.button(label="🎮 Play",  style=discord.ButtonStyle.primary,   custom_id="play",  row=0)
    async def play_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._guard(interaction): return
        await self._act(interaction, "play")

    @discord.ui.button(label="🛁 Clean", style=discord.ButtonStyle.secondary, custom_id="clean", row=0)
    async def clean_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._guard(interaction): return
        await self._act(interaction, "clean")

    @discord.ui.button(label="💤 Rest",  style=discord.ButtonStyle.secondary, custom_id="rest",  row=0)
    async def rest_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._guard(interaction): return
        await self._act(interaction, "rest")

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.interaction.edit_original_response(view=self)
        except Exception:
            pass


# ============================================================================
# RELEASE CONFIRMATION VIEW
# ============================================================================

class ReleaseView(discord.ui.View):

    def __init__(self, cog, uid: str, gid: str, pet_name: str):
        super().__init__(timeout=30)
        self.cog      = cog
        self.uid      = uid
        self.gid      = gid
        self.pet_name = pet_name

    @discord.ui.button(label="Yes, release", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cog.db.execute(
            "DELETE FROM tamagotchi WHERE user_id = ? AND guild_id = ?",
            (self.uid, self.gid),
        )
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=f"👋 You released **{self.pet_name}**. Use `/adopt` to get a new pet.",
                color=var.COLOR_NEUTRAL,
            ),
            view=self,
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(description="Release cancelled.", color=var.COLOR_OK),
            view=self,
        )


# ============================================================================
# COG
# ============================================================================

class TamagotchiCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    async def cog_load(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS tamagotchi (
                user_id      TEXT NOT NULL,
                guild_id     TEXT NOT NULL,
                name         TEXT NOT NULL,
                pet_type     TEXT NOT NULL,
                hunger       REAL NOT NULL DEFAULT 20,
                happiness    REAL NOT NULL DEFAULT 80,
                health       REAL NOT NULL DEFAULT 100,
                energy       REAL NOT NULL DEFAULT 100,
                weight       REAL NOT NULL DEFAULT 10,
                born_at      REAL NOT NULL,
                last_updated REAL NOT NULL,
                last_fed     REAL NOT NULL DEFAULT 0,
                last_played  REAL NOT NULL DEFAULT 0,
                last_cleaned REAL NOT NULL DEFAULT 0,
                last_rested  REAL NOT NULL DEFAULT 0,
                alive        INTEGER NOT NULL DEFAULT 1,
                total_fed    INTEGER NOT NULL DEFAULT 0,
                total_played INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

    # ── /adopt ────────────────────────────────────────────────────────────────

    @app_commands.command(name="adopt", description="Adopt a virtual pet and take care of it!")
    @app_commands.describe(
        name="Give your pet a name",
        pet_type="What kind of pet do you want?",
    )
    @app_commands.choices(pet_type=[
        app_commands.Choice(name="🐱 Cat",         value="cat"),
        app_commands.Choice(name="🐶 Dog",         value="dog"),
        app_commands.Choice(name="🐰 Bunny",       value="bunny"),
        app_commands.Choice(name="🐤 Chick",       value="chick"),
        app_commands.Choice(name="🐢 Turtle",      value="turtle"),
        app_commands.Choice(name="🐲 Dragon",      value="dragon"),
        app_commands.Choice(name="🌸 Waifu",       value="waifu"),
        app_commands.Choice(name="🖤 Goth Mommy",  value="goth_mommy"),
    ])
    async def adopt(self, interaction: discord.Interaction, name: str, pet_type: str):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if len(name) > 24:
            return await interaction.response.send_message(
                embed=discord.Embed(description="Pet name must be 24 characters or fewer.", color=var.COLOR_ERROR),
                ephemeral=True,
            )

        existing = _get_pet(self.db, uid, gid)
        if existing and existing["alive"]:
            ptype = var.PET_TYPES.get(existing["pet_type"], {})
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        f"You already have **{existing['name']}** {ptype.get('emoji', '')}!\n"
                        f"Use `/release_pet` first if you want a new pet."
                    ),
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )

        now = time.time()
        self.db.execute(
            """INSERT INTO tamagotchi
                   (user_id, guild_id, name, pet_type,
                    hunger, happiness, health, energy, weight,
                    born_at, last_updated,
                    last_fed, last_played, last_cleaned, last_rested,
                    alive, total_fed, total_played)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 1, 0, 0)
               ON CONFLICT(user_id, guild_id) DO UPDATE SET
                   name=excluded.name, pet_type=excluded.pet_type,
                   hunger=excluded.hunger, happiness=excluded.happiness,
                   health=excluded.health, energy=excluded.energy, weight=excluded.weight,
                   born_at=excluded.born_at, last_updated=excluded.last_updated,
                   last_fed=0, last_played=0, last_cleaned=0, last_rested=0,
                   alive=1, total_fed=0, total_played=0""",
            (uid, gid, name.strip(), pet_type,
             var.START_HUNGER, var.START_HAPPINESS, var.START_HEALTH,
             var.START_ENERGY, var.START_WEIGHT,
             now, now),
        )

        ptype_info = var.PET_TYPES[pet_type]
        embed = discord.Embed(
            title=f"🥚 You adopted {name}!",
            description=(
                f"Your new **{ptype_info['name']}** {ptype_info['emoji']} is hatching...\n\n"
                f"Feed it, play with it, keep it clean and rested.\n"
                f"If you neglect it, its health will drop and it may die. 🪦\n\n"
                f"Use `/mypet` to check on it anytime!"
            ),
            color=var.COLOR_HAPPY,
        )
        embed.set_footer(text=f"{interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    # ── /mypet ────────────────────────────────────────────────────────────────

    @app_commands.command(name="mypet", description="Check on your pet and interact with it.")
    async def mypet(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        p = _get_pet(self.db, uid, gid)
        if not p:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description="You don't have a pet yet! Use `/adopt` to get one. 🐾",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )

        p = _apply_decay(p)
        _save_pet(self.db, p)

        view  = PetView(self, interaction, p) if p["alive"] else None
        embed = _build_embed(p, interaction.user)
        await interaction.response.send_message(embed=embed, view=view)

    # ── /rename_pet ───────────────────────────────────────────────────────────

    @app_commands.command(name="rename_pet", description="Give your pet a new name.")
    @app_commands.describe(name="New name for your pet")
    async def rename_pet(self, interaction: discord.Interaction, name: str):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        if len(name) > 24:
            return await interaction.response.send_message(
                embed=discord.Embed(description="Name must be 24 characters or fewer.", color=var.COLOR_ERROR),
                ephemeral=True,
            )

        p = _get_pet(self.db, uid, gid)
        if not p:
            return await interaction.response.send_message(
                embed=discord.Embed(description="You don't have a pet to rename!", color=var.COLOR_ERROR),
                ephemeral=True,
            )

        old_name  = p["name"]
        p["name"] = name.strip()
        _save_pet(self.db, p)

        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ **{old_name}** has been renamed to **{p['name']}**!",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )

    # ── /release_pet ──────────────────────────────────────────────────────────

    @app_commands.command(name="release_pet", description="Release your pet (permanent — cannot be undone).")
    async def release_pet(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)

        p = _get_pet(self.db, uid, gid)
        if not p:
            return await interaction.response.send_message(
                embed=discord.Embed(description="You don't have a pet to release.", color=var.COLOR_ERROR),
                ephemeral=True,
            )

        ptype = var.PET_TYPES.get(p["pet_type"], {"emoji": "🐾"})
        embed = discord.Embed(
            title=f"💔 Release {p['name']}?",
            description=(
                f"Are you sure you want to release **{p['name']}** {ptype['emoji']}?\n"
                f"This is **permanent** and cannot be undone."
            ),
            color=var.COLOR_ERROR,
        )
        await interaction.response.send_message(
            embed=embed,
            view=ReleaseView(self, uid, gid, p["name"]),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(TamagotchiCog(bot))
    log.info("✅ Tamagotchi cog loaded")
