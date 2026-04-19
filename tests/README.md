# Automated tests

Four pytest modules + a bot harness. All tests re-seed the DB to a known state before running, so they're independent and repeatable.

## Prerequisites

1. **Docker Compose stack up**
   ```bash
   docker compose up -d
   ```
2. **Python deps**
   ```bash
   pip install -r requirements.txt
   ```
3. **FastAPI server running** (separate terminal)
   ```bash
   python -m uvicorn main:app --port 8000 --reload
   ```

## Run everything

From the repo root:

```bash
pytest -v tests/
```

## Run individual suites

```bash
pytest -v tests/test_concurrency_booking.py   # 30 bots race for the same slot
pytest -v tests/test_concurrency_wallet.py    # 20 bots spending one wallet
pytest -v tests/test_rollback.py              # transaction rollback paths
pytest -v tests/test_constraints.py           # direct CHECK/UNIQUE/trigger
```

Or as plain scripts (falls back to `pytest.main`):

```bash
python tests/test_concurrency_booking.py
```

## What each suite proves

| File | Property tested |
|---|---|
| `test_concurrency_booking.py` | `prevent_double_booking` trigger + partial UNIQUE index serialize 30 parallel bookings of the same slot to exactly 1 winner. |
| `test_concurrency_wallet.py`  | `SELECT … FOR UPDATE` on `Users.wallet_balance` prevents double-spending across 20 parallel bookings on the same user. |
| `test_rollback.py`            | Every failure path (insufficient balance, trigger block, bad slot) leaves wallet, bookings, and ledger untouched. Cancellation round-trip is atomic. |
| `test_constraints.py`         | Every CHECK / UNIQUE / trigger on Users, Wallet_Transactions, Facility_Slots, Booking_Slots, Bookings fires exactly when it should. |

## How the bot harness works

`tests/bots.py` parses `credentials.txt` (produced by `seed.py`) and returns logged-in `Bot` instances. Each `Bot` wraps `httpx.Client` and exposes `login / profile / deposit / availability / book / cancel`.

```python
from tests.bots import load_bots
bots = load_bots(n=25, role="Student")          # 25 logged-in students
results = [b.book(3, "2026-05-01", [17]) for b in bots]
```

## Debug tips

- **Watch every SQL the server runs**: `docker compose logs -f postgres` — statement logging is enabled in the compose file.
- **Watch every HTTP request**: restart uvicorn with `--log-level debug`.
- **Poke the DB manually**: `docker exec -it campus_pg psql -U postgres -d campus_booking`.
