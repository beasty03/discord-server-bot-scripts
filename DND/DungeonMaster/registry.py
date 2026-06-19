"""
ContentRegistry — in-memory store for all DLC-supplied content.

Starts completely empty. Filled exclusively by DLC register() calls via EngineAPI.
The engine reads from this at runtime; it never writes to it directly.
"""


class ContentRegistry:

    def __init__(self):
        self.classes:      dict[str, dict] = {}
        self.races:        dict[str, dict] = {}
        self.items:        dict[str, dict] = {}
        self.spells:       dict[str, dict] = {}
        self.campaigns:    list[dict]       = []
        self.recipes:      list[dict]       = []
        self.shop_items:   list[dict]       = []
        self.statuses:     dict[str, dict] = {}
        self.damage_types: dict[str, dict] = {}

    # ── Content ───────────────────────────────────────────────────────────────

    def add_class(self, data: dict):
        self.classes[data["id"]] = data

    def add_race(self, data: dict):
        self.races[data["id"]] = data

    def add_item(self, data: dict):
        self.items[data["id"]] = data

    def add_spell(self, data: dict):
        self.spells[data["id"]] = data

    def add_campaign(self, data: dict):
        self.campaigns.append(data)

    def add_recipe(self, data: dict):
        self.recipes.append(data)

    def add_shop_item(self, data: dict):
        if not any(s["id"] == data["id"] for s in self.shop_items):
            self.shop_items.append(data)

    # ── Vocabulary ────────────────────────────────────────────────────────────

    def define_status(self, sid: str, label: str, icon: str = "", effects: dict | None = None):
        self.statuses[sid] = {"id": sid, "label": label, "icon": icon, "effects": effects or {}}

    def define_damage_type(self, tid: str, label: str, icon: str = ""):
        self.damage_types[tid] = {"id": tid, "label": label, "icon": icon}

    # ── Lookups ───────────────────────────────────────────────────────────────

    def get_class(self, class_id: str) -> dict | None:
        return self.classes.get(class_id)

    def get_race(self, race_id: str) -> dict | None:
        return self.races.get(race_id)

    def get_item(self, item_id: str) -> dict | None:
        return self.items.get(item_id)

    def get_spell(self, spell_id: str) -> dict | None:
        return self.spells.get(spell_id)
