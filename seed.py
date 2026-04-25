"""
seed.py — Campus Facility Booking System database seeder.

Populates a freshly-migrated PostgreSQL schema with realistic data:
  * ~50 Users (mix of Students, Faculty, Admins, Organizations)
  * 15 Facilities across all defined types
  * Hall guest rooms (halls 1..14, 2 rooms each) + a Visitor Hostel room set
  * One week's worth of Facility_Slots
  * Initial wallet deposits for ~70 % of users
  * A handful of sample Bookings to prove the pipeline works

Run:
    python seed.py
"""

from __future__ import annotations

import os
import random
import string
from datetime import date, time, timedelta
from decimal import Decimal

import psycopg2
from psycopg2.extras import execute_values
from faker import Faker

# ---------------------------------------------------------------------------
# Connection settings — override via env vars in real deployments
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "dbname":   os.getenv("DB_NAME", "campus_booking"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     os.getenv("DB_PORT", "5432"),
}

fake = Faker("en_IN")
Faker.seed(42)
random.seed(42)


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
NUM_STUDENTS   = 30
NUM_FACULTY    = 8
NUM_ADMINS     = 2
NUM_ORGS       = 10        # 50 users total
DAYS_AHEAD     = 7         # one week of slots
ORG_TYPES      = ("Club", "Festival_Committee", "Society")

# (name, type, capacity)
FACILITY_DEFS = [
    ("Main Seminar Hall",        "Seminar_Hall",   200),
    ("North Block Seminar Hall", "Seminar_Hall",   120),
    ("Computer Science Lab 1",   "Lab",             40),
    ("Computer Science Lab 2",   "Lab",             40),
    ("Electronics Lab",          "Lab",             35),
    ("SAC Basketball Court",     "SAC_Court",       30),
    ("SAC Badminton Court",      "SAC_Court",       12),
    ("SAC Tennis Court",         "SAC_Court",       10),
    ("Open Air Theatre",         "OAT",           1500),
    ("Pronite Main Ground",      "Pronite_Ground",5000),
    # Hall guest rooms — one Facility row per hall, rooms modelled in Facility_Rooms
    ("Hall 1 Guest Rooms",       "Hall_Guest_Room", 4),
    ("Hall 2 Guest Rooms",       "Hall_Guest_Room", 4),
    ("Hall 3 Guest Rooms",       "Hall_Guest_Room", 4),
    ("Hall 4 Guest Rooms",       "Hall_Guest_Room", 4),
    # Visitor hostel — one Facility row, several numbered rooms
    ("Visitor Hostel",           "Visitor_Hostel_Room", 20),
]

# Recurring daily slot template (start, end, price ₹)
DAILY_SLOT_TEMPLATE = [
    (time(6, 0),  time(8, 0),   Decimal("0.00")),    # early morning – free
    (time(8, 0),  time(10, 0),  Decimal("100.00")),
    (time(10, 0), time(12, 0),  Decimal("200.00")),
    (time(12, 0), time(14, 0),  Decimal("150.00")),
    (time(14, 0), time(16, 0),  Decimal("200.00")),
    (time(16, 0), time(18, 0),  Decimal("300.00")),
    (time(18, 0), time(20, 0),  Decimal("500.00")),  # peak evening
    (time(20, 0), time(22, 0),  Decimal("400.00")),
]


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------
def truncate_all(cur) -> None:
    """Wipe data so the seeder is idempotent. RESTART IDENTITY resets serial PKs."""
    cur.execute("""
        TRUNCATE
            Booking_Slots,
            Bookings,
            Wallet_Transactions,
            Facility_Slots,
            Facility_Rooms,
            Facilities,
            Students,
            Organizations,
            Users
        RESTART IDENTITY CASCADE;
    """)


def gen_password(seed_val: int) -> str:
    """Reproducible per-user password: 4 lowercase letters + 4 digits."""
    rng = random.Random(seed_val * 1000 + 7)
    letters = "".join(rng.choice(string.ascii_lowercase) for _ in range(4))
    digits  = "".join(rng.choice(string.digits)           for _ in range(4))
    return letters + digits


def seed_users(cur) -> dict[str, list[int]]:
    """Insert users + the Students/Organizations subtype rows.
       Password column is set per-user to a unique 4-letter+4-digit token
       derived from the user's user_id (reproducible across re-seeds).
    """
    user_ids: dict[str, list[int]] = {"Student": [], "Faculty": [], "Admin": [], "Organization": []}
    credentials: list[tuple[int, str, str, str]] = []  # (uid, role, email, pwd)

    def insert_user(name: str, email: str, base_type: str, balance: Decimal) -> int:
        # Insert first (password falls back to the schema default), then rewrite
        # the password using the freshly-assigned user_id as the seed.
        cur.execute(
            """INSERT INTO Users (name, email, base_type, wallet_balance)
               VALUES (%s, %s, %s, %s) RETURNING user_id;""",
            (name, email, base_type, balance),
        )
        uid = cur.fetchone()[0]
        pwd = gen_password(uid)
        cur.execute("UPDATE Users SET password = %s WHERE user_id = %s;", (pwd, uid))
        credentials.append((uid, base_type, email, pwd))
        return uid

    # 70 % chance of having a starting balance
    def starting_balance() -> Decimal:
        return Decimal(random.randint(500, 5000)) if random.random() < 0.7 else Decimal("0")

    # Students
    used_rolls: set[str] = set()
    for _ in range(NUM_STUDENTS):
        name  = fake.name()
        email = f"{name.lower().replace(' ', '.')}{random.randint(10, 99)}@iitk.ac.in"
        uid   = insert_user(name, email, "Student", starting_balance())
        user_ids["Student"].append(uid)
        # unique roll number
        while True:
            roll = f"{random.randint(20, 24)}{random.choice(['BT','MT','PHD'])}{random.randint(1000, 9999)}"
            if roll not in used_rolls:
                used_rolls.add(roll)
                break
        cur.execute("INSERT INTO Students (user_id, roll_number) VALUES (%s, %s);", (uid, roll))

    # Faculty
    for _ in range(NUM_FACULTY):
        name  = "Dr. " + fake.name()
        email = f"{name.lower().replace('dr. ', '').replace(' ', '.')}@faculty.iitk.ac.in"
        uid   = insert_user(name, email, "Faculty", starting_balance())
        user_ids["Faculty"].append(uid)

    # Admins (always topped up — they may need to refund users)
    for i in range(NUM_ADMINS):
        uid = insert_user(f"Admin {i+1}", f"admin{i+1}@iitk.ac.in", "Admin", Decimal("10000"))
        user_ids["Admin"].append(uid)

    # Organizations
    org_names = [
        "Antaragni", "Techkriti", "Udghosh", "Robotics Club", "Programming Club",
        "Astronomy Club", "Music Club", "Dance Club", "Drama Club", "Photography Society",
    ]
    for i in range(NUM_ORGS):
        name  = org_names[i] if i < len(org_names) else f"Org {i+1}"
        email = f"{name.lower().replace(' ', '_')}@orgs.iitk.ac.in"
        uid   = insert_user(name, email, "Organization", starting_balance() + Decimal("2000"))
        user_ids["Organization"].append(uid)
        org_type = random.choice(ORG_TYPES)
        cur.execute(
            "INSERT INTO Organizations (user_id, org_type) VALUES (%s, %s);",
            (uid, org_type),
        )

    # Mirror initial deposits in the audit ledger
    cur.execute("SELECT user_id, wallet_balance FROM Users WHERE wallet_balance > 0;")
    deposits = [
        (uid, bal, "Deposit", "Opening balance (seeded)") for uid, bal in cur.fetchall()
    ]
    if deposits:
        execute_values(
            cur,
            """INSERT INTO Wallet_Transactions
               (user_id, amount, transaction_type, description) VALUES %s;""",
            deposits,
        )

    # Dump the login credentials for convenience so users of the demo can sign in.
    with open("credentials.txt", "w") as f:
        f.write(f"{'user_id':<8}{'role':<14}{'email':<42}password\n")
        f.write("-" * 80 + "\n")
        for uid, role, email, pwd in sorted(credentials):
            f.write(f"{uid:<8}{role:<14}{email:<42}{pwd}\n")

    return user_ids


def seed_facilities(cur) -> list[int]:
    """Insert facilities and return their ids in definition order."""
    facility_ids: list[int] = []
    for name, ftype, capacity in FACILITY_DEFS:
        cur.execute(
            """INSERT INTO Facilities (name, type, capacity)
               VALUES (%s, %s, %s) RETURNING facility_id;""",
            (name, ftype, capacity),
        )
        facility_ids.append(cur.fetchone()[0])
    return facility_ids


def seed_rooms(cur) -> None:
    """For Hall_Guest_Room rows, add 2 numbered rooms each with the right hall_number.
       For the Visitor_Hostel_Room facility, add 20 numbered rooms (VH-101..VH-120)."""
    # Hall guest rooms
    cur.execute("""SELECT facility_id, name
                     FROM Facilities
                    WHERE type = 'Hall_Guest_Room'
                 ORDER BY facility_id;""")
    hall_rows = cur.fetchall()
    room_payload: list[tuple] = []
    for facility_id, name in hall_rows:
        # Extract hall number from "Hall N Guest Rooms"
        try:
            hall_no = int(name.split()[1])
        except (IndexError, ValueError):
            hall_no = None
        for room_no in (1, 2):
            room_payload.append((facility_id, hall_no, str(room_no)))

    # Visitor hostel rooms — VH-101 .. VH-120
    cur.execute("SELECT facility_id FROM Facilities WHERE type = 'Visitor_Hostel_Room';")
    vh_rows = cur.fetchall()
    for (vh_id,) in vh_rows:
        for n in range(1, 21):
            room_payload.append((vh_id, None, f"VH-{100 + n}"))

    if room_payload:
        execute_values(
            cur,
            """INSERT INTO Facility_Rooms (facility_id, hall_number, room_number)
               VALUES %s;""",
            room_payload,
        )


def seed_slots(cur, facility_ids: list[int]) -> None:
    """Attach the daily template to every facility (slots are recurring)."""
    payload = [
        (fid, start, end, price)
        for fid in facility_ids
        for (start, end, price) in DAILY_SLOT_TEMPLATE
    ]
    execute_values(
        cur,
        """INSERT INTO Facility_Slots (facility_id, start_time, end_time, price)
           VALUES %s;""",
        payload,
    )


def seed_sample_bookings(cur, user_ids: dict[str, list[int]]) -> None:
    """Place a few bookings to verify the trigger pipeline. Bookings are placed
       on dates within DAYS_AHEAD, using slots from non-restricted facilities."""
    # Pick slots on safe (non-OAT/Pronite) facilities
    cur.execute("""
        SELECT fs.slot_id, fs.price, f.facility_id
          FROM Facility_Slots fs
          JOIN Facilities f ON f.facility_id = fs.facility_id
         WHERE f.type NOT IN ('OAT', 'Pronite_Ground')
         ORDER BY random()
         LIMIT 20;
    """)
    candidate_slots = cur.fetchall()
    if not candidate_slots:
        return

    student_pool = user_ids["Student"]
    if not student_pool:
        return

    for slot_id, price, _facility_id in candidate_slots[:8]:
        uid          = random.choice(student_pool)
        booking_date = date.today() + timedelta(days=random.randint(1, DAYS_AHEAD))

        cur.execute(
            """INSERT INTO Bookings (user_id, booking_date, total_cost, status)
               VALUES (%s, %s, %s, 'Confirmed') RETURNING booking_id;""",
            (uid, booking_date, price),
        )
        booking_id = cur.fetchone()[0]

        try:
            cur.execute(
                """INSERT INTO Booking_Slots (booking_id, slot_id, price_charged)
                   VALUES (%s, %s, %s);""",
                (booking_id, slot_id, price),
            )
        except psycopg2.errors.RaiseException:
            # Trigger blocked it (e.g. somehow restricted) — roll back this cart
            cur.connection.rollback()


def main() -> None:
    print("Connecting to PostgreSQL ...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            print("Truncating existing data ...")
            truncate_all(cur)

            print("Seeding users ...")
            user_ids = seed_users(cur)

            print("Seeding facilities ...")
            facility_ids = seed_facilities(cur)

            print("Seeding rooms (hall guest rooms + visitor hostel) ...")
            seed_rooms(cur)

            print("Seeding facility slots (recurring daily timetable) ...")
            seed_slots(cur, facility_ids)

            print("Placing a few sample bookings ...")
            seed_sample_bookings(cur, user_ids)

        conn.commit()
        print("Seed complete.")

        # Quick summary
        with conn.cursor() as cur:
            cur.execute("SELECT base_type, COUNT(*) FROM Users GROUP BY base_type ORDER BY 1;")
            print("\nUsers:")
            for row in cur.fetchall():
                print(f"   {row[0]:<14}: {row[1]}")
            cur.execute("SELECT COUNT(*) FROM Facilities;")
            print(f"Facilities    : {cur.fetchone()[0]}")
            cur.execute("SELECT COUNT(*) FROM Facility_Rooms;")
            print(f"Rooms         : {cur.fetchone()[0]}")
            cur.execute("SELECT COUNT(*) FROM Facility_Slots;")
            print(f"Slots         : {cur.fetchone()[0]}")
            cur.execute("SELECT COUNT(*) FROM Bookings;")
            print(f"Bookings      : {cur.fetchone()[0]}")

    except Exception as exc:
        conn.rollback()
        print(f"Seed failed, rolled back: {exc}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
