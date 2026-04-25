"""
conftest.py — pytest fixtures.

- `api_url`   : returns the running API base URL; skips if the API is unreachable.
- `fresh_db`  : clears only bookings and transactions so tests get a clean slate
                WITHOUT wiping users or facilities (seed.py only needs to be run once).
- `db_conn`   : direct psycopg2 connection (for constraint / rollback tests).
"""
from __future__ import annotations

import os
from pathlib import Path

import httpx
import psycopg2
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
API_URL   = os.getenv("API_URL", "http://localhost:8000")

DB_CONFIG = {
    "dbname":   os.getenv("DB_NAME",     "campus_booking"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
}


@pytest.fixture(scope="session")
def api_url() -> str:
    try:
        httpx.get(f"{API_URL}/api/health", timeout=3.0).raise_for_status()
    except Exception as exc:
        pytest.skip(f"API not reachable at {API_URL}: {exc}. "
                    f"Start it with `uvicorn main:app --port 8000` and re-run.")
    return API_URL


@pytest.fixture
def fresh_db() -> None:
    """Reset only transactional data between tests.

    Truncates Booking_Slots, Bookings, and Wallet_Transactions and restores
    every user's wallet to 1000 so tests have a predictable starting balance.
    Users, Facilities, Facility_Rooms, and Facility_Slots are left untouched —
    seed.py only needs to be run once during initial setup.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                TRUNCATE Booking_Slots, Bookings, Wallet_Transactions
                RESTART IDENTITY CASCADE;
            """)
            cur.execute("UPDATE Users SET wallet_balance = 1000.00;")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def db_conn():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()
