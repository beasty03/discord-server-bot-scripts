import discord
from discord.ext import commands
from discord import app_commands
import logging
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('rules_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)
from forge_db import ForgeDB

ForgeDB.declare_schema(
    tables=[
        """CREATE TABLE IF NOT EXISTS rules_list (
               id   INTEGER PRIMARY KEY AUTOINCREMENT,
               text TEXT NOT NULL
           )""",
        """CREATE TABLE IF NOT EXISTS rules_config (
               key   TEXT PRIMARY KEY,
               value TEXT NOT NULL
           )""",
    ],
)

log = logging.getLogger("launcher")


class Rules(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    # ── Database ──────────────────────────────────────────────────────────────

    def _get_cfg(self, key: str) -> str | None:
        rows = self.db.execute("SELECT value FROM rules_config WHERE key = ?", (key,))
        return rows[0][0] if rows else None

    def _set_cfg(self, key: str, value: str):
        self.db.execute(
            "INSERT OR REPLACE INTO rules_config (key, value) VALUES (?, ?)",
            (key, str(value)),
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_rules(self) -> list[tuple[int, str]]:
        rows = self.db.execute("SELECT id, text FROM rules_list ORDER BY id")
        return rows if rows else []

    def _build_embed(self) -> discord.Embed:
        rules  = self._get_rules()
        embed  = discord.Embed(title=var.RULES_TITLE, color=var.RULES_COLOR)
        if rules:
            embed.description = "\n\n".join(
                f"**{i + 1}.** {text}" for i, (_, text) in enumerate(rules)
            )
        else:
            embed.description = "*No rules have been added yet.*"
        embed.set_footer(text=f"{var.SERVER_NAME} — Breaking these rules may result in a mute, kick, or ban.")
        return embed

    def _resolve_channel(self) -> discord.TextChannel | None:
        guild = self.bot.get_guild(var.GUILD_ID)
        if guild is None:
            return None
        cid = self._get_cfg("channel_id")
        if cid:
            ch = guild.get_channel(int(cid))
            if ch:
                return ch
        return discord.utils.get(guild.text_channels, name=var.DEFAULT_CHANNEL_NAME)

    async def _sync_message(self):
        channel = self._resolve_channel()
        if channel is None:
            log.warning("[Rules] No channel configured — cannot sync rules message.")
            return

        embed = self._build_embed()
        mid   = self._get_cfg("message_id")

        if mid:
            try:
                msg = await channel.fetch_message(int(mid))
                await msg.edit(embed=embed)
                return
            except discord.NotFound:
                pass

        msg = await channel.send(embed=embed)
        self._set_cfg("message_id", str(msg.id))

    # ── Slash commands ────────────────────────────────────────────────────────

    @app_commands.command(name="rules_channel", description="Set the channel where the rules embed is posted.")
    @app_commands.describe(channel="Text channel to post the rules in")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def rules_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self._set_cfg("channel_id", str(channel.id))
        self._set_cfg("message_id", "")
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"Rules channel set to {channel.mention}. Run `/rules_post` to post the rules there.",
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )

    @app_commands.command(name="rules_add", description="Add a new rule to the list.")
    @app_commands.describe(rule="The rule text to add")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def rules_add(self, interaction: discord.Interaction, rule: str):
        self.db.execute("INSERT INTO rules_list (text) VALUES (?)", (rule,))
        count = len(self._get_rules())
        await interaction.response.send_message(
            embed=discord.Embed(description=f"Rule **#{count}** added.", color=var.COLOR_INFO),
            ephemeral=True,
        )
        await self._sync_message()

    @app_commands.command(name="rules_remove", description="Remove a rule by its number.")
    @app_commands.describe(number="Rule number to remove (as shown in the rules list)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def rules_remove(self, interaction: discord.Interaction, number: int):
        rules = self._get_rules()
        if not rules or number < 1 or number > len(rules):
            await interaction.response.send_message(
                f"Rule #{number} doesn't exist — there are currently **{len(rules)}** rules.",
                ephemeral=True,
            )
            return
        rule_id, rule_text = rules[number - 1]
        self.db.execute("DELETE FROM rules_list WHERE id = ?", (rule_id,))
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"Rule **#{number}** removed: *{rule_text}*",
                color=var.COLOR_INFO,
            ),
            ephemeral=True,
        )
        await self._sync_message()

    @app_commands.command(name="rules_edit", description="Edit an existing rule.")
    @app_commands.describe(number="Rule number to edit", rule="The new rule text")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def rules_edit(self, interaction: discord.Interaction, number: int, rule: str):
        rules = self._get_rules()
        if not rules or number < 1 or number > len(rules):
            await interaction.response.send_message(
                f"Rule #{number} doesn't exist — there are currently **{len(rules)}** rules.",
                ephemeral=True,
            )
            return
        rule_id, _ = rules[number - 1]
        self.db.execute("UPDATE rules_list SET text = ? WHERE id = ?", (rule, rule_id))
        await interaction.response.send_message(
            embed=discord.Embed(description=f"Rule **#{number}** updated.", color=var.COLOR_INFO),
            ephemeral=True,
        )
        await self._sync_message()

    @app_commands.command(name="rules_post", description="Post or refresh the rules embed in the rules channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def rules_post(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self._sync_message()
        await interaction.followup.send("Rules posted!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Rules(bot))
