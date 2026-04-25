# Campus Facility Booking System

A final-year DBMS project built with **PostgreSQL + FastAPI + raw SQL (no ORM) + Vanilla JS**.

Students, faculty, and organizations can log in, browse available time slots for campus facilities (seminar halls, labs, sports courts, guest rooms), pay from a wallet, and make bookings. The database enforces all correctness guarantees — ACID transactions, triggers, CHECK constraints, and partial UNIQUE indexes.

---

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Backend  | Python 3.10+, FastAPI, psycopg2     |
| Database | PostgreSQL 16                       |
| Frontend | Vanilla HTML/CSS/JS (single page)   |

---

## Prerequisites

Install these before starting:

- **Python 3.10+** — [python.org/downloads](https://www.python.org/downloads/)
- **PostgreSQL 16** — [postgresql.org/download](https://www.postgresql.org/download/)

> **Mac (Homebrew):**
> ```bash
> brew install postgresql@16 python@3.12
> brew services start postgresql@16
> echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zprofile
> source ~/.zprofile
> ```

> **Windows:** Install PostgreSQL from the official site. During install, set a password for the `postgres` user and remember it.

> **Linux (Ubuntu/Debian):**
> ```bash
> sudo apt install postgresql python3 python3-pip python3-venv
> sudo systemctl start postgresql
> sudo -u postgres createuser --superuser $USER
> ```

---

## Setup (step by step)

### 1. Clone the repo

```bash
git clone https://github.com/be-water22/facility-booking.git
cd facility-booking
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv venv

# Mac/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Create the PostgreSQL database and apply the schema

```bash
createdb campus_booking
psql campus_booking < schema.sql
```

You should see a list of `CREATE TABLE`, `CREATE TRIGGER`, `CREATE INDEX` messages — that means the schema was applied successfully.

> **If `createdb` says "role does not exist"** (common on Mac with Homebrew):
> ```bash
> psql postgres -c "CREATE ROLE postgres WITH SUPERUSER LOGIN PASSWORD 'postgres';"
> ```
> Then re-run the `createdb` and `psql` commands above.

> **Windows:** Open pgAdmin or run `psql -U postgres` and use the password you set during install. Then:
> ```sql
> CREATE DATABASE campus_booking;
> \q
> ```
> Then: `psql -U postgres campus_booking < schema.sql`

### 4. Configure database connection (if needed)

By default the app connects as:

| Setting  | Default value    |
|----------|------------------|
| Host     | `localhost`      |
| Port     | `5432`           |
| Database | `campus_booking` |
| User     | `postgres`       |
| Password | `postgres`       |

If your PostgreSQL uses a different user or password, set environment variables before running:

```bash
export DB_USER=your_user
export DB_PASSWORD=your_password
```

### 5. Seed the database

```bash
python seed.py
```

This creates:
- 50 users (30 students, 8 faculty, 2 admins, 10 organizations)
- 15 facilities across all types
- Time slots for each facility
- A few sample bookings

It also writes a `credentials.txt` file in the project folder with every user's email and password.

### 6. Start the server

```bash
uvicorn main:app --reload
```

Open **http://localhost:8000** in your browser — the UI will load.

Swagger API docs are at **http://localhost:8000/docs**

---

## Logging in

After seeding, open `credentials.txt` to find login credentials. Some quick examples:

| Role         | Email                         | Password     |
|--------------|-------------------------------|--------------|
| Admin        | `admin1@iitk.ac.in`           | see file     |
| Admin        | `admin2@iitk.ac.in`           | see file     |
| Student      | any `@iitk.ac.in` entry       | see file     |
| Organization | `antaragni@orgs.iitk.ac.in`   | see file     |

Password format is always: **4 lowercase letters + 4 digits** (e.g. `abcd1234`)

---

## Project Structure

```
facility-booking/
├── schema.sql          # 9 tables, 2 triggers, 5 indexes — the entire DB schema
├── seed.py             # Fills the DB with realistic sample data
├── main.py             # FastAPI backend — all API endpoints
├── static/
│   └── index.html      # Frontend — single page app (no framework)
├── tests/              # Automated pytest test suite
│   ├── conftest.py
│   ├── bots.py
│   ├── test_concurrency_booking.py
│   ├── test_concurrency_wallet.py
│   ├── test_constraints.py
│   └── test_rollback.py
├── TESTING.md          # Step-by-step manual testing guide
└── requirements.txt
```

---

## Running Tests

Make sure the server is running (`uvicorn main:app --reload`) in one terminal, then in another:

```bash
pytest -v tests/
```

Tests cover:
- Concurrent slot booking (only 1 winner allowed)
- Concurrent wallet operations
- DB constraint checks (wallet balance, password format, etc.)
- Transaction rollback on failure

---

## Resetting the Database

To wipe all data and start fresh:

```bash
dropdb campus_booking
createdb campus_booking
psql campus_booking < schema.sql
python seed.py
```

---

## Common Errors

| Error | Fix |
|-------|-----|
| `role "postgres" does not exist` | Run: `psql postgres -c "CREATE ROLE postgres WITH SUPERUSER LOGIN PASSWORD 'postgres';"` |
| `connection refused on port 5432` | PostgreSQL is not running. Run: `brew services start postgresql@16` (Mac) or `sudo systemctl start postgresql` (Linux) |
| `credentials.txt not found` when running tests | Run `python seed.py` first |
| `API not reachable` in tests | Start the server: `uvicorn main:app --reload` |
| `ModuleNotFoundError` | Make sure your virtual environment is activated: `source venv/bin/activate` |
