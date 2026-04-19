"""
bots.py — reusable test-bot helpers.

A `Bot` wraps the API client for one user (email + password). It logs in,
caches the profile, then exposes book/cancel/deposit/profile helpers.

The `load_bots()` helper parses `credentials.txt` (produced by seed.py) and
returns N bots ready to go.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import httpx

DEFAULT_API = os.getenv("API_URL", "http://localhost:8000")
CRED_FILE = Path(__file__).resolve().parent.parent / "credentials.txt"


@dataclass
class Bot:
    email: str
    password: str
    api:    str = DEFAULT_API
    user:   dict | None = field(default=None, repr=False)
    client: httpx.Client = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.client = httpx.Client(base_url=self.api, timeout=15.0)

    # ---------- low-level ----------
    def _json(self, r: httpx.Response) -> dict:
        try:
            body = r.json()
        except Exception:
            body = {"detail": r.text}
        if r.status_code >= 400:
            raise BotError(r.status_code, body.get("detail", str(body)))
        return body

    # ---------- API actions ----------
    def login(self) -> dict:
        self.user = self._json(self.client.post("/api/login",
            json={"email": self.email, "password": self.password}))
        return self.user

    def profile(self) -> dict:
        assert self.user, "login() first"
        self.user = self._json(self.client.get(f"/api/users/{self.user['user_id']}"))
        return self.user

    def wallet(self) -> float:
        return float(self.profile()["wallet_balance"])

    def deposit(self, amount: float) -> dict:
        return self._json(self.client.post("/api/wallet/deposit",
            json={"user_id": self.user["user_id"], "amount": amount}))

    def availability(self, facility_id: int, date: str, room_id: int | None = None) -> list[dict]:
        params = {"date": date}
        if room_id is not None:
            params["room_id"] = room_id
        return self._json(self.client.get(
            f"/api/facilities/{facility_id}/availability", params=params))

    def book(self, facility_id: int, date: str, slot_ids: list[int],
             room_id: int | None = None) -> dict:
        return self._json(self.client.post("/api/bookings", json={
            "user_id":     self.user["user_id"],
            "facility_id": facility_id,
            "booking_date": date,
            "slot_ids":    slot_ids,
            "room_id":     room_id,
        }))

    def cancel(self, booking_id: int) -> dict:
        return self._json(self.client.post(
            f"/api/bookings/{booking_id}/cancel",
            params={"user_id": self.user["user_id"]}))

    def close(self) -> None:
        self.client.close()


class BotError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _parse_credentials() -> list[dict]:
    """Parse credentials.txt produced by seed.py. Format:
       user_id  role          email                                     password
    """
    if not CRED_FILE.exists():
        raise FileNotFoundError(
            f"{CRED_FILE} not found — run `python seed.py` first.")
    rows: list[dict] = []
    for line in CRED_FILE.read_text().splitlines():
        m = re.match(r"^(\d+)\s+(\S+)\s+(\S+)\s+([A-Za-z]{4}\d{4})\s*$", line)
        if m:
            rows.append({"user_id": int(m.group(1)), "role": m.group(2),
                         "email":   m.group(3),     "password": m.group(4)})
    return rows


def load_bots(n: int = 20, role: str | None = "Student",
              api: str = DEFAULT_API) -> list[Bot]:
    """Return N bots of the given role (default Student). All are already logged in."""
    pool = [c for c in _parse_credentials() if role is None or c["role"] == role]
    if len(pool) < n:
        raise ValueError(f"Only {len(pool)} {role} users available, asked for {n}.")
    bots = [Bot(c["email"], c["password"], api=api) for c in pool[:n]]
    for b in bots:
        b.login()
    return bots


def get_admin_bot(api: str = DEFAULT_API) -> Bot:
    admins = [c for c in _parse_credentials() if c["role"] == "Admin"]
    if not admins:
        raise RuntimeError("No admin credentials found.")
    b = Bot(admins[0]["email"], admins[0]["password"], api=api)
    b.login()
    return b
