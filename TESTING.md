# Testing Guide

This document describes both the **manual UI tests** and the **automated pytest suite** for the Campus Facility Booking System. The test suite covers all four ACID properties (Atomicity, Consistency, Isolation, Durability), every CHECK constraint, every trigger, and concurrency scenarios.

Before starting, complete the setup steps in [README.md](README.md) so the backend is running at `http://localhost:8000` with a seeded database.

## Conventions

| Marker | Meaning                                                               |
|--------|-----------------------------------------------------------------------|
| PASS   | Expected: action succeeds                                             |
| FAIL   | Expected: action is rejected (the test is valid if rejection happens) |

Each manual step follows: **Setup → Action → Expected**. Record any mismatch as an issue.

---

# Part 1 — Manual UI Tests

## 1. Authentication

### 1.1 Valid login as a regular user [PASS]
1. Open http://localhost:8000.
2. Enter email `aryan.maharaj91@iitk.ac.in` and the matching password from `credentials.txt`.
3. Click **Log in**.
4. **Expected:** Profile page loads; top bar shows name, role badge **Student**, wallet chip.

### 1.2 Valid login as admin [PASS]
1. Email `admin1@iitk.ac.in` with the matching password.
2. **Expected:** Top bar shows red **Admin** badge. Nav bar adds **All Transactions**, **Utilization**, **Facilities** tabs.

### 1.3 Invalid password [FAIL]
1. Email `admin1@iitk.ac.in` / password `wrong1234`.
2. **Expected:** Red error "Invalid email or password." appears below the form.

### 1.4 Wrong password format [FAIL]
1. Password `abc`.
2. **Expected:** Client-side error "Password must be 4 letters followed by 4 digits." — no network call is made.

### 1.5 Logout
1. While logged in, click **Logout**.
2. **Expected:** Back to login screen, password and email fields cleared.

---

## 2. Profile

### 2.1 Profile fields render correctly [PASS]
1. Log in as any student.
2. **Expected:** Profile shows User ID, Name, Email, Role, Wallet Balance, Member Since, Roll Number. Balance matches the chip.

### 2.2 Organization shows Org Type
1. Log in as `antaragni@orgs.iitk.ac.in`.
2. **Expected:** Profile shows "Organization Type" (Club / Festival_Committee / Society).

### 2.3 Wallet top-up [PASS]
1. On Profile, enter `500` in the top-up amount, click **Deposit**.
2. **Expected:**
   - Green "Deposited ₹500.00." message
   - Wallet chip increases by 500
   - Profile wallet row increases by 500

### 2.4 Invalid deposit [FAIL]
1. Enter `0` or `-100` and click **Deposit**.
2. **Expected:** Red error; no change to wallet.

---

## 3. Booking — happy path

### 3.1 Browse by facility type
1. Log in as any student with sufficient balance.
2. Click **Book a Slot**.
3. Change **Facility type** to `Lab`.
4. **Expected:** Facility dropdown shows 3 labs.

### 3.2 Only available slots are visible
1. Select a lab, pick tomorrow's date.
2. **Expected:** Up to 8 slots appear. Slots already booked elsewhere are hidden.

### 3.3 Select slots, live total
1. Click 2 slots.
2. **Expected:** Slots highlight blue; footer shows `Total: ₹X · Wallet: ₹Y`.

### 3.4 Confirm booking [PASS]
1. Click **Confirm Booking**.
2. **Expected:**
   - Green "Booking #N confirmed. Charged ₹X." message
   - Slots disappear from the list (availability re-fetched)
   - Wallet chip decreases by charged amount
3. Go to **Profile** → **My Recent Bookings** shows the new booking with status **Confirmed**.

### 3.5 Hall guest room — room dropdown appears
1. Facility type `Hall_Guest_Room`.
2. **Expected:** A **Room** dropdown appears listing "Hall N – Room 1/2". Availability is per-room.

### 3.6 Book a free (₹0) slot
1. Pick the 06:00–08:00 slot (price ₹0).
2. **Expected:** Booking succeeds, wallet unchanged, no `Payment` transaction row created.

---

## 4. Booking — business rules

### 4.1 Insufficient balance [FAIL]
1. As a student with wallet < slot price, try to book.
2. **Expected:** Footer shows "(insufficient balance)" in red, Confirm button disabled. If forced via API, backend returns 400 and nothing persists.

### 4.2 Student cannot book OAT [FAIL]
1. Facility type `OAT` → Open Air Theatre.
2. Try to confirm.
3. **Expected:** Red error "Access Denied: Only official Organizations can book major grounds..." raised by the `validate_ground_booking` trigger.

### 4.3 Organization CAN book OAT [PASS]
1. Log out, log in as any organization (e.g. `antaragni@orgs.iitk.ac.in`).
2. Book an OAT slot.
3. **Expected:** Success.

### 4.4 Cancel a booking (refund) [PASS]
1. From Profile → Bookings, click **Cancel** on any Confirmed booking.
2. Confirm the prompt.
3. **Expected:**
   - Status flips to **Cancelled**
   - Wallet chip increases by `total_cost`
   - **My Transactions** shows a new `Refund` row at the top

### 4.5 Cancel twice [FAIL]
1. Try to cancel the same booking again.
2. **Expected:** Cancel button is gone in the UI. If forced via API, backend returns 400 "Already cancelled."

---

## 5. Transactions (My Transactions)

### 5.1 History matches actions
1. Log in as a user who has booked + cancelled + deposited.
2. Click **My Transactions**.
3. **Expected:** Rows in reverse-chronological order: Refund → Payment → Deposit. Amounts match.

### 5.2 Sign and colour coding
1. **Expected:** Payments show `−` in red; Deposits/Refunds show `+` in green/blue.

---

## 6. Admin features

### 6.1 All Transactions [PASS]
1. Log in as admin → click **All Transactions**.
2. **Expected:** Every transaction across all users.
3. Filter by type = `Payment`, then add a partial name in the search box. **Expected:** Filters combine.

### 6.2 Utilization report [PASS]
1. Click **Utilization**. No date filter.
2. **Expected:** Table of all 15 facilities with Type, Capacity, Operational, Bookings, Slots booked, Revenue (sorted by Revenue DESC).

### 6.3 Take a facility off-line [PASS]
1. Click **Facilities** → **Take off-line** on "Electronics Lab".
2. **Expected:** Status flips to "Off".
3. Logout → log in as a student → **Book a Slot** → Facility type `Lab`. **Expected:** Electronics Lab no longer in dropdown.
4. As admin, bring it back on-line. **Expected:** Reappears.

### 6.4 Non-admin cannot reach admin endpoints [FAIL]
1. In browser devtools, try `fetch('/api/admin/transactions?admin_id=1')` as a student.
2. **Expected:** HTTP 403 "Admin access required."

---

# Part 2 — Automated Test Suite

The automated suite lives in [tests/](tests/) and covers all four ACID properties. Run from the repo root:

```bash
pytest -v tests/
```

The server must be running (`uvicorn main:app --reload`) in a separate terminal.

## How tests work

The suite uses two fixtures defined in [`tests/conftest.py`](tests/conftest.py):

- **`fresh_db`** — truncates `Booking_Slots`, `Bookings`, and `Wallet_Transactions`, then resets every user's wallet to ₹1000. Users, facilities, rooms, and slots are preserved (no need to re-run `seed.py`).
- **`api_url`** — confirms the backend is up by hitting `/api/health`. Skips tests if unreachable.

The bot harness in [`tests/bots.py`](tests/bots.py) parses `credentials.txt` and returns logged-in `Bot` instances that wrap `httpx.Client`. Each bot exposes `login / profile / deposit / availability / book / cancel`.

## Mapping tests to ACID properties

| ACID Property | Test File | What it proves |
|---------------|-----------|----------------|
| Atomicity     | `test_rollback.py` | Failures roll back wallet, bookings, and ledger entries — all-or-nothing |
| Consistency   | `test_constraints.py` | CHECK / UNIQUE constraints and triggers reject every illegal state |
| Isolation     | `test_concurrency_booking.py` + `test_concurrency_wallet.py` | Concurrent transactions don't interfere — advisory locks + `SELECT FOR UPDATE` serialize correctly |
| Durability    | All tests (implicit) | Committed transactions survive — every assertion that reads back from the DB confirms it |

---

## 7. Concurrency tests (Isolation)

### 7.1 `test_concurrency_booking.py` — 30 bots race the same slot

**File:** [tests/test_concurrency_booking.py](tests/test_concurrency_booking.py)

**What it does:**
1. Loads 30 student bots from `credentials.txt` (each bot is a logged-in API client)
2. Picks the first available slot for a target facility/date — the **same slot for every bot**
3. Tops up each bot's wallet to ≥ ₹1000
4. Uses a `ThreadPoolExecutor` with 30 workers to fire 30 simultaneous `POST /api/bookings` requests for that one slot
5. Counts wins (HTTP 201) and losses (HTTP 400)

**What it proves:**
- Exactly **1** booking succeeds — the first transaction to acquire the advisory lock wins
- The other **29** are rejected with "Slot X on date is already booked"
- A direct DB query confirms exactly 1 live `Booking_Slots` row exists for that slot+date

**ACID property tested: Isolation**

This is the core race condition test. Without protection, two transactions in `READ COMMITTED` could both pass the `prevent_double_booking` trigger check (since neither sees the other's uncommitted insert) and both succeed. Two safeguards make this impossible:

1. **`pg_advisory_xact_lock(slot_id, date_int)`** — added in `main.py` before any insert. The second concurrent request blocks until the first commits.
2. **`prevent_double_booking` trigger** in `schema.sql` — once unblocked, the trigger sees the now-committed first booking and raises an exception.

Together these enforce serializable behaviour for booking the same slot, even under heavy parallelism.

---

### 7.2 `test_concurrency_wallet.py` — 20 bots drain one wallet

**File:** [tests/test_concurrency_wallet.py](tests/test_concurrency_wallet.py)

**What it does:**
1. Picks one student and resets their wallet to exactly ₹500 via direct DB write
2. Picks 20 distinct ₹200 slots (across multiple non-restricted facilities)
3. Creates 20 separate `Bot` instances all logged in as the same student
4. Fires 20 concurrent `POST /api/bookings` requests in parallel
5. Verifies the final wallet balance and counts successful payments

**What it proves:**
- Exactly **`floor(500 / 200) = 2`** bookings succeed — no over-spending
- Wallet ends at exactly **₹100** (`500 − 2 × 200`) — never negative
- The number of `Wallet_Transactions` payment rows equals the winners
- Failures all carry an "insufficient balance" reason — no random 500 errors

**ACID property tested: Isolation (row-level locking)**

The test exercises the **`SELECT user_id, wallet_balance FROM Users WHERE user_id = %s FOR UPDATE`** statement in `create_booking` (main.py). Without `FOR UPDATE`, two concurrent bookings could both read wallet=₹500, both decide they have enough for ₹200, and both succeed — leaving the wallet at ₹100 instead of debiting twice from ₹500.

`FOR UPDATE` acquires a row-level exclusive lock on the user row. The second transaction blocks until the first commits or rolls back. When it unblocks, it re-reads the now-debited wallet and correctly decides whether to proceed. This guarantees the wallet `CHECK (wallet_balance >= 0)` constraint is never violated regardless of concurrency.

---

## 8. Rollback / Atomicity tests

### 8.1 `test_rollback_on_insufficient_balance`

**File:** [tests/test_rollback.py](tests/test_rollback.py)

**What it does:**
1. Sets a student's wallet to ₹10 (via direct DB write)
2. Snapshots `(wallet_balance, count(bookings), count(transactions))`
3. Tries to book a ₹500 slot — expects `BotError`
4. Snapshots again and asserts no change

**What it proves:** A failed booking leaves **zero traces**. No `Bookings` row, no `Booking_Slots` row, no wallet debit, no `Wallet_Transactions` row.

**ACID property tested: Atomicity**

The booking endpoint runs all writes (booking header, line items, wallet debit, ledger entry) inside a single transaction. When the balance check fails, `conn.rollback()` undoes everything that was tentatively written. The pre-state and post-state are byte-identical.

---

### 8.2 `test_rollback_on_ground_trigger`

**What it does:**
1. Gives a student ₹10000 (so balance is *not* the failure cause)
2. Tries to book an OAT slot — should be blocked by the `validate_ground_booking` trigger
3. Asserts wallet/bookings/transactions all unchanged

**What it proves:** When a trigger raises mid-transaction, every prior insert in that transaction rolls back. The booking header inserted before the line item is also reverted.

**ACID property tested: Atomicity** — trigger-raised exceptions trigger a full rollback, not just the failing statement.

---

### 8.3 `test_rollback_on_bad_slot_id`

**What it does:** Sends a `POST /api/bookings` with `slot_ids: [999_999]` (a non-existent slot for the requested facility). Expects HTTP 400 and zero state change.

**What it proves:** Validation errors that fire **before** any insert leave the DB clean — no half-created booking headers.

---

### 8.4 `test_cancellation_refund_atomic`

**What it does:**
1. Books a paid slot
2. Immediately cancels it
3. Verifies: wallet net change = 0, bookings count +1 (cancelled but kept for history), transactions count +2 (one Payment + one Refund)

**What it proves:** Cancellation is atomic — the wallet is refunded *and* the booking is marked Cancelled *and* the refund row is logged, all in one commit. Either everything happens or nothing does.

**ACID property tested: Atomicity** — the `cancel_booking` endpoint touches three tables (`Bookings`, `Users`, `Wallet_Transactions`) inside one `with conn.cursor()` block followed by `conn.commit()`.

---

## 9. Constraint tests (Consistency)

**File:** [tests/test_constraints.py](tests/test_constraints.py)

These hit PostgreSQL directly (bypassing the API) to verify every CHECK / UNIQUE / trigger fires exactly when violated. Each test uses the `conn` fixture which provides a direct `psycopg2` connection in a transaction that's always rolled back at teardown.

### 9.1 `test_password_format_check`
**SQL:** `UPDATE Users SET password = '1234abcd' WHERE user_id = 1;`
**Expected:** `CheckViolation` — password must match `^[A-Za-z]{4}[0-9]{4}$` (4 letters + 4 digits).

### 9.2 `test_wallet_balance_never_negative`
**SQL:** `UPDATE Users SET wallet_balance = -5 WHERE user_id = 1;`
**Expected:** `CheckViolation` — `CHECK (wallet_balance >= 0)`.

### 9.3 `test_base_type_check`
**SQL:** `INSERT INTO Users (..., base_type) VALUES (..., 'Hacker');`
**Expected:** `CheckViolation` — `base_type IN ('Student', 'Faculty', 'Admin', 'Organization')`.

### 9.4 `test_email_unique`
**SQL:** Insert a row with an email that already exists.
**Expected:** `UniqueViolation` — `email VARCHAR(100) UNIQUE NOT NULL`.

### 9.5 `test_wallet_txn_amount_positive`
**SQL:** `INSERT INTO Wallet_Transactions (..., amount) VALUES (..., 0);`
**Expected:** `CheckViolation` — `CHECK (amount > 0)`. Zero-amount transactions are ledger noise and must be rejected.

### 9.6 `test_facility_slot_endtime_after_start`
**SQL:** `INSERT INTO Facility_Slots (..., start_time, end_time) VALUES (..., '10:00', '08:00', ...);`
**Expected:** `CheckViolation` — `CHECK (end_time > start_time)`.

### 9.7 `test_facility_slot_unique`
**SQL:** Insert a duplicate `(facility_id, start_time, end_time)`.
**Expected:** `UniqueViolation` — `UNIQUE (facility_id, start_time, end_time)`. No two facility slots can have the same time window for the same facility.

### 9.8 `test_double_booking_trigger`
**Action:** Insert two `Booking_Slots` rows for the **same slot, same date** under two different bookings.
**Expected:** The `prevent_double_booking` trigger raises `RAISE EXCEPTION 'Slot X on ... is already booked'`.

This is the *direct DB* version of test 7.1 — it confirms the trigger logic itself works, regardless of how the application calls it.

### 9.9 `test_ground_booking_trigger_blocks_non_org`
**Action:** Student tries to insert a `Booking_Slots` row pointing to an OAT slot.
**Expected:** The `validate_ground_booking` trigger raises `'Access Denied: Only official Organizations can book major grounds...'`.

### 9.10 `test_org_CAN_book_OAT` (counter-test)
**Action:** Organization user inserts an OAT booking.
**Expected:** Succeeds. Verifies the trigger lets the *correct* base_type through — it's not blanket-blocking everyone.

### 9.11 `test_delete_user_with_bookings_is_restricted`
**SQL:** `DELETE FROM Users WHERE user_id = (SELECT user_id FROM Bookings LIMIT 1);`
**Expected:** `ForeignKeyViolation` — `Bookings.user_id REFERENCES Users(user_id) ON DELETE RESTRICT`. Booking history must be preserved; users with bookings cannot be deleted.

**ACID property tested: Consistency** — every test in this suite confirms the database refuses to enter an invalid state, regardless of how the violation is attempted.

---

## 10. Resetting between manual sessions

If you've been poking the DB by hand and want a clean slate:

```bash
psql -U postgres campus_booking < schema.sql   # only if you want to rebuild tables
python seed.py                                  # truncates + re-seeds + rewrites credentials.txt
```

The automated test suite does NOT need this — the `fresh_db` fixture handles state reset between tests and only touches `Booking_Slots`, `Bookings`, and `Wallet_Transactions`.
