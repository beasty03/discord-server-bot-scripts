"""
DLCLoader — scans a root directory for DLC packages at startup.

Discovery rules:
  - Scans <root>/*/variables.py  (one level deep)
  - Folders whose name starts with '_' are skipped (templates, drafts)
  - Each variables.py must expose a register(api) callable
  - Missing register() → warning, skipped
  - Any exception during load → warning, skipped; other DLCs unaffected
"""
import importlib.util
import logging
from pathlib import Path

log = logging.getLogger("engine")


class DLCLoader:

    def __init__(self, api, dlc_root: Path):
        self._api  = api
        self._root = dlc_root

    def load_all(self) -> tuple[int, int]:
        """
        Discover and load all valid DLCs.
        Returns (loaded_count, skipped_count).
        """
        if not self._root.is_dir():
            log.warning("[DLCLoader] root not found: %s", self._root)
            return 0, 0

        loaded = skipped = 0
        for var_file in sorted(self._root.glob("*/variables.py")):
            folder = var_file.parent.name
            if folder.startswith("_"):
                continue
            if self._load_one(var_file, folder):
                loaded  += 1
            else:
                skipped += 1

        return loaded, skipped

    def _load_one(self, path: Path, name: str) -> bool:
        try:
            spec = importlib.util.spec_from_file_location(f"dlc.{name}", path)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            register = getattr(mod, "register", None)
            if not callable(register):
                log.warning("[DLCLoader] '%s' has no register() function — skipped", name)
                return False

            register(self._api)
            log.info("[DLCLoader] ✅ %s", name)
            return True

        except Exception as exc:
            log.warning("[DLCLoader] ❌ '%s' failed: %s", name, exc)
            return False
