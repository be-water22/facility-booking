"""
test_rollback.py — transactional rollback / recovery tests.

Each failure path must leave the DB exactly as it was before the request:
no partial Booking_Slots, no wallet debit, no stray Wallet_Transactions.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import psycopg2
import pytest

from tests.bots import Bot, BotError, _parse_credentials, get_admin_bot


def _snapshot(conn, user_id):
    with conn.cursor() as cur:
        cur.execute("SELECT wallet_balance FROM Users WHERE user_id = %s;", (user_id,))
        wallet = Decimal(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM Bookings       WHERE user_id = %s;", (user_id,))
        bookings = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Wallet_Transactions WHERE user_id = %s;", (user_id,))
        txs = cur.fetchone()[0]
    return wallet, bookings, txs


@pytest.fixture
def db():
    conn = psycopg2.connect(dbname="campus_booking", user="postgres",
                            password="postgres", host="localhost", port=5432)
    conn.autocommit = True
    try: yield conn
    finally: conn.close()


def test_rollback_on_insufficient_balance(fresh_db, api_url, db):
    """Poor user: balance of ₹10 tries to book a ₹500 slot. Everything must roll back."""
    cred = _parse_credentials()
    student = next(c for c in cred if c["role"] == "Student")

    with db.cursor() as cur:
        cur.execute("UPDATE Users SET wallet_balance = 10 WHERE user_id = %s;", (student["user_id"],))

    before = _snapshot(db, student["user_id"])

    bot = Bot(student["email"], student["password"], api=api_url); bot.login()
    # Find a 500-rupee slot (18:00–20:00 slot on any non-restricted facility)
    slots = bot.availability(1, (date.today() + timedelta(days=4)).isoformat())
    target = next(s for s in slots if Decimal(s["price"]) == 500)

    with pytest.raises(BotError) as ei:
        bot.book(1, (date.today() + timedelta(days=4)).isoformat(), [target["slot_id"]])
    assert "balance" in ei.value.detail.lower()

    after = _snapshot(db, student["user_id"])
    assert before == after, f"State changed on failed booking: before={before} after={after}"
    bot.close()


def test_rollback_on_ground_trigger(fresh_db, api_url, db):
    """A Student trying to book OAT/Pronite must be blocked by the authority trigger,
       and nothing (booking header, wallet debit, txn row) should remain."""
    cred = _parse_credentials()
    student = next(c for c in cred if c["role"] == "Student")

    with db.cursor() as cur:
        cur.execute("UPDATE Users SET wallet_balance = 10000 WHERE user_id = %s;", (student["user_id"],))

    # OAT is facility_id 9 (9th in FACILITY_DEFS); grab dynamically just in case
    with db.cursor() as cur:
        cur.execute("SELECT facility_id FROM Facilities WHERE type = 'OAT' LIMIT 1;")
        oat = cur.fetchone()[0]

    before = _snapshot(db, student["user_id"])

    bot = Bot(student["email"], student["password"], api=api_url); bot.login()
    slots = bot.availability(oat, (date.today() + timedelta(days=5)).isoformat())
    assert slots, "OAT had no slots"

    with pytest.raises(BotError) as ei:
        bot.book(oat, (date.today() + timedelta(days=5)).isoformat(), [slots[0]["slot_id"]])
    assert "organizations" in ei.value.detail.lower() or "access denied" in ei.value.detail.lower()

    after = _snapshot(db, student["user_id"])
    assert before == after, f"Ground-block rollback failed: before={before} after={after}"
    bot.close()


def test_rollback_on_bad_slot_id(fresh_db, api_url, db):
    """Request a slot_id that belongs to a DIFFERENT facility. Must 400 and leave no trace."""
    cred = _parse_credentials()
    student = next(c for c in cred if c["role"] == "Student")
    with db.cursor() as cur:
        cur.execute("UPDATE Users SET wallet_balance = 1000 WHERE user_id = %s;", (student["user_id"],))

    before = _snapshot(db, student["user_id"])

    bot = Bot(student["email"], student["password"], api=api_url); bot.login()
    with pytest.raises(BotError) as ei:
        bot.book(facility_id=3, date=(date.today() + timedelta(days=6)).isoformat(),
                 slot_ids=[999_999])
    assert ei.value.status == 400

    after = _snapshot(db, student["user_id"])
    assert before == after
    bot.close()


def test_cancellation_refund_atomic(fresh_db, api_url, db):
    """Create → cancel round trip. Net wallet change = 0, one Payment + one Refund."""
    cred = _parse_credentials()
    student = next(c for c in cred if c["role"] == "Student")
    with db.cursor() as cur:
        cur.execute("UPDATE Users SET wallet_balance = 1000 WHERE user_id = %s;", (student["user_id"],))

    before = _snapshot(db, student["user_id"])

    bot = Bot(student["email"], student["password"], api=api_url); bot.login()
    slots = bot.availability(1, (date.today() + timedelta(days=7)).isoformat())
    paid = next(s for s in slots if Decimal(s["price"]) > 0)
    res = bot.book(1, (date.today() + timedelta(days=7)).isoformat(), [paid["slot_id"]])
    bot.cancel(res["booking_id"])

    after = _snapshot(db, student["user_id"])
    # wallet unchanged, bookings +1 (cancelled but still in table), txs +2 (payment+refund)
    assert after[0] == before[0], f"Net wallet should match after cancel: {before} → {after}"
    assert after[1] == before[1] + 1
    assert after[2] == before[2] + 2
    bot.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
