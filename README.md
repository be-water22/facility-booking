# Campus Facility Booking System

A final-year DBMS project for booking campus facilities like seminar halls, labs, sports courts, guest rooms, and more.

**Stack:** Python + FastAPI + PostgreSQL + psycopg2 (raw SQL, no ORM) + Vanilla JS

---

## Prerequisites

- Python 3.10+
- PostgreSQL installed and running locally

---

## Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd facility-booking
```

### 2. Create the database and apply schema

```bash
createdb campus_booking
psql campus_booking < schema.sql
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Seed the database

```bash
python seed.py
```

This populates the DB with 50 users, 15 facilities, time slots, and some sample bookings.
It also creates a `credentials.txt` file with login details for all seeded users.

### 5. Run the server

```bash
uvicorn main:app --reload
```

Open **http://localhost:8000** in your browser.

API docs available at **http://localhost:8000/docs**

---

## Project Structure

```
facility-booking/
├── schema.sql          # All tables, triggers, constraints, indexes
├── seed.py             # Populates DB with sample data
├── main.py             # FastAPI backend
├── static/
│   └── index.html      # Frontend (single page app)
├── tests/              # Pytest test suite
├── TESTING.md          # Manual testing guide
└── requirements.txt
```

---

## Sample Logins

After running `seed.py`, check `credentials.txt` for the full list. Quick examples:

| Role         | Email                     | Password   |
|--------------|---------------------------|------------|
| Admin        | admin1@iitk.ac.in         | (see file) |
| Student      | (see credentials.txt)     | (see file) |
| Organization | antaragni@orgs.iitk.ac.in | (see file) |

---

## Running Tests

```bash
pytest -v tests/
```

Make sure the backend is running before running the tests.

---

## Resetting the Database

To wipe and re-seed from scratch:

```bash
psql campus_booking < schema.sql
python seed.py
```

Or drop and recreate:

```bash
dropdb campus_booking
createdb campus_booking
psql campus_booking < schema.sql
python seed.py
```
