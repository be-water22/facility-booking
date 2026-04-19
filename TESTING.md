# Manual Testing Plan

Step-by-step checklist for a human tester to verify every user-facing feature plus the DBMS guarantees (ACID, triggers, CHECK constraints, concurrency).

Before starting, complete the **Collaborator quickstart** in [README.md](README.md) so the backend is running at `http://localhost:8000` with a freshly seeded database.

## Conventions

| Term | Meaning |
|---|---|
| ✅ | Expected pass |
| ❌ | Expected fail (test is valid if the system rejects the action) |

Each step: **Setup → Action → Expected**. If the expected result doesn't happen, record the mismatch in an issue.

---

## 1. Authentication

### 1.1 Valid login as a regular user ✅
1. Open http://localhost:8000.
2. Enter email `aryan.maharaj91@iitk.ac.in` and password `bztf4238` (from `credentials.txt`).
3. Click **Log in**.
4. **Expected:** Profile page loads; top bar shows name, role badge *Student*, wallet chip (₹2753.00).

### 1.2 Valid login as admin ✅
1. Email `admin1@iitk.ac.in` / password `oflj6090`.
2. **Expected:** Top bar shows red *Admin* badge. Nav bar now has **All Transactions**, **Utilization**, **Facilities** tabs in addition to the standard three.

### 1.3 Invalid password ❌
1. Email `admin1@iitk.ac.in` / password `wrong1234`.
2. **Expected:** Red error "Invalid email or password." appears below the form.

### 1.4 Wrong password format ❌
1. Password `abc`.
2. **Expected:** Client-side error "Password must be 4 letters followed by 4 digits." — no network call is made.

### 1.5 Logout
1. While logged in, click **Logout**.
2. **Expected:** Back to login screen, password and email fields cleared.

---

## 2. Profile

### 2.1 Profile fields render correctly ✅
1. Log in as any student.
2. **Expected:** Profile table shows User ID, Name, Email, Role, Wallet Balance, Member Since, Roll Number. Balance matches the chip in the top bar.

### 2.2 Organization shows Org Type
1. Log in as `antaragni@orgs.iitk.ac.in`.
2. **Expected:** Profile shows "Organization Type: …" (Club / Festival_Committee / Society).

### 2.3 Wallet top-up (deposit) ✅
1. On Profile page, enter `500` in the top-up amount field, click **Deposit**.
2. **Expected:**
   - Green "Deposited ₹500.00." message.
   - Wallet chip in top bar increases by 500.
   - Profile wallet row increases by 500.

### 2.4 Invalid deposit ❌
1. Enter `0` or `-100` and click **Deposit**.
2. **Expected:** Red error; no change to wallet.

---

## 3. Booking — happy path

### 3.1 Browse by facility type
1. Log in as any student with ≥ ₹500 balance.
2. Click **Book a Slot**.
3. Change **Facility type** → `Lab`.
4. **Expected:** Facility dropdown now shows 3 labs (CS Lab 1, CS Lab 2, Electronics Lab).

### 3.2 Only available slots are visible
1. Select a lab, pick tomorrow's date.
2. **Expected:** 8 slots appear (06–22h). If any slot was already booked earlier in a prior test, it's hidden.

### 3.3 Select slots, live total
1. Click 2 slots.
2. **Expected:** Slots highlight blue; footer shows `Total: ₹X  ·  Wallet: ₹Y`.

### 3.4 Confirm booking ✅
1. Click **Confirm Booking**.
2. **Expected:**
   - Green "Booking #N confirmed. Charged ₹X." message.
   - Slots just booked disappear from the list (availability re-fetched).
   - Wallet chip decreases by charged amount.
3. Go to **Profile** → **My Recent Bookings** shows the new booking with status **Confirmed** and correct slot list.

### 3.5 Hall guest room — room dropdown appears
1. Facility type: `Hall_Guest_Room`.
2. **Expected:** A **Room** dropdown appears listing "Hall N – Room 1/2". Availability is per-room.

### 3.6 Book a free (₹0) slot
1. Pick the 06:00–08:00 slot (price ₹0).
2. **Expected:** Booking succeeds, wallet unchanged, no `Payment` transaction row created.

---

## 4. Booking — business rules

### 4.1 Insufficient balance ❌
1. As a student with wallet < slot price, try to book.
2. **Expected:** Footer shows "(insufficient balance)" in red, Confirm button disabled. If forced via API, backend returns 400 and nothing persists.

### 4.2 Student cannot book OAT ❌
1. Facility type: `OAT` → Open Air Theatre.
2. Try to confirm.
3. **Expected:** Red error "Access Denied: Only official Organizations can book major grounds…" (raised by the `validate_ground_booking` trigger).

### 4.3 Organization CAN book OAT ✅
1. Log out, log in as any organization (e.g. `antaragni@orgs.iitk.ac.in`).
2. Book an OAT slot.
3. **Expected:** Success.

### 4.4 Cancel a booking (refund) ✅
1. From Profile → Bookings, click **Cancel** on any Confirmed booking.
2. Confirm the prompt.
3. **Expected:**
   - Status flips to **Cancelled**.
   - Wallet chip increases by `total_cost`.
   - Go to **My Transactions** → a `Refund` row for the refunded amount now shows at the top.

### 4.5 Cancel twice ❌
1. Try to cancel the same booking again (shouldn't be possible via UI — Cancel button is gone).
2. If forced via API, **expected:** 400 "Already cancelled."

---

## 5. Transactions (My Transactions)

### 5.1 History matches actions
1. Log in as a user who has booked + cancelled + deposited during this session.
2. Click **My Transactions**.
3. **Expected:** Rows in reverse-chronological order: Refund → Payment → Deposit (opening). Amounts match.

### 5.2 Sign and colour coding
1. **Expected:** Payments show `−` in red; Deposits/Refunds show `+` in green/blue.

---

## 6. Admin features

### 6.1 All Transactions page ✅
1. Log in as admin.
2. Click **All Transactions**.
3. **Expected:** Every transaction across all users (see `credentials.txt` for a count, ~40 opening deposits + whatever was generated during testing).
4. Filter by type = `Payment`.
5. **Expected:** Only Payment rows shown; summary line updates.
6. Type a partial name in the search box (e.g. "aryan").
7. **Expected:** Filter combines with the type filter.

### 6.2 Utilization report ✅
1. Click **Utilization**. No date filter.
2. **Expected:** Table of all 15 facilities with Type, Capacity, Operational ✓, Bookings, Slots booked, Revenue (sorted by Revenue DESC).
3. Set `From` = today, `To` = today + 7 days.
4. **Expected:** Numbers shrink to only bookings in the window.

### 6.3 Take a facility off-line ✅
1. Click **Facilities**. Click **Take off-line** on "Electronics Lab".
2. **Expected:** Status flips to "Off" (red).
3. Logout → log in as a student → **Book a Slot** → Facility type = `Lab`.
4. **Expected:** Electronics Lab no longer appears in the facility dropdown.
5. As admin, bring it back on-line.
6. **Expected:** Reappears in the booking view.

### 6.4 Non-admin cannot reach admin endpoints ❌
1. In browser devtools, try `fetch('/api/admin/transactions?admin_id=1')` as a student.
2. **Expected:** HTTP 403 "Admin access required."

---

## 7. DBMS guarantees

Open a second terminal with `psql`:
```
docker exec -it campus_pg psql -U postgres -d campus_booking
```

### 7.1 ACID — wallet never negative
```sql
UPDATE Users SET wallet_balance = -1 WHERE user_id = 1;
```
**Expected:** `ERROR: new row for relation "users" violates check constraint "users_wallet_balance_check"`.

### 7.2 Password format CHECK
```sql
UPDATE Users SET password = '1234abcd' WHERE user_id = 1;
```
**Expected:** `ERROR: … violates check constraint "users_password_format_chk"`.

### 7.3 Email UNIQUE
```sql
INSERT INTO Users (name, email, base_type, password)
VALUES ('x', 'aryan.maharaj91@iitk.ac.in', 'Student', 'abcd1234');
```
**Expected:** `ERROR: duplicate key value violates unique constraint "users_email_key"`.

### 7.4 Double-booking trigger
Open a transaction that tries to insert a second Booking_Slots row on a slot/date already held by a Confirmed booking — must raise "Slot X on … is already booked".

### 7.5 ON DELETE RESTRICT on Bookings.user_id
```sql
DELETE FROM Users WHERE user_id = (SELECT user_id FROM Bookings LIMIT 1);
```
**Expected:** `ERROR: update or delete on table "users" violates foreign key constraint "bookings_user_id_fkey" on table "bookings"`.

---

## 8. Concurrency & recovery (automated)

These are implemented in [tests/](tests/). Run:

```bash
pytest -v tests/
```

### 8.1 30-bot same-slot race (`test_concurrency_booking.py`)
**Proves:** exactly 1 of 30 concurrent bookings of the same slot succeeds; the rest fail cleanly.

### 8.2 20-bot wallet double-spend (`test_concurrency_wallet.py`)
**Proves:** `SELECT FOR UPDATE` on the user row prevents over-spending — ₹500 wallet + 20 parallel ₹200 bookings = exactly 2 successes, no negative balance, no orphan txns.

### 8.3 Rollback paths (`test_rollback.py`)
**Proves:** insufficient-balance / trigger-block / bad-slot failures leave wallet, bookings, and Wallet_Transactions byte-identical to pre-state.

### 8.4 DB-level constraints (`test_constraints.py`)
**Proves:** every CHECK / UNIQUE / trigger fires when violated (10 direct-DB assertions).

---

## 9. How to watch what's happening

- **Every SQL statement (backend + tests)**: `docker compose logs -f postgres`
- **Every HTTP request**: run `uvicorn` with `--log-level debug`
- **Browse data in pgAdmin**: http://localhost:5050 (admin@local.com / admin)
- **Interactive API**: http://localhost:8000/docs (Swagger UI — call any endpoint with a form)

---

## 10. Reset between test runs

```bash
python seed.py          # TRUNCATEs + re-seeds + rewrites credentials.txt
```

Every concurrency test calls this via its `fresh_db` fixture, so manual reset is only needed if you've been poking the DB by hand.
