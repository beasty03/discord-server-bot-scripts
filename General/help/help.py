import discord
from discord.ext import commands
from discord import app_commands
import logging
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('help_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

log = logging.getLogger("launcher")

# ---------------------------------------------------------------------------
# Category definitions — each entry maps a display name to the cog class
# names whose commands should appear under it.
# ---------------------------------------------------------------------------

CATEGORIES = [
    {
        "label":       "👤 User",
        "value":       "user",
        "description": "Profile & currency — balance, stats, daily, give, leaderboard",
        "color":       var.COLOR_USER,
        "sections": [
            ("🏦 Bank",        "BankCog"),
            ("📊 Stats",       "StatsCog"),
            ("🏆 Leaderboard", "LeaderboardCog"),
        ],
    },
    {
        "label":       "🎰 Casino",
        "value":       "casino",
        "description": "Gambling games — Blackjack, Roulette, Slots, Horse Racing, Coin Flip, RPS, Poker & more",
        "color":       var.COLOR_CASINO,
        "sections": [
            ("🎲 Gamble",          "GambleCog"),
            ("🃏 Blackjack",       "BlackjackCog"),
            ("🎡 Roulette",        "RouletteCog"),
            ("🎴 Higher or Lower", "HigherLowerCog"),
            ("🃏 Baccarat",        "BaccaratCog"),
            ("🎰 Slots",           "SlotsCog"),
            ("🏇 Horse Racing",    "HorseRacingCog"),
            ("🐸 Crossy Road",     "CrossyRoadCog"),
            ("🪙 Coin Flip",           "CoinFlipCog"),
            ("✂️ Rock Paper Scissors", "RPSCog"),
            ("🃏 Poker",              "PokerCog"),
        ],
    },
    {
        "label":       "📋 General",
        "value":       "general",
        "description": "Server utilities — Rules, Self Roles, Quotes",
        "color":       var.COLOR_GENERAL,
        "sections": [
            ("📜 Rules",      "Rules"),
            ("🎭 Self Roles", "SelfRoles"),
            ("💬 Quotes",     "QuotesCog"),
        ],
    },
    {
        "label":       "🔔 Webhooks",
        "value":       "webhooks",
        "description": "Automated posting — Wordle Recap",
        "color":       var.COLOR_WEBHOOKS,
        "sections": [
            ("📰 Wordle Recap", "WordleRecap"),
        ],
    },
    {
        "label":       "🎪 Events",
        "value":       "events",
        "description": "Multiplayer events — Casino events, Multiplier events",
        "color":       var.COLOR_EVENTS,
        "sections": [
            ("🎰 Casino Events",    "CasinoEventCog"),
            ("💰 Multiplier Event", "MultiplierEventCog"),
        ],
    },
    {
        "label":       "⚔️ D&D",
        "value":       "dnd",
        "description": "D&D system — character creation, sheets, adventuring parties",
        "color":       0x8E44AD,
        "sections": [
            ("📜 Character", "CharacterCog"),
            ("🛡️ Parties",   "PartiesCog"),
        ],
    },
    {
        "label":       "🛡️ Admin",
        "value":       "admin",
        "description": "Admin-only configuration — Welcome System",
        "color":       var.COLOR_ADMIN,
        "sections": [
            ("⚙️ Config",        "ConfigCog"),
            ("👋 Welcome System", "WelcomeSystem"),
        ],
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_cog_commands(bot: commands.Bot, cog_name: str) -> list[app_commands.Command]:
    cog = bot.cogs.get(cog_name)
    if cog is None:
        return []
    return cog.get_app_commands()


def _build_home_embed() -> discord.Embed:
    embed = discord.Embed(
        title="📖 Help — Command Overview",
        description=(
            "Use the dropdown below to explore commands by category.\n\n"
            + "\n".join(
                f"**{cat['label']}** — {cat['description']}"
                for cat in CATEGORIES
            )
        ),
        color=var.COLOR_HOME,
    )
    embed.set_footer(text=f"{var.BOT_NAME} · Select a category to see its commands")
    return embed


def _build_category_embed(bot: commands.Bot, value: str) -> discord.Embed:
    cat = next((c for c in CATEGORIES if c["value"] == value), None)
    if cat is None:
        return discord.Embed(title="Unknown category", color=var.COLOR_ERROR)

    embed = discord.Embed(title=f"{cat['label']} Commands", color=cat["color"])
    any_found = False

    for section_name, cog_name in cat["sections"]:
        cmds = _get_cog_commands(bot, cog_name)
        if not cmds:
            continue
        any_found = True
        lines = [f"`/{cmd.name}` — {cmd.description}" for cmd in sorted(cmds, key=lambda c: c.name)]
        embed.add_field(name=section_name, value="\n".join(lines), inline=False)

    if not any_found:
        embed.description = "*No commands found — the relevant cog(s) may not be loaded.*"

    embed.set_footer(text=f"{var.BOT_NAME} · Use the dropdown to switch category")
    return embed


# ---------------------------------------------------------------------------
# UI components
# ---------------------------------------------------------------------------

class CategorySelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        options  = [
            discord.SelectOption(label=cat["label"], value=cat["value"], description=cat["description"])
            for cat in CATEGORIES
        ]
        super().__init__(
            placeholder="Choose a category…",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        embed = _build_category_embed(self.bot, self.values[0])
        await interaction.response.edit_message(embed=embed)


class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=120)
        self.add_item(CategorySelect(bot))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class HelpCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Browse all bot commands grouped by category.")
    async def help(self, interaction: discord.Interaction):
        embed = _build_home_embed()
        await interaction.response.send_message(embed=embed, view=HelpView(self.bot), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
    log.info("✅ General/Help cog loaded")
