"""
main.py — Campus Facility Booking System (FastAPI + raw psycopg2)

Endpoints:
  POST /api/login
  GET  /api/users
  GET  /api/users/{id}
  GET  /api/users/{id}/bookings
  GET  /api/users/{id}/transactions
  GET  /api/facilities
  GET  /api/facility-types
  GET  /api/facilities/{id}/availability?date=YYYY-MM-DD
  GET  /api/facilities/{id}/rooms
  POST /api/bookings
  POST /api/bookings/{id}/cancel
  POST /api/wallet/deposit
  GET  /api/admin/transactions
  GET  /api/admin/utilization
  PATCH /api/admin/facilities/{id}/operational
"""

from __future__ import annotations

import os
from typing import Generator
from datetime import date as _date
from decimal import Decimal

import psycopg2
from psycopg2 import errors
from psycopg2.extras import RealDictCursor

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

DB_CONFIG = {
    "dbname":   os.getenv("DB_NAME",     "campus_booking"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     os.getenv("DB_PORT",     "5432"),
}

app = FastAPI(title="Campus Facility Booking System")


def get_db() -> Generator:
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str

class BookingCreate(BaseModel):
    user_id: int
    facility_id: int
    booking_date: _date
    slot_ids: list[int] = Field(..., min_length=1)
    room_id: int | None = None

class DepositRequest(BaseModel):
    user_id: int
    amount: Decimal = Field(..., gt=0)

class OperationalToggle(BaseModel):
    admin_id: int
    is_operational: bool


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/api/login", tags=["auth"])
def login(payload: LoginRequest, conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT u.user_id, u.name, u.email, u.base_type, u.wallet_balance, u.created_at,
                   s.roll_number, o.org_type
              FROM Users u
         LEFT JOIN Students s      ON s.user_id = u.user_id
         LEFT JOIN Organizations o ON o.user_id = u.user_id
             WHERE LOWER(u.email) = LOWER(%s) AND u.password = %s;
        """, (payload.email.strip(), payload.password))
        row = cur.fetchone()
        if not row:
            raise HTTPException(401, "Invalid email or password.")
        return row


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@app.get("/api/users", tags=["users"])
def list_users(conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT user_id, name, email, base_type, wallet_balance
              FROM Users
          ORDER BY base_type, name;
        """)
        return cur.fetchall()


@app.get("/api/users/{user_id}", tags=["users"])
def get_user(user_id: int, conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT u.user_id, u.name, u.email, u.base_type, u.wallet_balance, u.created_at,
                   s.roll_number, o.org_type
              FROM Users u
         LEFT JOIN Students s      ON s.user_id = u.user_id
         LEFT JOIN Organizations o ON o.user_id = u.user_id
             WHERE u.user_id = %s;
        """, (user_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "User not found.")
        return row


@app.get("/api/users/{user_id}/bookings", tags=["users"])
def get_user_bookings(user_id: int, conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT b.booking_id, b.booking_date, b.total_cost, b.status, b.created_at,
                   f.facility_id, f.name AS facility_name, f.type AS facility_type,
                   ARRAY_AGG(
                     JSON_BUILD_OBJECT(
                       'slot_id',       fs.slot_id,
                       'start_time',    TO_CHAR(fs.start_time, 'HH24:MI'),
                       'end_time',      TO_CHAR(fs.end_time,   'HH24:MI'),
                       'price_charged', bs.price_charged,
                       'room_number',   fr.room_number,
                       'hall_number',   fr.hall_number
                     ) ORDER BY fs.start_time
                   ) AS slots
              FROM Bookings b
              JOIN Booking_Slots bs  ON bs.booking_id  = b.booking_id
              JOIN Facility_Slots fs ON fs.slot_id     = bs.slot_id
              JOIN Facilities f      ON f.facility_id  = fs.facility_id
         LEFT JOIN Facility_Rooms fr ON fr.room_id     = bs.room_id
             WHERE b.user_id = %s
          GROUP BY b.booking_id, f.facility_id
          ORDER BY b.booking_date DESC, b.booking_id DESC;
        """, (user_id,))
        return cur.fetchall()


@app.get("/api/users/{user_id}/transactions", tags=["users"])
def get_user_transactions(user_id: int, conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT transaction_id, amount, transaction_type, description, created_at
              FROM Wallet_Transactions
             WHERE user_id = %s
          ORDER BY created_at DESC;
        """, (user_id,))
        return cur.fetchall()


# ---------------------------------------------------------------------------
# Facilities
# ---------------------------------------------------------------------------

@app.get("/api/facility-types", tags=["facilities"])
def facility_types(conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT type FROM Facilities ORDER BY type;")
        return [r[0] for r in cur.fetchall()]


@app.get("/api/facilities", tags=["facilities"])
def list_facilities(type: str | None = Query(None), conn=Depends(get_db)):
    sql = "SELECT facility_id, name, type, capacity FROM Facilities WHERE is_operational = TRUE"
    params = []
    if type:
        sql += " AND type = %s"
        params.append(type)
    sql += " ORDER BY type, name;"
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


@app.get("/api/facilities/{facility_id}/rooms", tags=["facilities"])
def facility_rooms(facility_id: int, conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT room_id, hall_number, room_number
              FROM Facility_Rooms
             WHERE facility_id = %s AND is_operational = TRUE
          ORDER BY hall_number NULLS FIRST, room_number;
        """, (facility_id,))
        return cur.fetchall()


@app.get("/api/facilities/{facility_id}/availability", tags=["facilities"])
def facility_availability(
    facility_id: int,
    date: _date = Query(...),
    room_id: int | None = Query(None),
    conn=Depends(get_db),
):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT fs.slot_id,
                   TO_CHAR(fs.start_time, 'HH24:MI') AS start_time,
                   TO_CHAR(fs.end_time,   'HH24:MI') AS end_time,
                   fs.price
              FROM Facility_Slots fs
             WHERE fs.facility_id = %s
               AND fs.slot_id NOT IN (
                     SELECT bs.slot_id
                       FROM Booking_Slots bs
                       JOIN Bookings b ON b.booking_id = bs.booking_id
                      WHERE b.booking_date = %s
                        AND b.status IN ('Pending', 'Confirmed')
                        AND COALESCE(bs.room_id, -1) = COALESCE(%s, -1)
                   )
          ORDER BY fs.start_time;
        """, (facility_id, date, room_id))
        return cur.fetchall()


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

@app.post("/api/bookings", tags=["bookings"], status_code=201)
def create_booking(payload: BookingCreate, conn=Depends(get_db)):
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Acquire per-(slot, date) advisory locks before any inserts so that
            # concurrent requests for the same slot queue up instead of racing.
            # Sorting slot IDs prevents deadlock when multiple slots are booked.
            date_int = (payload.booking_date - _date(1970, 1, 1)).days
            for sid in sorted(payload.slot_ids):
                cur.execute("SELECT pg_advisory_xact_lock(%s, %s);", (sid, date_int))

            cur.execute(
                "SELECT user_id, wallet_balance FROM Users WHERE user_id = %s FOR UPDATE;",
                (payload.user_id,),
            )
            user = cur.fetchone()
            if not user:
                raise HTTPException(404, "User not found.")

            cur.execute("""
                SELECT slot_id, price FROM Facility_Slots
                 WHERE facility_id = %s AND slot_id = ANY(%s);
            """, (payload.facility_id, payload.slot_ids))
            slots = cur.fetchall()
            if len(slots) != len(payload.slot_ids):
                raise HTTPException(400, "Some slot IDs are invalid for this facility.")

            total = sum(Decimal(s["price"]) for s in slots)
            if Decimal(user["wallet_balance"]) < total:
                raise HTTPException(400, f"Not enough wallet balance. Need ₹{total}.")

            cur.execute("""
                INSERT INTO Bookings (user_id, booking_date, total_cost, status)
                VALUES (%s, %s, %s, 'Confirmed') RETURNING booking_id;
            """, (payload.user_id, payload.booking_date, total))
            booking_id = cur.fetchone()["booking_id"]

            for s in slots:
                cur.execute("""
                    INSERT INTO Booking_Slots (booking_id, slot_id, room_id, price_charged)
                    VALUES (%s, %s, %s, %s);
                """, (booking_id, s["slot_id"], payload.room_id, s["price"]))

            if total > 0:
                cur.execute(
                    "UPDATE Users SET wallet_balance = wallet_balance - %s WHERE user_id = %s;",
                    (total, payload.user_id),
                )
                cur.execute("""
                    INSERT INTO Wallet_Transactions (user_id, amount, transaction_type, description)
                    VALUES (%s, %s, 'Payment', %s);
                """, (payload.user_id, total, f"Booking #{booking_id}"))

        conn.commit()
        return {"booking_id": booking_id, "total_cost": str(total), "status": "Confirmed"}

    except HTTPException:
        conn.rollback()
        raise
    except errors.RaiseException as exc:
        conn.rollback()
        raise HTTPException(400, str(exc).splitlines()[0])
    except psycopg2.Error as exc:
        conn.rollback()
        raise HTTPException(400, f"Database error: {exc.pgerror or str(exc)}")


@app.post("/api/bookings/{booking_id}/cancel", tags=["bookings"])
def cancel_booking(booking_id: int, user_id: int = Query(...), conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT booking_id, user_id, total_cost, status FROM Bookings WHERE booking_id = %s FOR UPDATE;",
            (booking_id,),
        )
        b = cur.fetchone()
        if not b:
            raise HTTPException(404, "Booking not found.")
        if b["user_id"] != user_id:
            raise HTTPException(403, "You can only cancel your own bookings.")
        if b["status"] == "Cancelled":
            raise HTTPException(400, "Booking is already cancelled.")

        cur.execute("UPDATE Bookings SET status = 'Cancelled' WHERE booking_id = %s;", (booking_id,))

        refund = Decimal(b["total_cost"])
        if refund > 0:
            cur.execute(
                "UPDATE Users SET wallet_balance = wallet_balance + %s WHERE user_id = %s;",
                (refund, user_id),
            )
            cur.execute("""
                INSERT INTO Wallet_Transactions (user_id, amount, transaction_type, description)
                VALUES (%s, %s, 'Refund', %s);
            """, (user_id, refund, f"Refund for Booking #{booking_id}"))

    conn.commit()
    return {"booking_id": booking_id, "status": "Cancelled", "refund": str(refund)}


# ---------------------------------------------------------------------------
# Wallet
# ---------------------------------------------------------------------------

@app.post("/api/wallet/deposit", tags=["wallet"])
def wallet_deposit(payload: DepositRequest, conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT user_id FROM Users WHERE user_id = %s;", (payload.user_id,))
        if not cur.fetchone():
            raise HTTPException(404, "User not found.")

        cur.execute(
            "UPDATE Users SET wallet_balance = wallet_balance + %s WHERE user_id = %s;",
            (payload.amount, payload.user_id),
        )
        cur.execute("""
            INSERT INTO Wallet_Transactions (user_id, amount, transaction_type, description)
            VALUES (%s, %s, 'Deposit', %s);
        """, (payload.user_id, payload.amount, f"Wallet top-up ₹{payload.amount}"))
    conn.commit()
    return {"user_id": payload.user_id, "deposited": str(payload.amount)}


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@app.get("/api/admin/transactions", tags=["admin"])
def admin_all_transactions(admin_id: int = Query(...), conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT base_type FROM Users WHERE user_id = %s;", (admin_id,))
        row = cur.fetchone()
        if not row or row["base_type"] != "Admin":
            raise HTTPException(403, "Admin access required.")

        cur.execute("""
            SELECT t.transaction_id, t.user_id, u.name AS user_name, u.base_type,
                   t.amount, t.transaction_type, t.description, t.created_at
              FROM Wallet_Transactions t
              JOIN Users u ON u.user_id = t.user_id
          ORDER BY t.created_at DESC;
        """)
        return cur.fetchall()


@app.get("/api/admin/utilization", tags=["admin"])
def admin_utilization(
    admin_id: int = Query(...),
    date_from: _date | None = Query(None),
    date_to: _date | None = Query(None),
    conn=Depends(get_db),
):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT base_type FROM Users WHERE user_id = %s;", (admin_id,))
        row = cur.fetchone()
        if not row or row["base_type"] != "Admin":
            raise HTTPException(403, "Admin access required.")

        cur.execute("""
            WITH active AS (
                SELECT b.booking_id, b.booking_date, bs.price_charged, fs.facility_id
                  FROM Bookings b
                  JOIN Booking_Slots  bs ON bs.booking_id = b.booking_id
                  JOIN Facility_Slots fs ON fs.slot_id    = bs.slot_id
                 WHERE b.status IN ('Pending', 'Confirmed')
                   AND (%s::date IS NULL OR b.booking_date >= %s::date)
                   AND (%s::date IS NULL OR b.booking_date <= %s::date)
            )
            SELECT f.facility_id, f.name, f.type, f.capacity, f.is_operational,
                   COUNT(DISTINCT a.booking_id)      AS bookings,
                   COUNT(a.booking_id)               AS slots_booked,
                   COALESCE(SUM(a.price_charged), 0) AS revenue
              FROM Facilities f
         LEFT JOIN active a ON a.facility_id = f.facility_id
          GROUP BY f.facility_id
          ORDER BY revenue DESC, f.name;
        """, (date_from, date_from, date_to, date_to))
        return cur.fetchall()


@app.patch("/api/admin/facilities/{facility_id}/operational", tags=["admin"])
def toggle_operational(facility_id: int, payload: OperationalToggle, conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT base_type FROM Users WHERE user_id = %s;", (payload.admin_id,))
        row = cur.fetchone()
        if not row or row["base_type"] != "Admin":
            raise HTTPException(403, "Admin access required.")

        cur.execute("""
            UPDATE Facilities SET is_operational = %s
             WHERE facility_id = %s
         RETURNING facility_id, name, is_operational;
        """, (payload.is_operational, facility_id))
        result = cur.fetchone()
        if not result:
            raise HTTPException(404, "Facility not found.")
    conn.commit()
    return result


# ---------------------------------------------------------------------------
# Serve frontend
# ---------------------------------------------------------------------------

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
