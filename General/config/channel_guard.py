"""
channel_guard.py
================
Global interaction check registered via bot.tree.add_check() by ConfigCog.

Rules
-----
- Regular commands   → allowed channels only  (default: #general)
- Admin commands     → control-panel channel + staff role
- /help              → always allowed everywhere

Admin commands are detected by name prefix ("set_", "add_allowed_channel",
"remove_allowed_channel", "view_config") or explicit name ("startevent").

Settings persist in General/config/bot_settings.json.
"""

from __future__ import annotations
import json
import discord
from pathlib import Path

# ── Defaults (used before anything is configured) ─────────────────────────────
_DEFAULT_ALLOWED   = ["general"]
_DEFAULT_CP_NAME   = "control-panel"
_DEFAULT_STAFF     = ["Admin", "Administrator", "Moderator", "Mod"]

# ── Admin-command detection ───────────────────────────────────────────────────
_ADMIN_PREFIXES = ("set_", "add_allowed_channel", "remove_allowed_channel", "view_config")
_ADMIN_NAMES    = frozenset({"startevent"})
_BYPASS         = frozenset({"help"})   # always allowed everywhere

_CONFIG_FILE = Path(__file__).parent / "bot_settings.json"


# ── Config singleton ──────────────────────────────────────────────────────────

class BotConfig:
    _inst: BotConfig | None = None

    def __new__(cls):
        if cls._inst is None:
            inst = super().__new__(cls)
            inst._d: dict = inst._load()
            cls._inst = inst
        return cls._inst

    def _load(self) -> dict:
        if _CONFIG_FILE.exists():
            try:
                return json.loads(_CONFIG_FILE.read_text("utf-8"))
            except Exception:
                pass
        return {}

    def _save(self):
        _CONFIG_FILE.write_text(json.dumps(self._d, indent=2), "utf-8")

    # ── Allowed channels ──────────────────────────────────────────────────────

    def allowed_channels(self) -> list[dict]:
        """List of {id: int, name: str} dicts."""
        return self._d.get("allowed_channels", [])

    def add_allowed(self, cid: int, name: str):
        ch = self.allowed_channels()
        if not any(c["id"] == cid for c in ch):
            ch.append({"id": cid, "name": name})
            self._d["allowed_channels"] = ch
            self._save()

    def remove_allowed(self, cid: int):
        self._d["allowed_channels"] = [c for c in self.allowed_channels() if c["id"] != cid]
        self._save()

    def allowed_names(self) -> list[str]:
        ch = self.allowed_channels()
        return [c["name"] for c in ch] if ch else _DEFAULT_ALLOWED

    # ── Control panel ─────────────────────────────────────────────────────────

    def control_panel(self) -> dict | None:
        return self._d.get("control_panel")

    def set_control_panel(self, cid: int, name: str):
        self._d["control_panel"] = {"id": cid, "name": name}
        self._save()

    def control_panel_name(self) -> str:
        cp = self.control_panel()
        return cp["name"] if cp else _DEFAULT_CP_NAME

    # ── Staff roles ───────────────────────────────────────────────────────────

    def staff_role_names(self) -> list[str]:
        return self._d.get("staff_role_names", _DEFAULT_STAFF)

    def set_staff_roles(self, names: list[str]):
        self._d["staff_role_names"] = names
        self._save()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _is_admin_command(name: str) -> bool:
    return name in _ADMIN_NAMES or any(name.startswith(p) for p in _ADMIN_PREFIXES)


def _is_staff(interaction: discord.Interaction) -> bool:
    member = interaction.user
    if not isinstance(member, discord.Member):
        return False
    if member.guild_permissions.administrator:
        return True
    role_names = {r.name for r in member.roles}
    return bool(role_names & set(BotConfig().staff_role_names()))


def _in_allowed_channel(interaction: discord.Interaction) -> bool:
    ch  = interaction.channel
    cfg = BotConfig()
    channels = cfg.allowed_channels()

    if channels:
        return ch is not None and any(c["id"] == ch.id for c in channels)

    # Nothing configured yet — fall back to name match
    return hasattr(ch, "name") and ch.name in _DEFAULT_ALLOWED


def _in_control_panel(interaction: discord.Interaction) -> bool:
    ch  = interaction.channel
    cfg = BotConfig()
    cp  = cfg.control_panel()

    if cp:
        return ch is not None and ch.id == cp["id"]

    # Fall back to default name
    return hasattr(ch, "name") and ch.name == _DEFAULT_CP_NAME


def _control_panel_exists(interaction: discord.Interaction) -> bool:
    """True if a control-panel channel is configured or exists by default name."""
    cfg = BotConfig()
    if cfg.control_panel():
        return True
    guild = interaction.guild
    if guild:
        return discord.utils.get(guild.text_channels, name=_DEFAULT_CP_NAME) is not None
    return False


# ── Global check (registered via bot.tree.add_check) ─────────────────────────

async def global_interaction_check(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        return True  # allow DMs / let Discord handle them

    cmd = interaction.command
    if cmd is None:
        return True

    name = cmd.qualified_name  # handles subcommands too

    if name in _BYPASS:
        return True

    # ── Admin command ─────────────────────────────────────────────────────────
    if _is_admin_command(name):
        if not _is_staff(interaction):
            await interaction.response.send_message(
                "🔒 You need an **Admin** or **Moderator** role to use this command.",
                ephemeral=True,
            )
            return False

        if _control_panel_exists(interaction) and not _in_control_panel(interaction):
            cp = BotConfig().control_panel_name()
            await interaction.response.send_message(
                f"🔒 Admin commands can only be used in **#{cp}**.",
                ephemeral=True,
            )
            return False

        return True

    # ── Regular command ───────────────────────────────────────────────────────
    if _in_allowed_channel(interaction) or _in_control_panel(interaction):
        return True

    names = BotConfig().allowed_names()
    await interaction.response.send_message(
        f"⚠️ Commands can only be used in: {', '.join(f'**#{n}**' for n in names)}.",
        ephemeral=True,
    )
    return False
