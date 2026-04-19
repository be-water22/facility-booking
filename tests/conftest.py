"""
conftest.py — pytest fixtures.

- `api_url`   : returns the running API base URL; skips if the API is unreachable.
- `fresh_db`  : re-runs seed.py so a test gets a pristine DB state.
- `db_conn`   : direct psycopg2 connection (for constraint / rollback tests).
"""
from __future__ import annotations

import os
import subprocess
import sys
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
    """Re-seed the database so the caller gets a known starting state."""
    result = subprocess.run(
        [sys.executable, "seed.py"], cwd=REPO_ROOT,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"seed.py failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")


@pytest.fixture
def db_conn():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()
