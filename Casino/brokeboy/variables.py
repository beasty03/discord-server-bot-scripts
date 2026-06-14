# variables.py — Brokeboy (beg / dumpster_dive / loan / loan_payback)

from utils.config_loader import get_bot_token, load_config
from pathlib import Path

# ============================================================================
# CENTRAL CONFIG LOADER
# ============================================================================

BOT_TOKEN = get_bot_token()
config = load_config()
GUILD_ID    = int(config.get('guild_id') or config.get('server', {}).get('guild_id', 0))
SERVER_NAME = config.get('server_name') or config.get('server', {}).get('name', 'Unknown Server')

if 'paths' in config:
    paths = config['paths']
    if 'database_file' in paths:
        DATABASE_NAME = str(Path(paths['database_file']))
    elif 'db_file' in paths:
        DATABASE_NAME = str(Path(paths['db_file']))
    elif 'database_dir' in paths:
        DATABASE_NAME = str(Path(paths['database_dir']) / 'user_database.db')
    else:
        _root = Path(__file__).parent.parent.parent
        DATABASE_NAME = str(_root / 'database' / 'user_database.db')
else:
    _root = Path(__file__).parent.parent.parent
    (_root / 'database').mkdir(exist_ok=True)
    DATABASE_NAME = str(_root / 'database' / 'user_database.db')

# ============================================================================
# BEG / DUMPSTER DIVE SETTINGS
# ============================================================================

# Maximum balance a user may have to use /beg or /dumpster_dive
MAX_BALANCE_TO_USE = 10

# How many times per hour each command can be used per user
MAX_USES_PER_HOUR = 3

# /beg reward range and chance
BEG_MIN_REWARD = 1
BEG_MAX_REWARD = 5
BEG_WIN_CHANCE = 60    # percent (0-100)

# /dumpster_dive reward range and chance
DUMPSTER_MIN_REWARD = 1
DUMPSTER_MAX_REWARD = 8
DUMPSTER_WIN_CHANCE = 40   # percent (0-100)

# ============================================================================
# LOAN SETTINGS
# ============================================================================

# Loan amount bounds
LOAN_MIN_AMOUNT = 25
LOAN_MAX_AMOUNT = 500

# Max loan = net_loss // LOAN_NET_LOSS_DIVISOR, capped at LOAN_MAX_AMOUNT.
# Users with net profit can only borrow LOAN_MIN_AMOUNT.
LOAN_NET_LOSS_DIVISOR = 2

# Fraction of every balance *increase* that is auto-deducted toward the loan.
# 0.10 = 10 %.  Must be between 0 and 1.
LOAN_REPAYMENT_RATE = 0.10

# How often (seconds) the background task checks for repayments and deadlines.
LOAN_CHECK_INTERVAL = 30   # 30 seconds — keeps deductions feeling near-instant

# Repayment deadline tiers: (max_loan_amount, days_to_repay)
# Sorted ascending — first matching tier wins.
LOAN_DURATION_TIERS = [
    (100,    3),   # loan <= 100  → 3 days
    (300,    5),   # loan <= 300  → 5 days
    (999_999, 7),  # anything larger → 7 days
]

# ============================================================================
# CURRENCY
# ============================================================================

CURRENCY_NAME   = config.get("currency_name",   "coins")
CURRENCY_SYMBOL = config.get("currency_symbol", "🪙")

# ============================================================================
# EMBED COLOURS
# ============================================================================

COLOR_WIN   = 0x00FF00
COLOR_LOSE  = 0xFF0000
COLOR_ERROR = 0xFFA500
COLOR_INFO  = 0x5865F2

# ============================================================================
# FLAVOUR MESSAGES
# ============================================================================

BEG_TAUNTS = [
    "🤣 LMAOOO you're literally begging. Touch grass, bro.",
    "💀 Bro is on his knees... absolutely pathetic energy.",
    "😂 The audacity to beg in MY server. Iconic.",
    "🤡 Peak clownery. You really typed `/beg` with no shame.",
    "💸 So broke you need to beg. Honestly impressive.",
    "😭 This is embarrassing to witness. Someone help him.",
    "🪣 Holding out an empty cup... this is your life now.",
]

DUMPSTER_TAUNTS = [
    "🗑️ You are literally digging through trash. Take a moment.",
    "😭 Even the raccoons are judging you right now.",
    "🤢 You climbed IN. Not beside it — IN.",
    "💀 The dumpster smells better than your financial situation.",
    "🤡 This is what rock bottom looks like, everyone. Observe.",
    "😂 You found your calling — dumpster archaeologist.",
    "🧟 Risen from the trash like a discount zombie.",
]

BEG_SUCCESS_MESSAGES = [
    "A kind soul took pity on you. You received **{amount} {currency}**. Don't spend it all in one place.",
    "Someone tossed you **{amount} {currency}** without making eye contact. Cherish that.",
    "A random stranger felt guilty looking at you and handed over **{amount} {currency}**.",
    "You received **{amount} {currency}** in charity. The girlboss era has ended for you.",
    "They gave you **{amount} {currency}** just so you'd stop. It worked.",
]

BEG_FAIL_MESSAGES = [
    "You begged and everyone walked away. Not a single coin. Brutal.",
    "People actively avoided eye contact. You got nothing.",
    "Someone almost helped... then they saw your profile picture. Nothing.",
    "The server looked at you, then looked away. Empty handed.",
    "Not even a sympathy coin. You are astronomically broke.",
]

DUMPSTER_SUCCESS_MESSAGES = [
    "You dug through the trash and found **{amount} {currency}** in an old fast food bag. Questionable but valid.",
    "Between two pizza boxes you found **{amount} {currency}**. Finders keepers.",
    "A crumpled note at the bottom — **{amount} {currency}**. The dumpster provides.",
    "You emerged victorious with **{amount} {currency}** and a mysterious stain. Worth it.",
    "The trash giveth: **{amount} {currency}** discovered inside a soggy envelope.",
]

DUMPSTER_FAIL_MESSAGES = [
    "You found: a half-eaten sandwich, three receipts, and zero coins. Tragic.",
    "Nothing. Not even the raccoon showed up to commiserate.",
    "The dumpster is as empty as your wallet. You got nothing.",
    "You searched for five minutes and found only regret.",
    "Even the trash didn't want you. You got absolutely nothing.",
]

# Used in the public kick announcement — {name} and {amount} are substituted
LOAN_DEFAULT_TAUNTS = [
    "**{name}** couldn't pay back **{amount}** and has been escorted off the premises. 👋",
    "**{name}** thought they could outrun their debt. They were wrong. Bye. 👋",
    "**{name}** borrowed **{amount}**, yolo'd it, and is now gone. A cautionary tale.",
    "**{name}** has been removed for non-payment. The house always wins. 🏦",
    "Pouring one out for **{name}**, who could not, would not, pay back **{amount}**. Gone.",
]
