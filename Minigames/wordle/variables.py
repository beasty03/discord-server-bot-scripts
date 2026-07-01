from utils.config_loader import get_bot_token, load_config

BOT_TOKEN   = get_bot_token()
config      = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ============================================================================
# WORDNIK API  (shared key with hangman — add "wordnik_api_key" to config.json)
# ============================================================================

WORDNIK_API_KEY        = config.get("wordnik_api_key", "")
WORDNIK_API_URL        = "https://api.wordnik.com/v4/words.json/randomWord"
WORDNIK_MIN_CORPUS     = 100000   # higher than hangman — words must be very familiar
WORDNIK_PART_OF_SPEECH = "noun"

# ============================================================================
# WORDLE SETTINGS
# ============================================================================

WORD_LENGTH    = 5
MAX_ATTEMPTS   = 6
MIN_BET        = 10
MAX_BET        = -1     # -1 = no limit
BUTTON_TIMEOUT = 300    # 5 minutes

# Payout multiplier per attempt number (index 0 = guessed on attempt 1)
WIN_MULTIPLIERS = [6.0, 4.0, 3.0, 2.5, 1.5, 1.2]

# Fallback word list (used when API key is missing or API is unreachable)
WORDS = [
    "ABOUT", "ABOVE", "ACUTE", "ADMIT", "ADOPT", "AFTER", "AGENT", "AGREE",
    "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIVE", "ALLEY", "ALLOW", "ALONE",
    "ANGEL", "ANGER", "ANGLE", "ANKLE", "APPLE", "ARENA", "ASIDE", "AUDIO",
    "AVOID", "AWARD", "AWARE", "BACON", "BADGE", "BEACH", "BEGIN", "BEING",
    "BELOW", "BENCH", "BERRY", "BIRTH", "BLACK", "BLADE", "BLAME", "BLANK",
    "BLAST", "BLAZE", "BLEND", "BLIND", "BLOCK", "BLOOD", "BLOOM", "BLOWN",
    "BLUNT", "BOARD", "BONUS", "BOOTH", "BORED", "BOUND", "BRAIN", "BRAND",
    "BRAVE", "BREAD", "BREAK", "BREED", "BRICK", "BRIDE", "BRING", "BROAD",
    "BROKE", "BROWN", "BRUSH", "BUILD", "BUILT", "BURST", "CABIN", "CANDY",
    "CARRY", "CAUSE", "CHAIR", "CHAOS", "CHARM", "CHASE", "CHEAP", "CHECK",
    "CHESS", "CHEST", "CHIEF", "CHILD", "CHOSE", "CIVIL", "CLAIM", "CLASS",
    "CLEAN", "CLEAR", "CLICK", "CLIFF", "CLIMB", "CLOCK", "CLOSE", "CLOUD",
    "COACH", "COAST", "COLOR", "COMIC", "CORAL", "COULD", "COUNT", "COURT",
    "COVER", "CRACK", "CRAFT", "CRASH", "CRAZY", "CREAM", "CRIME", "CROSS",
    "CROWD", "CROWN", "CRUSH", "CURVE", "CYCLE", "DAILY", "DANCE", "DEATH",
    "DELAY", "DENSE", "DEPTH", "DIRTY", "DODGE", "DOUBT", "DOUGH", "DRAFT",
    "DRAMA", "DRAWN", "DREAM", "DRIVE", "DRONE", "DRUMS", "EAGLE", "EARLY",
    "EARTH", "EIGHT", "ELITE", "EMPTY", "ENEMY", "ENJOY", "ENTER", "EQUAL",
    "ESSAY", "EVENT", "EVERY", "EXACT", "EXTRA", "FAINT", "FAITH", "FANCY",
    "FATAL", "FAULT", "FEAST", "FENCE", "FEVER", "FIELD", "FIFTH", "FIFTY",
    "FIGHT", "FINAL", "FIRST", "FIXED", "FLAME", "FLASH", "FLESH", "FLOAT",
    "FLOOR", "FLUID", "FOCUS", "FORGE", "FORUM", "FOUND", "FRESH", "FRONT",
    "FROST", "FRUIT", "FUNDS", "FUNNY", "GHOST", "GIANT", "GIVEN", "GLASS",
    "GLOBE", "GLORY", "GRACE", "GRADE", "GRAIN", "GRANT", "GRAPE", "GRASS",
    "GRAVE", "GREAT", "GREEN", "GRIEF", "GROAN", "GROUP", "GROWN", "GUARD",
    "GUESS", "GUEST", "GUIDE", "GUILD", "GUILT", "HANDS", "HAPPY", "HARSH",
    "HEART", "HEAVY", "HENCE", "HONOR", "HORSE", "HOTEL", "HOUSE", "HUMAN",
    "HUMOR", "HURRY", "IMAGE", "INDEX", "INPUT", "ISSUE", "JEWEL", "JOINT",
    "JUDGE", "JUICE", "JUICY", "KNIFE", "KNOCK", "KNOWN", "LABEL", "LARGE",
    "LASER", "LATER", "LAUGH", "LAYER", "LEARN", "LEAVE", "LEGAL", "LEMON",
    "LEVEL", "LIGHT", "LIMIT", "LINEN", "LIVER", "LOCAL", "LODGE", "LOGIC",
    "LOOSE", "LOVER", "LOWER", "LOYAL", "LUCKY", "LUNCH", "MAGIC", "MAJOR",
    "MAKER", "MANOR", "MAPLE", "MARCH", "MATCH", "MAYOR", "MEDIA", "METAL",
    "MINOR", "MINUS", "MODEL", "MONEY", "MONTH", "MORAL", "MOTOR", "MOUNT",
    "MOUSE", "MOUTH", "MOVED", "MOVIE", "MUSIC", "NAVAL", "NEVER", "NIGHT",
    "NINJA", "NOISE", "NORTH", "NOTED", "NOVEL", "NURSE", "NYMPH", "OCEAN",
    "OFFER", "OFTEN", "OLIVE", "ONSET", "OPERA", "ORDER", "OTHER", "OUTER",
    "OWNED", "OWNER", "OZONE", "PAINT", "PANEL", "PAPER", "PARTY", "PASTA",
    "PATCH", "PAUSE", "PEACE", "PEARL", "PEDAL", "PENNY", "PHASE", "PHONE",
    "PHOTO", "PIECE", "PILOT", "PINCH", "PIZZA", "PLACE", "PLAIN", "PLANE",
    "PLANT", "PLATE", "PLAZA", "PLUCK", "PLUMB", "PLUME", "PLUNGE", "POINT",
    "POKER", "POLAR", "POPPY", "PORCH", "POWER", "PRESS", "PRICE", "PRIDE",
    "PRIME", "PRINT", "PRIOR", "PRIZE", "PROBE", "PRONE", "PROOF", "PROSE",
    "PROUD", "PROVE", "PROWL", "PULSE", "PUNCH", "PUPIL", "QUEEN", "QUEST",
    "QUEUE", "QUIET", "QUOTA", "QUOTE", "RAISE", "RALLY", "RANGE", "RAPID",
    "RATIO", "REACH", "REACT", "REALM", "REBEL", "REFER", "REIGN", "RELAX",
    "REPLY", "RIGHT", "RIGID", "RISKY", "RIVER", "ROBOT", "ROCKY", "ROMAN",
    "ROUGE", "ROUGH", "ROUND", "ROUTE", "ROYAL", "RUGBY", "RULER", "RURAL",
    "SAFER", "SAINT", "SALAD", "SAUCE", "SCALE", "SCENE", "SCOPE", "SCORE",
    "SCOUT", "SENSE", "SERVE", "SETUP", "SEVEN", "SHADE", "SHAKE", "SHALL",
    "SHAME", "SHAPE", "SHARE", "SHARK", "SHARP", "SHEEP", "SHEER", "SHELF",
    "SHELL", "SHIFT", "SHINE", "SHIRT", "SHOOT", "SHORE", "SHORT", "SHOUT",
    "SIGHT", "SILLY", "SINCE", "SIXTH", "SIXTY", "SIZED", "SKILL", "SKULL",
    "SLATE", "SLEEP", "SLICE", "SLIDE", "SLOPE", "SMILE", "SMOKE", "SNAKE",
    "SOLAR", "SOLID", "SOLVE", "SORRY", "SOUTH", "SPACE", "SPARE", "SPARK",
    "SPEAK", "SPEED", "SPEND", "SPICE", "SPIKE", "SPINE", "SPLIT", "SPOKE",
    "SPOON", "SQUAD", "STACK", "STAFF", "STAGE", "STAIN", "STAKE", "STALE",
    "STALL", "STAMP", "STAND", "STARK", "START", "STATE", "STEAK", "STEEL",
    "STEEP", "STEER", "STERN", "STICK", "STIFF", "STILL", "STOCK", "STONE",
    "STOOD", "STORE", "STORM", "STORY", "STRIP", "STUCK", "STUDY", "STUFF",
    "STYLE", "SUGAR", "SUITE", "SUNNY", "SUPER", "SURGE", "SWAMP", "SWEEP",
    "SWEET", "SWEPT", "SWIFT", "SWORD", "TABLE", "TAKEN", "TASTE", "TEACH",
    "TEETH", "THEIR", "THEME", "THERE", "THESE", "THICK", "THING", "THINK",
    "THIRD", "THOSE", "THREE", "THROW", "TIGER", "TIGHT", "TIMER", "TIRED",
    "TITLE", "TODAY", "TOKEN", "TOTAL", "TOUCH", "TOUGH", "TOWER", "TOXIC",
    "TRACK", "TRADE", "TRAIL", "TRAIN", "TRAIT", "TRAWL", "TREND", "TRIAL",
    "TRIBE", "TRICK", "TRIED", "TROOP", "TRUCK", "TRULY", "TRUMP", "TRUNK",
    "TRUST", "TRUTH", "TUMOR", "TWIST", "TWITCH", "ULTRA", "UNCLE", "UNDER",
    "UNION", "UNITY", "UNTIL", "UPPER", "UPSET", "URBAN", "USAGE", "USUAL",
    "UTTER", "VALID", "VALUE", "VALVE", "VERSE", "VIDEO", "VIGIL", "VIRAL",
    "VIRUS", "VISIT", "VITAL", "VIVID", "VOCAL", "VOICE", "VOTER", "WAGON",
    "WASTE", "WATCH", "WATER", "WEARY", "WEDGE", "WEIRD", "WHALE", "WHEAT",
    "WHEEL", "WHERE", "WHICH", "WHILE", "WHITE", "WHOLE", "WIDER", "WITCH",
    "WOMAN", "WOMEN", "WOODS", "WORLD", "WORRY", "WORSE", "WORST", "WORTH",
    "WOULD", "WOUND", "WRATH", "WRIST", "WROTE", "YACHT", "YIELD", "YOUNG",
    "YOUTH", "ZEBRA", "ZONAL",
]

# ============================================================================
# EMBED COLORS
# ============================================================================

COLOR_WIN     = 0x57F287
COLOR_LOSE    = 0xED4245
COLOR_ERROR   = 0xED4245
COLOR_PLAYING = 0x5865F2
