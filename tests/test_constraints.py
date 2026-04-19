"""
test_constraints.py — direct DB-level tests.

These hit Postgres directly (bypassing the API) to verify every CHECK /
UNIQUE / trigger fires as designed.
"""
from __future__ import annotations

import pytest
import psycopg2
from psycopg2 import errors

from tests.conftest import DB_CONFIG


@pytest.fixture
def conn(fresh_db):
    c = psycopg2.connect(**DB_CONFIG)
    c.autocommit = False
    try: yield c
    finally: c.rollback(); c.close()


def test_password_format_check(conn):
    """Users.password must match ^[A-Za-z]{4}[0-9]{4}$ (4 letters + 4 digits)."""
    with conn.cursor() as cur:
        with pytest.raises(errors.CheckViolation):
            cur.execute("UPDATE Users SET password = '1234abcd' WHERE user_id = 1;")


def test_wallet_balance_never_negative(conn):
    with conn.cursor() as cur:
        with pytest.raises(errors.CheckViolation):
            cur.execute("UPDATE Users SET wallet_balance = -5 WHERE user_id = 1;")


def test_base_type_check(conn):
    with conn.cursor() as cur:
        with pytest.raises(errors.CheckViolation):
            cur.execute("""INSERT INTO Users (name, email, base_type)
                           VALUES ('X', 'x@y', 'Hacker');""")


def test_email_unique(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT email FROM Users LIMIT 1;")
        e = cur.fetchone()[0]
        with pytest.raises(errors.UniqueViolation):
            cur.execute("""INSERT INTO Users (name, email, base_type, password)
                           VALUES ('Clone', %s, 'Student', 'abcd1234');""", (e,))


def test_wallet_txn_amount_positive(conn):
    with conn.cursor() as cur:
        with pytest.raises(errors.CheckViolation):
            cur.execute("""INSERT INTO Wallet_Transactions
                           (user_id, amount, transaction_type, description)
                           VALUES (1, 0, 'Payment', 'zero');""")


def test_facility_slot_endtime_after_start(conn):
    with conn.cursor() as cur:
        with pytest.raises(errors.CheckViolation):
            cur.execute("""INSERT INTO Facility_Slots (facility_id, start_time, end_time, price)
                           VALUES (3, '10:00', '08:00', 100);""")


def test_facility_slot_unique(conn):
    with conn.cursor() as cur:
        with pytest.raises(errors.UniqueViolation):
            cur.execute("""INSERT INTO Facility_Slots (facility_id, start_time, end_time, price)
                           VALUES (3, '06:00', '08:00', 0);""")  # already seeded


def test_double_booking_trigger(conn):
    """Insert two Booking_Slots rows on the same slot/date — trigger must raise."""
    with conn.cursor() as cur:
        # Create a fresh booking referencing slot 25 (facility 4, 06:00-08:00)
        cur.execute("""INSERT INTO Bookings (user_id, booking_date, total_cost, status)
                       VALUES (1, CURRENT_DATE + 10, 0, 'Confirmed') RETURNING booking_id;""")
        b1 = cur.fetchone()[0]
        cur.execute("""INSERT INTO Booking_Slots (booking_id, slot_id, price_charged)
                       VALUES (%s, 25, 0);""", (b1,))

        cur.execute("""INSERT INTO Bookings (user_id, booking_date, total_cost, status)
                       VALUES (2, CURRENT_DATE + 10, 0, 'Confirmed') RETURNING booking_id;""")
        b2 = cur.fetchone()[0]
        with pytest.raises(errors.RaiseException) as ei:
            cur.execute("""INSERT INTO Booking_Slots (booking_id, slot_id, price_charged)
                           VALUES (%s, 25, 0);""", (b2,))
        assert "already booked" in str(ei.value).lower()


def test_ground_booking_trigger_blocks_non_org(conn):
    """Student (non-Org) tries to book an OAT slot — authority trigger must block."""
    with conn.cursor() as cur:
        cur.execute("SELECT slot_id FROM Facility_Slots fs JOIN Facilities f "
                    "ON f.facility_id=fs.facility_id WHERE f.type='OAT' LIMIT 1;")
        oat_slot = cur.fetchone()[0]
        # user_id 1 is a student per seed ordering
        cur.execute("""INSERT INTO Bookings (user_id, booking_date, total_cost, status)
                       VALUES (1, CURRENT_DATE + 11, 0, 'Confirmed') RETURNING booking_id;""")
        b = cur.fetchone()[0]
        with pytest.raises(errors.RaiseException) as ei:
            cur.execute("""INSERT INTO Booking_Slots (booking_id, slot_id, price_charged)
                           VALUES (%s, %s, 0);""", (b, oat_slot))
        assert "organizations" in str(ei.value).lower()


def test_org_CAN_book_OAT(conn):
    """Counter-test: an Organization user MUST be able to book OAT."""
    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM Users WHERE base_type='Organization' LIMIT 1;")
        org = cur.fetchone()[0]
        cur.execute("SELECT slot_id FROM Facility_Slots fs JOIN Facilities f "
                    "ON f.facility_id=fs.facility_id WHERE f.type='OAT' LIMIT 1;")
        oat_slot = cur.fetchone()[0]
        cur.execute("""INSERT INTO Bookings (user_id, booking_date, total_cost, status)
                       VALUES (%s, CURRENT_DATE + 12, 0, 'Confirmed') RETURNING booking_id;""", (org,))
        b = cur.fetchone()[0]
        # Must succeed
        cur.execute("""INSERT INTO Booking_Slots (booking_id, slot_id, price_charged)
                       VALUES (%s, %s, 0);""", (b, oat_slot))


def test_delete_user_with_bookings_is_restricted(conn):
    """ON DELETE RESTRICT on Bookings.user_id prevents deleting users with history."""
    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM Bookings LIMIT 1;")
        u = cur.fetchone()[0]
        with pytest.raises(errors.ForeignKeyViolation):
            cur.execute("DELETE FROM Users WHERE user_id = %s;", (u,))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
