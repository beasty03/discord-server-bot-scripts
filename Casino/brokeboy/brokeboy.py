import importlib.util as _ilu
import random
import time
from datetime import datetime
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks

_spec = _ilu.spec_from_file_location('brokeboy_variables', Path(__file__).parent / 'variables.py')
var = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(var)

from forge_db import ForgeDB

# ── helpers ───────────────────────────────────────────────────────────────────

def _hour_bucket() -> int:
    return int(time.time()) // 3600 * 3600


def _check_hourly_limit(db, uid: str, gid: str, command: str) -> tuple[bool, int]:
    """Returns (allowed, uses_so_far). Resets automatically when the hour rolls over."""
    bucket = _hour_bucket()
    rows = db.execute(
        "SELECT uses_this_hour, hour_bucket FROM brokeboy_usage "
        "WHERE user_id=? AND guild_id=? AND command=?",
        (uid, gid, command),
    )
    if not rows:
        return True, 0
    stored_uses, stored_bucket = rows[0]
    if stored_bucket != bucket:
        return True, 0
    return stored_uses < var.MAX_USES_PER_HOUR, stored_uses


def _record_use(db, uid: str, gid: str, command: str):
    bucket = _hour_bucket()
    db.execute(
        """INSERT INTO brokeboy_usage (user_id, guild_id, command, hour_bucket, uses_this_hour)
           VALUES (?, ?, ?, ?, 1)
           ON CONFLICT(user_id, guild_id, command) DO UPDATE SET
               uses_this_hour = CASE
                   WHEN hour_bucket = excluded.hour_bucket THEN uses_this_hour + 1
                   ELSE 1
               END,
               hour_bucket = excluded.hour_bucket""",
        (uid, gid, command, bucket),
    )


def _secs_until_next_hour() -> int:
    return int((_hour_bucket() + 3600) - time.time())


def _loan_duration(amount: int) -> int:
    """Days to repay based on loan amount (uses LOAN_DURATION_TIERS)."""
    for threshold, days in var.LOAN_DURATION_TIERS:
        if amount <= threshold:
            return days
    return var.LOAN_DURATION_TIERS[-1][1]


def _calc_max_loan(db, uid: str, gid: str) -> int:
    """Max loan = net_loss // divisor, capped at LOAN_MAX_AMOUNT. Net profit → LOAN_MIN_AMOUNT."""
    rows = db.execute(
        "SELECT total_won, total_lost FROM casino_stats WHERE user_id=? AND guild_id=?",
        (uid, gid),
    )
    if not rows:
        return var.LOAN_MIN_AMOUNT
    net_loss = rows[0][1] - rows[0][0]
    if net_loss <= 0:
        return var.LOAN_MIN_AMOUNT
    return min(max(var.LOAN_MIN_AMOUNT, net_loss // var.LOAN_NET_LOSS_DIVISOR), var.LOAN_MAX_AMOUNT)


def _announce_channel(guild: discord.Guild) -> discord.TextChannel | None:
    """Best channel to post public announcements in."""
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        return guild.system_channel
    return next(
        (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages),
        None,
    )


# ── cog ───────────────────────────────────────────────────────────────────────

class BrokeBoy(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db  = ForgeDB.get()

    async def cog_load(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS brokeboy_usage (
                user_id        TEXT    NOT NULL,
                guild_id       TEXT    NOT NULL,
                command        TEXT    NOT NULL,
                hour_bucket    INTEGER NOT NULL,
                uses_this_hour INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id, command)
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS brokeboy_loans (
                user_id          TEXT    NOT NULL,
                guild_id         TEXT    NOT NULL,
                amount           INTEGER NOT NULL,
                remaining        INTEGER NOT NULL,
                due_timestamp    INTEGER NOT NULL,
                balance_snapshot INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        if not self._loan_checker.is_running():
            self._loan_checker.start()

    async def cog_unload(self):
        self._loan_checker.cancel()

    # ── background loan task ──────────────────────────────────────────────────

    @tasks.loop(seconds=var.LOAN_CHECK_INTERVAL)
    async def _loan_checker(self):
        """
        Every LOAN_CHECK_INTERVAL seconds:
        - Deduct LOAN_REPAYMENT_RATE of any balance gains toward outstanding loans.
        - Kick users who missed their deadline and announce it to the server.
        - Celebrate loan pay-offs publicly.
        """
        loans = self.db.execute(
            "SELECT user_id, guild_id, amount, remaining, due_timestamp, balance_snapshot "
            "FROM brokeboy_loans"
        )
        if not loans:
            return

        now = int(time.time())

        for uid, gid, original, remaining, due_ts, snapshot in loans:
            bot_uid     = str(self.bot.user.id)
            current_bal = self.db.get_balance(uid, gid)

            # Collect repayment on any net balance increase since last check
            if current_bal > snapshot and remaining > 0:
                gain    = current_bal - snapshot
                payment = max(1, int(gain * var.LOAN_REPAYMENT_RATE))
                payment = min(payment, remaining)
                self.db.update_balance(uid, gid, -payment, 'loan_repayment')
                self.db.ensure_user(bot_uid, gid, "House")
                self.db.update_balance(bot_uid, gid, payment, 'loan_repayment')
                remaining   -= payment
                new_snapshot = current_bal - payment
            else:
                new_snapshot = current_bal

            guild = self.bot.get_guild(int(gid))

            if remaining <= 0:
                # ── fully repaid ──────────────────────────────────────────────
                self.db.execute(
                    "DELETE FROM brokeboy_loans WHERE user_id=? AND guild_id=?",
                    (uid, gid),
                )
                if guild:
                    ch = _announce_channel(guild)
                    if ch:
                        await ch.send(embed=discord.Embed(
                            description=(
                                f"✅ <@{uid}> fully repaid their loan of "
                                f"**{var.CURRENCY_SYMBOL} {original:,} {var.CURRENCY_NAME}**. "
                                f"Redemption arc complete. 👏"
                            ),
                            color=var.COLOR_WIN,
                        ))

            elif now > due_ts:
                # ── defaulted — announce then kick ────────────────────────────
                member = guild.get_member(int(uid)) if guild else None

                if guild:
                    ch = _announce_channel(guild)
                    if ch:
                        taunt = random.choice(var.LOAN_DEFAULT_TAUNTS).format(
                            name=f"<@{uid}>",
                            amount=f"{var.CURRENCY_SYMBOL} {remaining:,} {var.CURRENCY_NAME}",
                        )
                        await ch.send(embed=discord.Embed(
                            title="🚨 Loan Default",
                            description=(
                                f"{taunt}\n\n"
                                f"*Borrowed {var.CURRENCY_SYMBOL} {original:,}, "
                                f"still owed {var.CURRENCY_SYMBOL} {remaining:,}. "
                                f"They can rejoin with an invite — the debt is buried.*"
                            ),
                            color=var.COLOR_LOSE,
                        ))

                if member:
                    try:
                        await member.send(embed=discord.Embed(
                            title="💸 You've Been Kicked",
                            description=(
                                f"You were removed from **{guild.name}** for not repaying your loan.\n"
                                f"You still owed **{var.CURRENCY_SYMBOL} {remaining:,} {var.CURRENCY_NAME}**.\n\n"
                                f"You can rejoin with an invite link. The debt is cleared."
                            ),
                            color=var.COLOR_ERROR,
                        ))
                    except Exception:
                        pass
                    try:
                        await member.kick(reason="Defaulted on BrokeBoy loan.")
                    except Exception:
                        pass

                self.db.execute(
                    "DELETE FROM brokeboy_loans WHERE user_id=? AND guild_id=?",
                    (uid, gid),
                )

            else:
                # ── still active — update snapshot and remaining ───────────────
                self.db.execute(
                    "UPDATE brokeboy_loans SET remaining=?, balance_snapshot=? "
                    "WHERE user_id=? AND guild_id=?",
                    (remaining, new_snapshot, uid, gid),
                )

    @_loan_checker.before_loop
    async def _before_loan_checker(self):
        await self.bot.wait_until_ready()

    # ── shared gate for beg / dumpster_dive ──────────────────────────────────

    def _gate(self, uid: str, gid: str, command: str) -> discord.Embed | None:
        """Return an error embed if the user is ineligible, else None."""
        balance = self.db.get_balance(uid, gid)
        if balance >= var.MAX_BALANCE_TO_USE:
            return discord.Embed(
                title="🚫 You're Not Broke Enough",
                description=(
                    f"Only users with fewer than **{var.CURRENCY_SYMBOL} {var.MAX_BALANCE_TO_USE} "
                    f"{var.CURRENCY_NAME}** may use this command.\n"
                    f"Your balance: **{var.CURRENCY_SYMBOL} {balance:,}**"
                ),
                color=var.COLOR_ERROR,
            )

        allowed, _ = _check_hourly_limit(self.db, uid, gid, command)
        if not allowed:
            mins = _secs_until_next_hour() // 60
            return discord.Embed(
                title="⏰ Cooldown",
                description=(
                    f"You've used `/{command}` **{var.MAX_USES_PER_HOUR}x** this hour.\n"
                    f"Even the broke need to pace themselves. Try again in **{mins}m**."
                ),
                color=var.COLOR_ERROR,
            )

        return None

    # ── /beg ─────────────────────────────────────────────────────────────────

    @app_commands.command(name="beg", description="Beg for coins when you're completely broke.")
    async def beg(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)
        self.db.ensure_user(uid, gid, interaction.user.display_name)

        err = self._gate(uid, gid, "beg")
        if err:
            await interaction.response.send_message(embed=err, ephemeral=True)
            return

        _, uses_before = _check_hourly_limit(self.db, uid, gid, "beg")
        _record_use(self.db, uid, gid, "beg")
        uses_after = uses_before + 1

        taunt = random.choice(var.BEG_TAUNTS)
        won   = random.randint(1, 100) <= var.BEG_WIN_CHANCE

        if won:
            amount  = random.randint(var.BEG_MIN_REWARD, var.BEG_MAX_REWARD)
            bot_uid = str(self.bot.user.id)
            self.db.update_balance(uid, gid, amount, 'beg')
            self.db.ensure_user(bot_uid, gid, "House")
            self.db.update_balance(bot_uid, gid, -amount, 'house_payout')
            new_bal = self.db.get_balance(uid, gid)
            result  = random.choice(var.BEG_SUCCESS_MESSAGES).format(
                amount=f"{var.CURRENCY_SYMBOL} {amount:,}", currency=var.CURRENCY_NAME,
            )
            embed = discord.Embed(title="🙏 Begging Complete", description=f"{taunt}\n\n{result}", color=var.COLOR_WIN)
            embed.add_field(name="New Balance", value=f"{var.CURRENCY_SYMBOL} {new_bal:,} {var.CURRENCY_NAME}", inline=True)
        else:
            new_bal = self.db.get_balance(uid, gid)
            result  = random.choice(var.BEG_FAIL_MESSAGES)
            embed   = discord.Embed(title="🫳 Nobody Cared", description=f"{taunt}\n\n{result}", color=var.COLOR_LOSE)
            embed.add_field(name="Balance (still)", value=f"{var.CURRENCY_SYMBOL} {new_bal:,} {var.CURRENCY_NAME}", inline=True)

        embed.add_field(name="Uses This Hour", value=f"{uses_after}/{var.MAX_USES_PER_HOUR}", inline=True)
        embed.set_footer(text=f"{interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    # ── /dumpster_dive ────────────────────────────────────────────────────────

    @app_commands.command(name="dumpster_dive", description="Dig through the trash for loose coins when you're flat broke.")
    async def dumpster_dive(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)
        self.db.ensure_user(uid, gid, interaction.user.display_name)

        err = self._gate(uid, gid, "dumpster_dive")
        if err:
            await interaction.response.send_message(embed=err, ephemeral=True)
            return

        _, uses_before = _check_hourly_limit(self.db, uid, gid, "dumpster_dive")
        _record_use(self.db, uid, gid, "dumpster_dive")
        uses_after = uses_before + 1

        taunt = random.choice(var.DUMPSTER_TAUNTS)
        won   = random.randint(1, 100) <= var.DUMPSTER_WIN_CHANCE

        if won:
            amount  = random.randint(var.DUMPSTER_MIN_REWARD, var.DUMPSTER_MAX_REWARD)
            bot_uid = str(self.bot.user.id)
            self.db.update_balance(uid, gid, amount, 'dumpster_dive')
            self.db.ensure_user(bot_uid, gid, "House")
            self.db.update_balance(bot_uid, gid, -amount, 'house_payout')
            new_bal = self.db.get_balance(uid, gid)
            result  = random.choice(var.DUMPSTER_SUCCESS_MESSAGES).format(
                amount=f"{var.CURRENCY_SYMBOL} {amount:,}", currency=var.CURRENCY_NAME,
            )
            embed = discord.Embed(title="🗑️ Dumpster Dive — Score!", description=f"{taunt}\n\n{result}", color=var.COLOR_WIN)
            embed.add_field(name="New Balance", value=f"{var.CURRENCY_SYMBOL} {new_bal:,} {var.CURRENCY_NAME}", inline=True)
        else:
            new_bal = self.db.get_balance(uid, gid)
            result  = random.choice(var.DUMPSTER_FAIL_MESSAGES)
            embed   = discord.Embed(title="🗑️ Dumpster Dive — Nothing", description=f"{taunt}\n\n{result}", color=var.COLOR_LOSE)
            embed.add_field(name="Balance (still)", value=f"{var.CURRENCY_SYMBOL} {new_bal:,} {var.CURRENCY_NAME}", inline=True)

        embed.add_field(name="Uses This Hour", value=f"{uses_after}/{var.MAX_USES_PER_HOUR}", inline=True)
        embed.set_footer(text=f"{interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

    # ── /loan ────────────────────────────────────────────────────────────────

    @app_commands.command(name="loan", description="Take out a loan from the house — repay it or get kicked.")
    @app_commands.describe(amount="How many coins to borrow")
    async def loan(self, interaction: discord.Interaction, amount: int):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)
        self.db.ensure_user(uid, gid, interaction.user.display_name)

        # Block duplicate loans
        existing = self.db.execute(
            "SELECT remaining, due_timestamp FROM brokeboy_loans WHERE user_id=? AND guild_id=?",
            (uid, gid),
        )
        if existing:
            rem, due_ts = existing[0]
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Already in Debt",
                    description=(
                        f"Pay off your existing loan first.\n"
                        f"Remaining: **{var.CURRENCY_SYMBOL} {rem:,}** — Due: <t:{due_ts}:R>"
                    ),
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        if amount < var.LOAN_MIN_AMOUNT:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"Minimum loan is **{var.CURRENCY_SYMBOL} {var.LOAN_MIN_AMOUNT:,}**.",
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        max_loan = _calc_max_loan(self.db, uid, gid)
        if amount > max_loan:
            stats = self.db.execute(
                "SELECT total_won, total_lost FROM casino_stats WHERE user_id=? AND guild_id=?",
                (uid, gid),
            )
            net_pl = (stats[0][0] - stats[0][1]) if stats else 0   # total_won - total_lost
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Loan Too Large",
                    description=(
                        f"Your casino history allows up to **{var.CURRENCY_SYMBOL} {max_loan:,}**.\n"
                        f"Your net P&L: **{var.CURRENCY_SYMBOL} {net_pl:+,}**\n\n"
                        f"*Lose more to raise your credit limit. Classic.*"
                    ),
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        bot_uid = str(self.bot.user.id)
        self.db.ensure_user(bot_uid, gid, "House")
        house_bal = self.db.get_balance(bot_uid, gid)
        if house_bal < amount:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🏦 House is Broke",
                    description=(
                        f"The house can't cover **{var.CURRENCY_SYMBOL} {amount:,}**.\n"
                        f"House balance: **{var.CURRENCY_SYMBOL} {house_bal:,}**\n\n"
                        f"*Wait for other players to donate their money first.*"
                    ),
                    color=var.COLOR_ERROR,
                ),
                ephemeral=True,
            )
            return

        days   = _loan_duration(amount)
        due_ts = int(time.time()) + days * 86_400

        # Transfer house → user
        self.db.update_balance(bot_uid, gid, -amount, 'loan_issued')
        self.db.update_balance(uid, gid, amount, 'loan_received')
        new_bal = self.db.get_balance(uid, gid)

        self.db.execute(
            """INSERT INTO brokeboy_loans
               (user_id, guild_id, amount, remaining, due_timestamp, balance_snapshot)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (uid, gid, amount, amount, due_ts, new_bal),
        )

        embed = discord.Embed(
            title="💰 Loan Approved",
            description=(
                f"The house loaned you **{var.CURRENCY_SYMBOL} {amount:,} {var.CURRENCY_NAME}**.\n\n"
                f"**{var.LOAN_REPAYMENT_RATE * 100:.0f}%** of every currency gain is auto-deducted until repaid.\n"
                f"**Deadline:** <t:{due_ts}:F> (<t:{due_ts}:R>)\n\n"
                f"⚠️ **Miss the deadline = kicked from the server.**"
            ),
            color=var.COLOR_INFO,
        )
        embed.add_field(name="Borrowed",      value=f"{var.CURRENCY_SYMBOL} {amount:,}", inline=True)
        embed.add_field(name="Days to Repay", value=f"{days} days",                      inline=True)
        embed.add_field(name="New Balance",   value=f"{var.CURRENCY_SYMBOL} {new_bal:,}", inline=True)
        embed.set_footer(text=f"{interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed)

        # Public announcement
        if interaction.channel:
            await interaction.channel.send(embed=discord.Embed(
                description=(
                    f"🏦 **{interaction.user.display_name}** just took out a loan of "
                    f"**{var.CURRENCY_SYMBOL} {amount:,}** from the house. "
                    f"**{days} days** to repay or they're out. 👀"
                ),
                color=var.COLOR_INFO,
            ))

    # ── /loan_payback ────────────────────────────────────────────────────────

    @app_commands.command(name="loan_payback", description="Check your active loan status and net profit/loss.")
    async def loan_payback(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        gid = str(interaction.guild_id)
        self.db.ensure_user(uid, gid, interaction.user.display_name)

        loan_rows = self.db.execute(
            "SELECT amount, remaining, due_timestamp FROM brokeboy_loans WHERE user_id=? AND guild_id=?",
            (uid, gid),
        )
        stat_rows = self.db.execute(
            "SELECT total_won, total_lost FROM casino_stats WHERE user_id=? AND guild_id=?",
            (uid, gid),
        )
        total_won  = stat_rows[0][0] if stat_rows else 0
        total_lost = stat_rows[0][1] if stat_rows else 0
        net        = total_won - total_lost

        if not loan_rows:
            max_loan = _calc_max_loan(self.db, uid, gid)
            embed = discord.Embed(
                title="📋 No Active Loan",
                description="You have no outstanding loan.",
                color=var.COLOR_INFO,
            )
            embed.add_field(name="Net P&L",           value=f"{var.CURRENCY_SYMBOL} {net:+,}", inline=True)
            embed.add_field(name="Max Loan Available", value=f"{var.CURRENCY_SYMBOL} {max_loan:,}", inline=True)
            embed.set_footer(text=f"{interaction.user.display_name} · {var.SERVER_NAME}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        original, remaining, due_ts = loan_rows[0]
        paid     = original - remaining
        pct_paid = (paid / original * 100) if original > 0 else 0
        now      = int(time.time())

        filled = max(0, min(10, int(pct_paid / 10)))
        bar    = "█" * filled + "░" * (10 - filled)

        danger = (due_ts - now) < 86_400
        color  = var.COLOR_WIN if pct_paid >= 50 else (var.COLOR_INFO if pct_paid >= 25 else var.COLOR_LOSE)

        embed = discord.Embed(title="💳 Active Loan", color=color)
        embed.add_field(name="Original Loan", value=f"{var.CURRENCY_SYMBOL} {original:,}",               inline=True)
        embed.add_field(name="Remaining",     value=f"{var.CURRENCY_SYMBOL} {remaining:,}",              inline=True)
        embed.add_field(name="Paid Back",     value=f"{var.CURRENCY_SYMBOL} {paid:,} ({pct_paid:.0f}%)", inline=True)
        embed.add_field(name="Progress",      value=f"`{bar}` {pct_paid:.0f}%",                          inline=False)
        embed.add_field(name="Due",           value=f"<t:{due_ts}:F> (<t:{due_ts}:R>)",                  inline=True)
        embed.add_field(name="Net P&L",       value=f"{var.CURRENCY_SYMBOL} {net:+,}",                   inline=True)
        embed.add_field(name="Repay Rate",    value=f"{var.LOAN_REPAYMENT_RATE * 100:.0f}% of each gain", inline=True)

        if danger:
            embed.add_field(
                name="⚠️ DANGER ZONE",
                value="Less than 24 hours — repay now or you'll be kicked!",
                inline=False,
            )

        embed.set_footer(text=f"{interaction.user.display_name} · {var.SERVER_NAME}")
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(BrokeBoy(bot))
    print("✅ Casino/BrokeBoy cog loaded successfully")
