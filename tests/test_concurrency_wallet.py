"""
test_concurrency_wallet.py — 20 bots all try to spend ONE user's wallet at once.

Scenario:
  * A single user with a known capped wallet (e.g. ₹500)
  * 20 parallel booking requests, each costing ₹200 on a DIFFERENT slot so the
    double-booking trigger doesn't interfere — we're testing wallet isolation.
  * Expected: only floor(500/200) = 2 bookings succeed, the rest fail with
    "Insufficient wallet balance".
  * wallet_balance must end >= 0. Wallet_Transactions 'Payment' count must
    equal the winners. No negative wallets, no phantom debits.

This exercises the `SELECT … FOR UPDATE` on the user row in POST /bookings.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal

import psycopg2
import pytest

from tests.bots import Bot, BotError, _parse_credentials

NUM_REQUESTS     = 20
BUDGET           = Decimal("500.00")
TARGET_FACILITY  = 1       # Main Seminar Hall — slots cost 100/150/200/300/400/500
TARGET_DATE      = (date.today() + timedelta(days=3)).isoformat()


def _slot_price(api_url, facility_id, target_date, want_price):
    tmp = Bot(_parse_credentials()[0]["email"], _parse_credentials()[0]["password"], api=api_url)
    tmp.login()
    slots = [s for s in tmp.availability(facility_id, target_date) if Decimal(s["price"]) == want_price]
    tmp.close()
    return slots


def test_no_double_spend_on_shared_wallet(fresh_db, api_url):
    # Pick one student, reset their wallet to exactly BUDGET via direct DB write.
    cred = _parse_credentials()
    student = next(c for c in cred if c["role"] == "Student")

    conn = psycopg2.connect(dbname="campus_booking", user="postgres",
                            password="postgres", host="localhost", port=5432)
    with conn, conn.cursor() as cur:
        cur.execute("UPDATE Users SET wallet_balance = %s WHERE user_id = %s;",
                    (BUDGET, student["user_id"]))
    conn.close()

    # Grab 20 distinct ₹200 slots for the target date — 20 seminar halls don't
    # exist, so we'll mix across multiple facilities of the same (non-restricted) type.
    conn = psycopg2.connect(dbname="campus_booking", user="postgres",
                            password="postgres", host="localhost", port=5432)
    with conn, conn.cursor() as cur:
        cur.execute("""
            SELECT fs.slot_id, fs.facility_id
              FROM Facility_Slots fs
              JOIN Facilities f ON f.facility_id = fs.facility_id
             WHERE f.type NOT IN ('OAT', 'Pronite_Ground')
               AND fs.price = 200
             ORDER BY fs.facility_id, fs.start_time
             LIMIT %s;
        """, (NUM_REQUESTS,))
        candidates = cur.fetchall()  # list of (slot_id, facility_id)
    conn.close()
    assert len(candidates) == NUM_REQUESTS, \
        f"Need {NUM_REQUESTS} ₹200 slots, found {len(candidates)}"

    # Each request is one bot acting as the same user — to simulate 20 clients,
    # we create 20 Bot instances with the same credentials.
    bots = [Bot(student["email"], student["password"], api=api_url) for _ in range(NUM_REQUESTS)]
    for b in bots:
        b.login()

    def spend(args):
        bot, (slot_id, facility_id) = args
        try:
            r = bot.book(facility_id, TARGET_DATE, [slot_id])
            return (True, slot_id, "ok", r)
        except BotError as e:
            return (False, slot_id, e.detail, None)

    with ThreadPoolExecutor(max_workers=NUM_REQUESTS) as ex:
        results = list(ex.map(spend, zip(bots, candidates)))

    wins  = [r for r in results if r[0]]
    fails = [r for r in results if not r[0]]

    # wallet ended at 0 or positive; total spent ≤ BUDGET
    conn = psycopg2.connect(dbname="campus_booking", user="postgres",
                            password="postgres", host="localhost", port=5432)
    with conn, conn.cursor() as cur:
        cur.execute("SELECT wallet_balance FROM Users WHERE user_id = %s;", (student["user_id"],))
        final_balance = Decimal(cur.fetchone()[0])
        cur.execute("""
            SELECT COUNT(*), COALESCE(SUM(amount), 0)
              FROM Wallet_Transactions
             WHERE user_id = %s AND transaction_type = 'Payment';
        """, (student["user_id"],))
        pay_count, pay_sum = cur.fetchone()
    conn.close()

    print(f"\n▸ wins={len(wins)}  fails={len(fails)}  "
          f"final wallet=₹{final_balance}  payments={pay_count} sum=₹{pay_sum}")

    # Core invariants
    assert final_balance >= 0, "Wallet went negative — SELECT FOR UPDATE isn't protecting the wallet."
    assert len(wins) == int(BUDGET // 200), (
        f"Expected {int(BUDGET // 200)} wins (exactly BUDGET // 200), got {len(wins)}. "
        "Over-booking means two concurrent bookings didn't see each other's debit.")
    assert pay_count == len(wins), "Wallet_Transactions count != winners"
    assert Decimal(pay_sum) == 200 * len(wins)
    assert final_balance == BUDGET - Decimal(pay_sum)

    # Failures must be wallet-related (not random 500s)
    for ok, _slot, detail, _r in fails:
        assert "balance" in detail.lower() or "insufficient" in detail.lower(), \
            f"Unexpected failure reason: {detail}"

    for b in bots:
        b.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
