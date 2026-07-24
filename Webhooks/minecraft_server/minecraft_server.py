import asyncio
import importlib.util as _ilu
import json
import logging
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

_spec = _ilu.spec_from_file_location('minecraft_server_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

log = logging.getLogger("launcher")

_CONFIG_FILE = Path(__file__).parent / "mc_servers_config.json"

STATE_EMOJI = {
    "running":  "🟢",
    "starting": "🟡",
    "stopping": "🟠",
    "offline":  "🔴",
}
STATE_COLOR = {
    "running":  var.COLOR_OK,
    "starting": var.COLOR_WARN,
    "stopping": var.COLOR_WARN,
    "offline":  var.COLOR_ERROR,
}


# ============================================================================
# SHARED EMBEDS
# ============================================================================

def _not_configured_embed() -> discord.Embed:
    return discord.Embed(
        description=(
            "⚠️ No Minecraft servers are configured yet. Add one with "
            "`/set_mc_server`, or under `minecraft_servers` in the config file."
        ),
        color=var.COLOR_ERROR,
    )


def _unknown_server_embed(name: str, known_names) -> discord.Embed:
    known = ", ".join(f"`{n}`" for n in known_names) or "*(none configured)*"
    return discord.Embed(
        description=f"⚠️ Unknown server `{name}`. Configured servers: {known}",
        color=var.COLOR_ERROR,
    )


def _effective(server_cfg: dict) -> tuple[str, str, str]:
    """Merges a server entry with the shared PANEL_URL/CLIENT_API_KEY fallbacks."""
    panel_url = (server_cfg.get('panel_url') or var.PANEL_URL).rstrip('/')
    api_key   = server_cfg.get('client_api_key') or var.CLIENT_API_KEY
    server_id = server_cfg.get('server_id', '')
    return panel_url, api_key, server_id


def _require_mc_admin(interaction: discord.Interaction) -> bool:
    """Administrators always pass; otherwise the member needs the role set via /set_mc_adminrole.
    If no role has been configured yet, only Administrators can use these commands."""
    if not isinstance(interaction.user, discord.Member):
        return False
    if interaction.user.guild_permissions.administrator:
        return True
    cog = interaction.client.get_cog("MinecraftServerCog")
    role_id = cog._cfg.get("admin_role_id") if cog else None
    if role_id is None:
        return False
    return any(r.id == role_id for r in interaction.user.roles)


# ============================================================================
# PTERODACTYL CLIENT API HELPERS
# ============================================================================

def _extract_error(data: dict | None) -> str:
    if not data:
        return "Unknown error"
    errors = data.get("errors") or []
    if errors:
        return errors[0].get("detail") or errors[0].get("code") or "Unknown error"
    return "Unknown error"


async def _api_request(panel_url: str, api_key: str, method: str, path: str, json_body: dict | None = None):
    """Returns (ok, data_or_error_message)."""
    url = f"{panel_url}/api/client{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, url, headers=headers, json=json_body,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 204:
                    return True, None
                data = await resp.json(content_type=None)
                if resp.status >= 400:
                    return False, _extract_error(data)
                return True, data
    except Exception as exc:
        log.error("[MinecraftServer] API request failed: %s", exc)
        return False, str(exc)


async def _get_state(panel_url: str, api_key: str, server_id: str) -> tuple[str | None, dict | None]:
    ok, data = await _api_request(panel_url, api_key, "GET", f"/servers/{server_id}/resources")
    if not ok or not data:
        return None, None
    attrs = data.get("attributes", {})
    return attrs.get("current_state"), attrs.get("resources")


async def _send_power(panel_url: str, api_key: str, server_id: str, signal: str) -> tuple[bool, str | None]:
    return await _api_request(panel_url, api_key, "POST", f"/servers/{server_id}/power", {"signal": signal})


# ============================================================================
# CONFIRMATION VIEW (used by /mc_stop and /mc_restart)
# ============================================================================

class ConfirmPowerView(discord.ui.View):

    def __init__(self, panel_url: str, api_key: str, server_id: str, signal: str, verb: str):
        super().__init__(timeout=var.CONFIRM_TIMEOUT)
        self.panel_url = panel_url
        self.api_key   = api_key
        self.server_id = server_id
        self.signal    = signal
        self.verb      = verb
        self.resolved  = False

    def _disable_all(self):
        for item in self.children:
            item.disabled = True

    async def on_timeout(self):
        self._disable_all()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.resolved:
            await interaction.response.send_message("This confirmation has expired.", ephemeral=True)
            return
        self.resolved = True
        self._disable_all()
        await interaction.response.defer()

        ok, err = await _send_power(self.panel_url, self.api_key, self.server_id, self.signal)
        if ok:
            embed = discord.Embed(description=f"✅ **{self.verb.capitalize()}** signal sent.", color=var.COLOR_OK)
        else:
            embed = discord.Embed(description=f"❌ Failed to {self.verb} the server: {err}", color=var.COLOR_ERROR)
        await interaction.edit_original_response(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.resolved:
            await interaction.response.send_message("This confirmation has expired.", ephemeral=True)
            return
        self.resolved = True
        self._disable_all()
        embed = discord.Embed(description="Cancelled — no signal was sent.", color=var.COLOR_WARN)
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()


# ============================================================================
# COG
# ============================================================================

class MinecraftServerCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cfg = self._load_cfg()

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            role_id = self._cfg.get("admin_role_id")
            msg = (
                f"❌ You need the <@&{role_id}> role (or Administrator) to use this command."
                if role_id else
                "❌ You need Administrator, or a role set via `/set_mc_adminrole`, to use this command."
            )
            embed = discord.Embed(description=msg, color=var.COLOR_ERROR)
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            raise error

    # ── Runtime config (JSON, layered on top of variables.py) ─────────────────
    # variables.py / the shared config file is the static baseline (e.g. what
    # was known at deploy time). /set_mc_server writes here instead, so a new
    # server — including one on a totally different panel/host — can be added
    # or changed without touching config files or restarting the bot.

    def _load_cfg(self) -> dict:
        if _CONFIG_FILE.exists():
            try:
                return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_cfg(self):
        _CONFIG_FILE.write_text(json.dumps(self._cfg, indent=2), encoding="utf-8")

    def _servers(self) -> dict:
        """Static servers from variables.py, overridden/extended by runtime ones."""
        merged = dict(var.SERVERS)
        merged.update(self._cfg.get("servers", {}))
        return merged

    def _default_name(self) -> str | None:
        servers = self._servers()
        dn = self._cfg.get("default_server") or var.DEFAULT_SERVER_NAME
        if dn in servers:
            return dn
        return next(iter(servers), None)

    def _resolve_server(self, name: str | None) -> tuple[str | None, dict | None]:
        """Returns (name, server_cfg). name is None only when nothing could be resolved."""
        servers = self._servers()
        if not servers:
            return None, None
        if name:
            if name in servers:
                return name, servers[name]
            for n in servers:
                if n.lower() == name.lower():
                    return n, servers[n]
            return name, None  # signals "given but not found"
        dn = self._default_name()
        if dn:
            return dn, servers[dn]
        return None, None

    async def _server_autocomplete(self, _interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        current_l = current.lower()
        choices = []
        for name in self._servers():
            if current_l in name.lower():
                choices.append(app_commands.Choice(name=name, value=name))
        return choices[:25]

    # ── /mc_list ──────────────────────────────────────────────────────────────

    @app_commands.command(name="mc_list", description="List all configured Minecraft servers and their current state.")
    async def mc_list(self, interaction: discord.Interaction):
        servers = self._servers()
        if not servers:
            await interaction.response.send_message(embed=_not_configured_embed(), ephemeral=True)
            return

        await interaction.response.defer()

        async def _one(name: str, cfg: dict):
            panel_url, api_key, server_id = _effective(cfg)
            state, _resources = await _get_state(panel_url, api_key, server_id)
            return name, state, cfg.get("description")

        results = await asyncio.gather(*(_one(n, c) for n, c in servers.items()))

        default_name = self._default_name()
        embed = discord.Embed(title="🗺️ Minecraft Servers", color=var.COLOR_INFO)
        for name, state, description in results:
            emoji = STATE_EMOJI.get(state, "⚪")
            default_tag = "*(default)* — " if name == default_name else ""
            desc_line = f"\n{description}" if description else ""
            embed.add_field(
                name=f"{emoji} {name}",
                value=f"{default_tag}`{state or 'unreachable'}`{desc_line}",
                inline=False,
            )
        await interaction.followup.send(embed=embed)

    # ── /mc_status ────────────────────────────────────────────────────────────

    @app_commands.command(name="mc_status", description="Check a Minecraft server's current power state.")
    @app_commands.describe(server="Which server (defaults to the configured default)")
    async def mc_status(self, interaction: discord.Interaction, server: str | None = None):
        name, cfg = self._resolve_server(server)
        if name is None:
            await interaction.response.send_message(embed=_not_configured_embed(), ephemeral=True)
            return
        if cfg is None:
            await interaction.response.send_message(embed=_unknown_server_embed(server, self._servers()), ephemeral=True)
            return

        await interaction.response.defer()
        panel_url, api_key, server_id = _effective(cfg)
        state, resources = await _get_state(panel_url, api_key, server_id)
        if state is None:
            await interaction.followup.send(embed=discord.Embed(
                description=f"⚠️ Could not reach the panel API for **{name}**. Check the Panel URL and API key.",
                color=var.COLOR_ERROR,
            ))
            return

        emoji = STATE_EMOJI.get(state, "⚪")
        description = cfg.get("description")
        desc_prefix = f"{description}\n\n" if description else ""
        embed = discord.Embed(
            title=f"{emoji} {name}",
            description=f"{desc_prefix}Current state: `{state}`",
            color=STATE_COLOR.get(state, var.COLOR_INFO),
        )
        if resources:
            uptime_ms = resources.get("uptime", 0)
            embed.add_field(name="CPU", value=f"{resources.get('cpu_absolute', 0):.1f}%", inline=True)
            mem_mb = resources.get("memory_bytes", 0) / (1024 * 1024)
            embed.add_field(name="Memory", value=f"{mem_mb:.0f} MB", inline=True)
            embed.add_field(name="Uptime", value=f"{uptime_ms // 1000 // 60} min", inline=True)
        await interaction.followup.send(embed=embed)

    @mc_status.autocomplete("server")
    async def mc_status_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._server_autocomplete(interaction, current)

    # ── /mc_start ─────────────────────────────────────────────────────────────

    @app_commands.command(name="mc_start", description="Start a Minecraft server.")
    @app_commands.describe(server="Which server (defaults to the configured default)")
    @app_commands.check(_require_mc_admin)
    async def mc_start(self, interaction: discord.Interaction, server: str | None = None):
        name, cfg = self._resolve_server(server)
        if name is None:
            await interaction.response.send_message(embed=_not_configured_embed(), ephemeral=True)
            return
        if cfg is None:
            await interaction.response.send_message(embed=_unknown_server_embed(server, self._servers()), ephemeral=True)
            return

        await interaction.response.defer()
        panel_url, api_key, server_id = _effective(cfg)
        state, _resources = await _get_state(panel_url, api_key, server_id)
        if state in ("running", "starting"):
            await interaction.followup.send(embed=discord.Embed(
                description=f"ℹ️ **{name}** is already `{state}`.",
                color=var.COLOR_WARN,
            ))
            return

        ok, err = await _send_power(panel_url, api_key, server_id, "start")
        if ok:
            await interaction.followup.send(embed=discord.Embed(
                description=f"🟢 Start signal sent to **{name}** — it's booting up.",
                color=var.COLOR_OK,
            ))
        else:
            await interaction.followup.send(embed=discord.Embed(
                description=f"❌ Failed to start **{name}**: {err}",
                color=var.COLOR_ERROR,
            ))

    @mc_start.autocomplete("server")
    async def mc_start_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._server_autocomplete(interaction, current)

    # ── /mc_stop ──────────────────────────────────────────────────────────────

    @app_commands.command(name="mc_stop", description="Stop a Minecraft server (disconnects all players).")
    @app_commands.describe(server="Which server (defaults to the configured default)")
    @app_commands.check(_require_mc_admin)
    async def mc_stop(self, interaction: discord.Interaction, server: str | None = None):
        name, cfg = self._resolve_server(server)
        if name is None:
            await interaction.response.send_message(embed=_not_configured_embed(), ephemeral=True)
            return
        if cfg is None:
            await interaction.response.send_message(embed=_unknown_server_embed(server, self._servers()), ephemeral=True)
            return

        await interaction.response.defer()
        panel_url, api_key, server_id = _effective(cfg)
        state, _resources = await _get_state(panel_url, api_key, server_id)
        if state == "offline":
            await interaction.followup.send(embed=discord.Embed(
                description=f"ℹ️ **{name}** is already `offline`.",
                color=var.COLOR_WARN,
            ))
            return

        embed = discord.Embed(
            description=f"⚠️ This will **stop {name} and disconnect all players**. Are you sure?",
            color=var.COLOR_WARN,
        )
        await interaction.followup.send(embed=embed, view=ConfirmPowerView(panel_url, api_key, server_id, "stop", "stop"))

    @mc_stop.autocomplete("server")
    async def mc_stop_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._server_autocomplete(interaction, current)

    # ── /mc_restart ───────────────────────────────────────────────────────────

    @app_commands.command(name="mc_restart", description="Restart a Minecraft server (disconnects all players).")
    @app_commands.describe(server="Which server (defaults to the configured default)")
    @app_commands.check(_require_mc_admin)
    async def mc_restart(self, interaction: discord.Interaction, server: str | None = None):
        name, cfg = self._resolve_server(server)
        if name is None:
            await interaction.response.send_message(embed=_not_configured_embed(), ephemeral=True)
            return
        if cfg is None:
            await interaction.response.send_message(embed=_unknown_server_embed(server, self._servers()), ephemeral=True)
            return

        await interaction.response.defer()
        panel_url, api_key, server_id = _effective(cfg)
        embed = discord.Embed(
            description=f"⚠️ This will **restart {name} and disconnect all players**. Are you sure?",
            color=var.COLOR_WARN,
        )
        await interaction.followup.send(embed=embed, view=ConfirmPowerView(panel_url, api_key, server_id, "restart", "restart"))

    @mc_restart.autocomplete("server")
    async def mc_restart_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._server_autocomplete(interaction, current)

    # ── /set_mc_server ────────────────────────────────────────────────────────

    @app_commands.command(name="set_mc_server", description="Add or update a Minecraft server the bot can control.")
    @app_commands.describe(
        name="Name used to select this server, and shown in embeds (e.g. 'Survival')",
        server_id="The server's short identifier from its panel URL, e.g. the abc12345 in /server/abc12345 (not the long UUID)",
        description="Optional short blurb shown alongside this server in embeds (e.g. 'Main survival world')",
        panel_url="Only set this if this server lives on a DIFFERENT panel/host than the shared default",
        client_api_key="Only set this if this server needs its own Client API key (Panel → Account → API Credentials)",
    )
    @app_commands.check(_require_mc_admin)
    async def set_mc_server(
        self,
        interaction: discord.Interaction,
        name: str,
        server_id: str,
        description: str | None = None,
        panel_url: str | None = None,
        client_api_key: str | None = None,
    ):
        servers = self._cfg.setdefault("servers", {})
        entry = servers.get(name, {}).copy()
        entry["server_id"] = server_id
        if description:
            entry["description"] = description
        if panel_url:
            entry["panel_url"] = panel_url.rstrip("/")
        if client_api_key:
            entry["client_api_key"] = client_api_key
        servers[name] = entry
        self._save_cfg()

        if len(self._servers()) == 1 and not self._cfg.get("default_server"):
            self._cfg["default_server"] = name
            self._save_cfg()

        overrides = []
        if panel_url:
            overrides.append("its own panel URL")
        if client_api_key:
            overrides.append("its own API key")
        override_note = f" — using {' and '.join(overrides)}" if overrides else " — using the shared panel URL/API key"

        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Saved server **{name}**{override_note}.",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )

    @set_mc_server.autocomplete("name")
    async def set_mc_server_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._server_autocomplete(interaction, current)

    # ── /remove_mc_server ─────────────────────────────────────────────────────

    @app_commands.command(name="remove_mc_server", description="Remove a server added via /set_mc_server.")
    @app_commands.describe(name="Which server to remove")
    @app_commands.check(_require_mc_admin)
    async def remove_mc_server(self, interaction: discord.Interaction, name: str):
        servers = self._cfg.get("servers", {})
        if name not in servers:
            note = (
                " It exists in the static config file, not something added via `/set_mc_server` — "
                "remove it there instead."
                if name in var.SERVERS else ""
            )
            await interaction.response.send_message(
                embed=discord.Embed(description=f"⚠️ No runtime entry found for `{name}`.{note}", color=var.COLOR_ERROR),
                ephemeral=True,
            )
            return

        del servers[name]
        self._cfg["servers"] = servers
        if self._cfg.get("default_server") == name:
            self._cfg["default_server"] = None
        self._save_cfg()

        await interaction.response.send_message(
            embed=discord.Embed(description=f"🗑️ Removed `{name}`.", color=var.COLOR_OK),
            ephemeral=True,
        )

    @remove_mc_server.autocomplete("name")
    async def remove_mc_server_autocomplete(self, interaction: discord.Interaction, current: str):
        current_l = current.lower()
        choices = []
        for name in self._cfg.get("servers", {}):
            if current_l in name.lower():
                choices.append(app_commands.Choice(name=name, value=name))
        return choices[:25]

    # ── /set_mc_default ───────────────────────────────────────────────────────

    @app_commands.command(name="set_mc_default", description="Set which server /mc_status, /mc_start, /mc_stop, /mc_restart act on by default.")
    @app_commands.describe(name="Which server should be the default")
    @app_commands.check(_require_mc_admin)
    async def set_mc_default(self, interaction: discord.Interaction, name: str):
        servers = self._servers()
        if name not in servers:
            await interaction.response.send_message(embed=_unknown_server_embed(name, servers), ephemeral=True)
            return

        self._cfg["default_server"] = name
        self._save_cfg()
        await interaction.response.send_message(
            embed=discord.Embed(description=f"✅ Default server set to **{name}**.", color=var.COLOR_OK),
            ephemeral=True,
        )

    @set_mc_default.autocomplete("name")
    async def set_mc_default_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._server_autocomplete(interaction, current)

    # ── /view_mc_config ───────────────────────────────────────────────────────

    @app_commands.command(name="view_mc_config", description="Show all configured Minecraft servers and where each setting comes from.")
    @app_commands.check(_require_mc_admin)
    async def view_mc_config(self, interaction: discord.Interaction):
        servers = self._servers()
        if not servers:
            await interaction.response.send_message(embed=_not_configured_embed(), ephemeral=True)
            return

        runtime_names = set(self._cfg.get("servers", {}).keys())
        default_name = self._default_name()

        embed = discord.Embed(title="⚙️ Minecraft Server Config", color=var.COLOR_INFO)
        for name, cfg in servers.items():
            panel_url, api_key, server_id = _effective(cfg)
            masked = f"{api_key[:6]}…" if api_key else "*(none set)*"
            source = "`/set_mc_server`" if name in runtime_names else "config file"
            default_tag = " ⭐" if name == default_name else ""
            desc_line = f"\n{cfg['description']}" if cfg.get("description") else ""
            embed.add_field(
                name=f"{name}{default_tag}",
                value=f"Server ID: `{server_id or '—'}`\nPanel: `{panel_url or '—'}`\nAPI key: `{masked}`\nSource: {source}{desc_line}",
                inline=False,
            )
        admin_role_id = self._cfg.get("admin_role_id")
        embed.set_footer(text="Admin role: not set (Administrator required)" if admin_role_id is None else f"Admin role ID: {admin_role_id}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /set_mc_adminrole ─────────────────────────────────────────────────────

    @app_commands.command(name="set_mc_adminrole", description="Set the role required to use Minecraft server commands.")
    @app_commands.describe(role="The role that should be allowed to manage Minecraft servers (Administrators can always use these commands regardless)")
    @app_commands.check(_require_mc_admin)
    async def set_mc_adminrole(self, interaction: discord.Interaction, role: discord.Role):
        self._cfg["admin_role_id"] = role.id
        self._save_cfg()
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ **{role.name}** can now use Minecraft server commands (Administrators always can too).",
                color=var.COLOR_OK,
            ),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MinecraftServerCog(bot))
    log.info("✅ Webhooks/MinecraftServer cog loaded")
