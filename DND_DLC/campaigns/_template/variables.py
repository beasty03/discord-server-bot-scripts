"""
CAMPAIGN DLC TEMPLATE
═══════════════════════════════════════════════════════════════════════════════

HOW TO CREATE A CAMPAIGN
─────────────────────────
1. Copy this folder (remove the _ prefix, e.g. "goblin_forest")
2. Edit variables.py — fill in the campaign dict and encounters
3. Restart the bot — the engine loader picks it up automatically
4. Test with /wander

FOLDER NAMING
─────────────
  DND_DLC/campaigns/your_campaign_name/variables.py
  Use snake_case. The folder name is just for you — the campaign id is what the engine uses.

═══════════════════════════════════════════════════════════════════════════════
FIELD REFERENCE
═══════════════════════════════════════════════════════════════════════════════

CAMPAIGN FIELDS
───────────────
  id              str   Unique identifier. Use snake_case. Never change after release.
  name            str   Display name shown on the quest board.
  emoji           str   Single emoji shown next to the name.
  min_level       int   Players below this level cannot queue this campaign.
  min_players     int   Minimum party size (usually 1).
  max_players     int   Maximum party size (usually 4).
  difficulty      str   "Easy" | "Medium" | "Hard" | "Deadly"
  intro           str   Flavor text shown when the campaign starts.
  reward_gold_min int   Minimum gold reward per player on success.
  reward_gold_max int   Maximum gold reward per player on success.
  reward_xp       int   XP per player on success.
  encounters      list  Ordered list of encounter dicts (see below).

DIFFICULTY GUIDELINES
─────────────────────
  Easy    Lv 1–2   Simple enemies, forgiving DC checks
  Medium  Lv 2–4   One tough fight or tricky interaction
  Hard    Lv 4–6   Multi-encounter gauntlet, dangerous boss
  Deadly  Lv 8+    Party wipe is a real risk

═══════════════════════════════════════════════════════════════════════════════
ENCOUNTER TYPES
═══════════════════════════════════════════════════════════════════════════════

──────────────────────────────────────────────────────────────────────────────
TYPE: "combat"
──────────────────────────────────────────────────────────────────────────────
  name    str   Title shown above the fight embed.
  intro   str   Flavor text shown when the encounter starts.
  enemy   dict  Enemy stat block (see ENEMY FIELDS below).

ENEMY FIELDS
  name        str   Enemy display name.
  emoji       str   Emoji shown next to the name.
  hp          int   Total hit points.
  ac          int   Armor class (player rolls to beat this to hit).
  atk_bonus   int   Enemy attack bonus added to a d20 roll vs player AC.
  dmg         str   Damage dice expression e.g. "1d6+2", "2d8+4".
  initiative  int   Tie-breaker when sorting turn order (higher = acts sooner).
  drops       list  [{"id": item_id, "chance": 0–100}, ...]
                    Each player rolls separately. Use existing item IDs from
                    character/variables.py ITEMS list.

STAT SCALING GUIDE
  Level 1–2 Easy    hp 18–25   ac 11–13   atk +2–3   dmg 1d4+1  – 1d6+2
  Level 2–3 Medium  hp 25–38   ac 13–14   atk +3–5   dmg 1d6+2  – 1d8+3
  Level 4–5 Hard    hp 38–55   ac 14–16   atk +5–6   dmg 1d8+3  – 2d6+3
  Level 6+  Boss    hp 55–110  ac 15–17   atk +6–8   dmg 2d6+4  – 2d10+5

──────────────────────────────────────────────────────────────────────────────
TYPE: "interaction"
──────────────────────────────────────────────────────────────────────────────
  name             str        Title shown on the encounter embed.
  intro            str        Flavor text describing the situation.
  skill            str        Ability used for the check:
                                strength / dexterity / constitution /
                                intelligence / wisdom / charisma
  skill_label      str        Button label shown to players e.g. "🗣️ Persuade"
  dc               int        Difficulty class. Roll d20 + ability mod vs this.
  success_text     str        Shown when the check passes.
  failure_text     str        Shown when the check fails.
  combat_fallback  dict|None  Enemy dict (same format as combat) spawned on
                              failure. Set to None for no combat consequence.

DC GUIDELINES
  DC  8   Trivial — most characters pass easily
  DC 10   Easy — average ability mod clears it
  DC 12   Medium — you need a decent stat or some luck
  DC 14   Hard — needs a good stat
  DC 16   Very hard — specialist territory
  DC 18   Heroic — only the best succeed

──────────────────────────────────────────────────────────────────────────────
TYPE: "choice"
──────────────────────────────────────────────────────────────────────────────
  name     str   Title shown when the choice is presented.
  intro    str   Flavor text before the options appear.
  options  list  Each option is a dict:
    label        str   Button label e.g. "🌾 Help the farmers"
    result_text  str   Short line shown after the choice is made.
    encounters   list  Sub-encounter list that runs for this branch
                       (same format as top-level encounters).

  Note: choice branches currently support "combat" and "interaction"
  sub-encounters. Nested choices are not supported.

═══════════════════════════════════════════════════════════════════════════════
DROPS — AVAILABLE ITEM IDs
═══════════════════════════════════════════════════════════════════════════════
  herb              Common crafting material (plants, fungi)
  leather_scrap     Common crafting material (from beast/humanoid enemies)
  arcane_shard      Rare crafting material (from magical creatures)

  scroll_misty_step     Rare   Wizard learns Misty Step
  scroll_scorching_ray  Rare   Wizard learns Scorching Ray
  scroll_fireball       Epic   Wizard learns Fireball
  scroll_counterspell   Epic   Wizard learns Counterspell

  small_health_potion   Common    heals 1d4+1
  health_potion         Uncommon  heals 2d4+2
  large_health_potion   Rare      heals 4d4+4

  (Any item id from character/variables.py ITEMS works here)

═══════════════════════════════════════════════════════════════════════════════
COMPLETE EXAMPLE — UNCOMMENT AND EDIT
═══════════════════════════════════════════════════════════════════════════════
"""


def register(api):
    api.add_campaign({
        # ── Identity ──────────────────────────────────────────────────────────
        "id":          "my_campaign",        # <-- change this
        "name":        "My Campaign",        # <-- change this
        "emoji":       "⚔️",
        "min_level":   1,
        "min_players": 1,
        "max_players": 4,
        "difficulty":  "Easy",

        # ── Intro shown when campaign starts ──────────────────────────────────
        "intro": "A short hook that explains why the players are here.",

        # ── Rewards on success ────────────────────────────────────────────────
        "reward_gold_min": 50,
        "reward_gold_max": 120,
        "reward_xp":       150,

        # ── Encounters ────────────────────────────────────────────────────────
        "encounters": [

            # Combat encounter
            {
                "type":  "combat",
                "name":  "First Fight",
                "intro": "Flavor text — what do the players see when this fight starts?",
                "enemy": {
                    "name":       "Enemy Name",
                    "emoji":      "👺",
                    "hp":         22,
                    "ac":         12,
                    "atk_bonus":  3,
                    "dmg":        "1d6+1",
                    "initiative": 1,
                    "drops": [
                        {"id": "herb",          "chance": 50},
                        {"id": "leather_scrap", "chance": 30},
                    ],
                },
            },

            # Interaction encounter
            {
                "type":        "interaction",
                "name":        "Tense Moment",
                "intro":       "Describe the situation that calls for a skill check.",
                "skill":       "charisma",
                "skill_label": "🗣️ Persuade",
                "dc":          11,
                "success_text": "What happens when they pass.",
                "failure_text": "What happens when they fail.",
                "combat_fallback": {         # set to None if no fight on failure
                    "name":       "Angry Foe",
                    "emoji":      "😤",
                    "hp":         20,
                    "ac":         12,
                    "atk_bonus":  3,
                    "dmg":        "1d6+1",
                    "initiative": 2,
                    "drops": [],
                },
            },

            # Boss combat
            {
                "type":  "combat",
                "name":  "The Boss",
                "intro": "The climax — make it feel earned.",
                "enemy": {
                    "name":       "Boss Name",
                    "emoji":      "💀",
                    "hp":         45,
                    "ac":         14,
                    "atk_bonus":  5,
                    "dmg":        "1d10+3",
                    "initiative": 3,
                    "drops": [
                        {"id": "arcane_shard", "chance": 30},
                        {"id": "herb",         "chance": 50},
                    ],
                },
            },

        ],
    })
