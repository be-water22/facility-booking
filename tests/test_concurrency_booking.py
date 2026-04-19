"""
test_concurrency_booking.py — 30 bots race for the SAME slot at the SAME time.

Expected result:
  * Exactly 1 booking succeeds (the first commit wins).
  * The other 29 get a 400 with "Slot X on … is already booked" raised by
    the `prevent_double_booking` trigger or the partial UNIQUE index.
  * No orphan Booking_Slots rows exist for the losing carts.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import psycopg2
import pytest

from tests.bots import load_bots, BotError

NUM_BOTS = 30
# Lab 1 is a safe non-restricted facility; pick an early, free slot for the race.
TARGET_FACILITY = 3
TARGET_DATE     = (date.today() + timedelta(days=2)).isoformat()


def test_only_one_booking_wins(fresh_db, api_url):
    bots = load_bots(n=NUM_BOTS, role="Student", api=api_url)

    # Pick the first available slot for the target facility/date — same one for all bots
    slots = bots[0].availability(TARGET_FACILITY, TARGET_DATE)
    assert slots, "No slots available to race on"
    target_slot = slots[0]["slot_id"]

    # Give every bot enough balance (slot may be priced; free slots also fine)
    for b in bots:
        if b.wallet() < 1000:
            b.deposit(1000)

    # Fire N parallel POST /bookings requests on the same slot/date
    results: list[tuple[int, bool, str]] = []
    def race(bot):
        try:
            r = bot.book(TARGET_FACILITY, TARGET_DATE, [target_slot])
            return (bot.user["user_id"], True, f"booking_id={r['booking_id']}")
        except BotError as e:
            return (bot.user["user_id"], False, e.detail)

    with ThreadPoolExecutor(max_workers=NUM_BOTS) as ex:
        results = list(ex.map(race, bots))

    wins   = [r for r in results if r[1]]
    losses = [r for r in results if not r[1]]

    print(f"\n▸ {len(wins)} booking(s) succeeded, {len(losses)} failed")
    for uid, _ok, msg in wins[:3]:
        print(f"   WIN  user_id={uid}  {msg}")
    for uid, _ok, msg in losses[:3]:
        print(f"   FAIL user_id={uid}  {msg[:90]}")

    assert len(wins) == 1, (
        f"Expected exactly 1 winner, got {len(wins)}. "
        "The prevent_double_booking trigger failed to serialize.")
    assert len(losses) == NUM_BOTS - 1

    # Losers must have failed with a conflict message, not some other error
    collision_phrases = ("already booked", "already exists", "duplicate key")
    unexpected = [l for l in losses if not any(p in l[2].lower() for p in collision_phrases)]
    assert not unexpected, f"Unexpected failure reasons: {unexpected[:3]}"

    # Verify the DB agrees: exactly 1 Booking_Slots row for this slot+date that's not Cancelled
    conn = psycopg2.connect(dbname="campus_booking", user="postgres",
                            password="postgres", host="localhost", port=5432)
    with conn, conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM Booking_Slots bs
              JOIN Bookings b ON b.booking_id = bs.booking_id
             WHERE bs.slot_id = %s
               AND b.booking_date = %s
               AND b.status IN ('Pending','Confirmed');
        """, (target_slot, TARGET_DATE))
        live = cur.fetchone()[0]
    conn.close()
    assert live == 1, f"Expected 1 live booking in DB, found {live}"

    for b in bots:
        b.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
