"""
DungeonMaster_data — single import point for all game data.

Usage in character/variables.py:
    _data = _load('dm_data', Path(__file__).parent.parent / 'DungeonMaster_data' / 'data.py')
    RACES  = _data.RACES
    CLASSES = _data.CLASSES
    ...
"""

from pathlib import Path
import importlib.util as _ilu


def _load(name: str, path: Path):
    spec = _ilu.spec_from_file_location(name, path)
    mod  = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_root      = Path(__file__).parent
_human     = _load("data_human",         _root / "races"   / "human.py")
_dwarf     = _load("data_dwarf",         _root / "races"   / "dwarf.py")
_elf       = _load("data_elf",           _root / "races"   / "elf.py")
_fighter   = _load("data_fighter",       _root / "classes" / "fighter.py")
_ranger    = _load("data_ranger",        _root / "classes" / "ranger.py")
_wizard    = _load("data_wizard",        _root / "classes" / "wizard.py")
_wiz_spells = _load("data_wizard_spells", _root / "spells"  / "wizard_spells.py")

# ── Assembled exports ────────────────────────────────────────────────────────

RACES = [_human.RACE, _dwarf.RACE, _elf.RACE]

CLASSES = [_fighter.CLASS, _ranger.CLASS, _wizard.CLASS]

# {race_id: [trait_dict, ...]}
RACE_TRAITS = {
    "human": _human.TRAITS,
    "dwarf": _dwarf.TRAITS,
    "elf":   _elf.TRAITS,
}

# {class_id: [feature_dict, ...]}
CLASS_FEATURES = {
    "fighter": _fighter.CLASS_FEATURES,
    "ranger":  _ranger.CLASS_FEATURES,
    "wizard":  _wizard.CLASS_FEATURES,
}

# {class_id: [combat_feature_dict, ...]}
COMBAT_FEATURES = {
    "fighter": _fighter.COMBAT_FEATURES,
    "ranger":  _ranger.COMBAT_FEATURES,
    "wizard":  _wizard.COMBAT_FEATURES,
}

# {subclass_id: [combat_feature_dict, ...]}
SUBCLASS_COMBAT_FEATURES = {
    **_fighter.SUBCLASS_COMBAT_FEATURES,
    **_ranger.SUBCLASS_COMBAT_FEATURES,
    **_wizard.SUBCLASS_COMBAT_FEATURES,
}

# {(class_id, level): choice_dict}
LEVEL_UP_CHOICES = {
    **_fighter.LEVEL_UP_CHOICES,
    **_human.LEVEL_UP_CHOICES,
    **_dwarf.LEVEL_UP_CHOICES,
    **_elf.LEVEL_UP_CHOICES,
    **_ranger.LEVEL_UP_CHOICES,
    **_wizard.LEVEL_UP_CHOICES,
}

# Ranger favored enemy keyword map — used by the engine to match enemy names
RANGER_FAVORED_ENEMY_KEYWORDS: dict[str, list[str]] = _ranger.FAVORED_ENEMY_KEYWORDS

# Wizard spell data — used by the engine for preparation and combat
WIZARD_CANTRIPS:        set[str]       = _wiz_spells.CANTRIPS
WIZARD_STARTING_SPELLS: list[str]      = _wiz_spells.STARTING_SPELLS
WIZARD_SPELLS:          list[dict]     = _wiz_spells.SPELLS
