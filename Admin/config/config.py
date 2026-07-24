import discord
from discord.ext import commands
from discord import app_commands
import logging
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('cfg_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

_cg_spec = _ilu.spec_from_file_location('channel_guard', Path(__file__).parent / 'channel_guard.py')
_cg = _ilu.module_from_spec(_cg_spec)
_cg_spec.loader.exec_module(_cg)
BotConfig = _cg.BotConfig
global_interaction_check = _cg.global_interaction_check

log = logging.getLogger("launcher")


class ConfigCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.tree.interaction_check = global_interaction_check
        log.info("✅ Global channel/role guard active")

    def cog_unload(self):
        try:
            del self.bot.tree.interaction_check
        except AttributeError:
            pass

    # ── Allowed channels ──────────────────────────────────────────────────────

    @app_commands.command(name="add_allowed_channel", description="Add a channel where bot commands can be used.")
    @app_commands.describe(channel="Channel to allow")
    async def add_allowed_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        BotConfig().add_allowed(channel.id, channel.name)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ {channel.mention} added to allowed channels.",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="remove_allowed_channel", description="Remove a channel from the allowed list.")
    @app_commands.describe(channel="Channel to remove")
    async def remove_allowed_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        BotConfig().remove_allowed(channel.id)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ {channel.mention} removed from allowed channels.",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )

    # ── Control panel ─────────────────────────────────────────────────────────

    @app_commands.command(name="set_control_panel", description="Set the channel where admin/set commands must be run.")
    @app_commands.describe(channel="The control panel channel")
    async def set_control_panel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        BotConfig().set_control_panel(channel.id, channel.name)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Control panel set to {channel.mention}.",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )

    # ── Staff roles ───────────────────────────────────────────────────────────

    @app_commands.command(name="set_staff_roles", description="Set which roles count as Admin/Moderator for bot commands.")
    @app_commands.describe(
        role1="First staff role",
        role2="Second staff role (optional)",
        role3="Third staff role (optional)",
        role4="Fourth staff role (optional)",
    )
    async def set_staff_roles(
        self,
        interaction: discord.Interaction,
        role1: discord.Role,
        role2: discord.Role | None = None,
        role3: discord.Role | None = None,
        role4: discord.Role | None = None,
    ):
        roles = [r for r in [role1, role2, role3, role4] if r is not None]
        BotConfig().set_staff_roles([r.name for r in roles])
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Staff roles set to: {', '.join(r.mention for r in roles)}.",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )

    # ── View current config ───────────────────────────────────────────────────

    @app_commands.command(name="view_config", description="Show the current channel and role configuration.")
    async def view_config(self, interaction: discord.Interaction):
        cfg = BotConfig()

        allowed = cfg.allowed_channels()
        allowed_val = (
            "\n".join(f"<#{c['id']}> (#{c['name']})" for c in allowed)
            if allowed else f"*(default: #{', #'.join(cfg.allowed_names())})*"
        )

        cp = cfg.control_panel()
        cp_val = f"<#{cp['id']}> (#{cp['name']})" if cp else f"*(default: #{cfg.control_panel_name()})*"

        staff = cfg.staff_role_names()
        staff_val = ", ".join(f"**{r}**" for r in staff)

        embed = discord.Embed(title="⚙️ Bot Configuration", color=var.COLOR_INFO)
        embed.add_field(name="Allowed Channels",  value=allowed_val, inline=False)
        embed.add_field(name="Control Panel",     value=cp_val,      inline=False)
        embed.add_field(name="Staff Role Names",  value=staff_val,   inline=False)
        embed.set_footer(text=var.SERVER_NAME)
        await interaction.response.send_message(embed=embed, ephemeral=True)


    # ── /debug ────────────────────────────────────────────────────────────────

    @app_commands.command(name="debug", description="[Admin] System health check for a bot category.")
    @app_commands.describe(category="Which category to inspect")
    @app_commands.choices(category=[
        app_commands.Choice(name="🤖 Bot Overview",      value="bot"),
        app_commands.Choice(name="⚔️ DND / Engine",      value="dnd"),
        app_commands.Choice(name="🎰 Casino",             value="casino"),
        app_commands.Choice(name="🌐 General",            value="general"),
        app_commands.Choice(name="👤 User",               value="user"),
        app_commands.Choice(name="💬 Quotes",             value="quotes"),
        app_commands.Choice(name="🎉 Events",             value="events"),
        app_commands.Choice(name="🗄️ Database",           value="database"),
        app_commands.Choice(name="⚙️ Config",             value="config"),
    ])
    async def debug(self, interaction: discord.Interaction, category: str):
        import sys
        embed = discord.Embed(color=var.COLOR_INFO)

        def _loaded(name: str) -> str:
            return "✅" if self.bot.cogs.get(name) else "❌"

        if category == "bot":
            embed.title = "🤖 Bot Overview"
            loaded_names = sorted(self.bot.cogs.keys())
            embed.add_field(
                name="📡 Status",
                value=(
                    f"**Latency:** {round(self.bot.latency * 1000)} ms\n"
                    f"**Guilds:** {len(self.bot.guilds)}\n"
                    f"**Cogs loaded:** {len(loaded_names)}"
                ),
                inline=False,
            )
            # Lists whatever is actually loaded on THIS bot instance — not a fixed
            # catalog. Each bot only loads whichever cogs were selected for it, so
            # comparing against "every cog that exists in the repo" would falsely
            # flag intentionally-absent ones as broken.
            chunks, chunk, chunk_len = [], [], 0
            for name in loaded_names:
                token = f"`{name}`"
                if chunk and chunk_len + len(token) + 2 > 1000:
                    chunks.append(chunk)
                    chunk, chunk_len = [], 0
                chunk.append(token)
                chunk_len += len(token) + 2
            if chunk:
                chunks.append(chunk)
            for i, ch in enumerate(chunks):
                embed.add_field(name="✅ Loaded Cogs" if i == 0 else "​", value="  ".join(ch), inline=False)

        elif category == "dnd":
            embed.title = "⚔️ DND / Engine"
            core = self.bot.cogs.get("EngineCore")
            cog_lines = [
                f"{_loaded('DungeonMasterCog')} `DungeonMasterCog`",
                f"{_loaded('EngineCore')} `EngineCore`",
                f"{_loaded('CharacterCog')} `CharacterCog`",
                f"{_loaded('ShopCog')} `ShopCog`",
                f"{_loaded('RecipesCog')} `RecipesCog`",
                f"{_loaded('PartiesCog')} `PartiesCog`",
                f"{_loaded('ScribeCog')} `ScribeCog`",
            ]
            embed.add_field(name="🔧 Cogs", value="\n".join(cog_lines), inline=True)
            if core:
                r = core.registry
                embed.add_field(
                    name="📋 Registry",
                    value=(
                        f"**Races:** {list(r.races.keys()) or '—'}\n"
                        f"**Classes:** {list(r.classes.keys()) or '—'}\n"
                        f"**Items:** {len(r.items)}\n"
                        f"**Shop items:** {len(r.shop_items)}\n"
                        f"**Campaigns:** {len(r.campaigns)}\n"
                        f"**Recipes:** {len(r.recipes)}"
                    ),
                    inline=True,
                )
                eng_mod  = sys.modules.get(type(core).__module__)
                dlc_root = getattr(eng_mod, "_DLC_ROOT", None)
                if dlc_root and dlc_root.is_dir():
                    dlc_lines = [f"**Root:** `{dlc_root}`"]
                    for cat_dir in sorted(dlc_root.iterdir()):
                        if not cat_dir.is_dir() or cat_dir.name.startswith("_"):
                            continue
                        plugins = [
                            p.name for p in sorted(cat_dir.iterdir())
                            if p.is_dir() and not p.name.startswith("_")
                            and (p / "variables.py").exists()
                        ]
                        if plugins:
                            dlc_lines.append(f"**{cat_dir.name}/**: {', '.join(f'`{p}`' for p in plugins)}")
                    embed.add_field(name="📦 DLC Plugins", value="\n".join(dlc_lines), inline=False)
            dm = self.bot.cogs.get("DungeonMasterCog")
            if dm and hasattr(dm, "_runs"):
                embed.add_field(
                    name="⚔️ Active Runs", value=str(len(dm._runs)) or "0", inline=True)

        elif category == "casino":
            embed.title = "🎰 Casino"
            games = [
                ("🎰 Slots",               "SlotsCog"),
                ("🃏 Blackjack",           "BlackjackCog"),
                ("🎲 Baccarat",            "BaccaratCog"),
                ("🎡 Roulette",            "RouletteCog"),
                ("🎲 Gamble",              "GambleCog"),
                ("🪙 Coinflip",            "CoinFlipCog"),
                ("📈 Higher / Lower",      "HigherLowerCog"),
                ("🐎 Horse Racing",        "HorseRacingCog"),
                ("🐸 Crossy Road",         "CrossyRoadCog"),
                ("✂️ Rock Paper Scissors", "RPSCog"),
                ("♠️ Poker",               "PokerCog"),
                ("💸 Broke Boy",           "BrokeBoy"),
            ]
            lines = [
                f"{_loaded(cog)} **{name}** `{cog}`" for name, cog in games
            ]
            embed.add_field(name="🎮 Games", value="\n".join(lines), inline=False)

        elif category == "general":
            embed.title = "🌐 General"
            mods = [
                ("🎉 Welcome System", "WelcomeSystem"),
                ("🏷️ Self Roles",     "SelfRoles"),
                ("📜 Rules",           "Rules"),
                ("❓ Help",            "HelpCog"),
            ]
            lines = [f"{_loaded(cog)} **{name}** `{cog}`" for name, cog in mods]
            embed.add_field(name="Modules", value="\n".join(lines), inline=False)

        elif category == "user":
            embed.title = "👤 User"
            mods = [
                ("🏦 Bank",        "BankCog"),
                ("🏆 Leaderboard", "LeaderboardCog"),
                ("📊 Stats",       "StatsCog"),
            ]
            lines = [f"{_loaded(cog)} **{name}** `{cog}`" for name, cog in mods]
            embed.add_field(name="Modules", value="\n".join(lines), inline=False)

        elif category == "quotes":
            embed.title = "💬 Quotes"
            embed.add_field(
                name="Module", value=f"{_loaded('QuotesCog')} `QuotesCog`", inline=False)
            dm = self.bot.cogs.get("DungeonMasterCog")
            if dm and hasattr(dm, "db"):
                try:
                    count = dm.db.execute("SELECT COUNT(*) FROM quotes")[0][0]
                    embed.add_field(name="📝 Total Quotes", value=f"{count:,}", inline=True)
                except Exception:
                    pass

        elif category == "events":
            embed.title = "🎉 Events"
            mods = [
                ("🎰 Casino Event",     "CasinoEventCog"),
                ("✨ Multiplier Event", "MultiplierEventCog"),
            ]
            lines = [f"{_loaded(cog)} **{name}** `{cog}`" for name, cog in mods]
            embed.add_field(name="Modules", value="\n".join(lines), inline=False)

        elif category == "database":
            embed.title = "🗄️ Database"
            dm = self.bot.cogs.get("DungeonMasterCog")
            if not (dm and hasattr(dm, "db")):
                embed.add_field(
                    name="Status",
                    value="❌ DungeonMasterCog not loaded — cannot access DB",
                    inline=False,
                )
            else:
                db = dm.db
                _tables = [
                    ("dnd_characters",  "DND Characters"),
                    ("dnd_inventory",   "DND Inventory rows"),
                    ("dnd_runs",        "DND Active runs"),
                    ("balances",        "Balances"),
                    ("transactions",    "Transactions"),
                    ("quotes",          "Quotes"),
                    ("slot_sessions",   "Slot sessions"),
                    ("blackjack_hands", "Blackjack hands"),
                ]
                db_lines = ["✅ Connected"]
                for tbl, label in _tables:
                    try:
                        n = db.execute(f"SELECT COUNT(*) FROM {tbl}")[0][0]
                        db_lines.append(f"**{label}:** {n:,}")
                    except Exception:
                        db_lines.append(f"**{label}:** *(not found)*")
                embed.add_field(
                    name="📊 Table Counts", value="\n".join(db_lines), inline=False)

        elif category == "config":
            embed.title = "⚙️ Config"
            cfg = BotConfig()
            allowed = cfg.allowed_channels()
            allowed_txt = (
                "\n".join(f"<#{c['id']}> `#{c['name']}`" for c in allowed)
                if allowed
                else f"*(default: {', '.join('#' + n for n in cfg.allowed_names())})*"
            )
            cp = cfg.control_panel()
            cp_txt = (f"<#{cp['id']}> `#{cp['name']}`" if cp
                      else f"*(default: #{cfg.control_panel_name()})*")
            staff = cfg.staff_role_names()
            staff_txt = (", ".join(f"`{r}`" for r in staff) if staff else "*(none set)*")
            embed.add_field(name="📺 Allowed Channels", value=allowed_txt, inline=False)
            embed.add_field(name="🎛️ Control Panel",    value=cp_txt,      inline=False)
            embed.add_field(name="👮 Staff Roles",       value=staff_txt,   inline=False)

        else:
            embed.title = "❓ Unknown Category"
            embed.description = f"Category `{category}` is not recognised."

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ConfigCog(bot))
    log.info("✅ General/Config cog loaded")
