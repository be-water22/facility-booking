# Automated tests

Four pytest modules + a bot harness. The `fresh_db` fixture resets booking and transaction tables between tests, so they're independent and repeatable. Users and facilities are preserved (no need to re-run `seed.py`).

For detailed explanations of every test, the ACID property each one targets, and how concurrency is enforced, see [../TESTING.md](../TESTING.md).

## Prerequisites

1. **PostgreSQL running** with the `campus_booking` database created and seeded (see [../README.md](../README.md))
2. **Python deps**
   ```bash
   pip install -r requirements.txt
   ```
3. **FastAPI server running** (separate terminal)
   ```bash
   uvicorn main:app --reload
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

## What each suite proves

| File | Property tested |
|---|---|
| `test_concurrency_booking.py` | `prevent_double_booking` trigger + advisory locks serialize 30 parallel bookings of the same slot to exactly 1 winner. |
| `test_concurrency_wallet.py`  | `SELECT ... FOR UPDATE` on `Users.wallet_balance` prevents double-spending across 20 parallel bookings on the same user. |
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

- **Watch every HTTP request:** restart uvicorn with `--log-level debug`
- **Direct DB access:** `psql -U postgres campus_booking`
- **GUI browse:** TablePlus (see ../README.md for connection settings)
