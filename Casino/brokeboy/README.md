# BrokeBoy

Poverty-themed commands. `/beg` and `/dumpster_dive` let broke players scrape together a few coins with maximum public humiliation. `/loan` lets anyone borrow from the house bank — with an auto-repayment system and a kick if they default.

---

Commands: 5

## Commands

| Command | Description |
|---|---|
| `/beg` | Beg the server for loose change. 60% chance of 1–5 coins. Public. |
| `/dumpster_dive` | Dig through the trash. 40% chance of 1–8 coins. Public. |
| `/loan <amount>` | Borrow coins from the house. Auto-repaid at 10% of each gain. Public announcement. |
| `/loan_payback` | Check your active loan, progress bar, and net P&L. Ephemeral. |

---

## Loan System

- **Eligibility** — anyone can take a loan (no balance floor). Max amount is calculated from your **net casino loss**: `net_loss ÷ 2`, capped at 500. If you're net-profitable you can only borrow the minimum (25).
- **Repayment** — every 5 minutes the bot checks your balance. If it has risen since the last check, **10% of the increase** is automatically deducted toward the loan.
- **Duration** — based on the loan amount:
  - ≤ 100 coins → 3 days
  - ≤ 300 coins → 5 days
  - > 300 coins → 7 days
- **Default** — if the deadline passes with remaining debt, the bot:
  1. Posts a public roast announcement in the server.
  2. DMs the user.
  3. Kicks them. They can rejoin with an invite. The debt is cleared.
- **Pay-off** — when the loan reaches zero, a public celebration message is posted.
- **House bank** — loans come directly from the bot's house balance. If the house is dry, no loans.

---

## Beg / Dumpster Dive Restrictions

- **Balance gate** — only users with fewer than `MAX_BALANCE_TO_USE` coins (default **10**) may use `/beg` or `/dumpster_dive`.
- **Hourly cap** — each command: max `MAX_USES_PER_HOUR` times per user per hour (default **3**).

---

## Configuration (`variables.py`)

| Variable | Default | Description |
|---|---|---|
| `MAX_BALANCE_TO_USE` | `10` | Balance must be *below* this to use `/beg` or `/dumpster_dive`. |
| `MAX_USES_PER_HOUR` | `3` | Max uses per command per user per hour. |
| `BEG_WIN_CHANCE` | `60` | % success rate for `/beg`. |
| `BEG_MIN_REWARD` / `BEG_MAX_REWARD` | `1` / `5` | Coin range on a successful beg. |
| `DUMPSTER_WIN_CHANCE` | `40` | % success rate for `/dumpster_dive`. |
| `DUMPSTER_MIN_REWARD` / `DUMPSTER_MAX_REWARD` | `1` / `8` | Coin range on a successful dive. |
| `LOAN_MIN_AMOUNT` | `25` | Minimum loan size. |
| `LOAN_MAX_AMOUNT` | `500` | Absolute cap on any single loan. |
| `LOAN_NET_LOSS_DIVISOR` | `2` | `max_loan = net_loss ÷ this`. |
| `LOAN_REPAYMENT_RATE` | `0.10` | Fraction of each balance gain auto-deducted (0.10 = 10%). |
| `LOAN_CHECK_INTERVAL` | `300` | Seconds between background repayment checks. |
| `LOAN_DURATION_TIERS` | see file | `(max_amount, days)` pairs that set the repayment deadline. |
