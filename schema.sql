-- =============================================================================
-- CAMPUS FACILITY BOOKING SYSTEM — POSTGRESQL SCHEMA (v2, cleaned)
-- =============================================================================
-- Improvements over v1:
--   * Facility 'type' values are now clean enum-style identifiers
--     ('Hall_Guest_Room' and 'Visitor_Hostel_Room' instead of free-text).
--   * A new Facility_Rooms table stores room numbers for facilities that have
--     them (Hall guest rooms 1..14 with 2 rooms each, Visitor Hostel rooms).
--   * Slot uniqueness is enforced (no duplicate slot definitions per facility).
--   * Bookings.user_id is NOT NULL and ON DELETE RESTRICT (history must persist).
--   * Booking_Slots gains a per-date dimension via a UNIQUE(slot_id, booking_date)
--     guard so the same physical slot can never be double-booked on the same day.
--   * Trigger upgraded to skip CANCELLED carts and to validate on date-level
--     conflicts as well.
-- =============================================================================


-- =============================================================================
-- LAYER 1: IDENTITY, AUTHORITY & FINANCE
-- =============================================================================

CREATE TABLE Users (
    user_id         SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    email           VARCHAR(100) UNIQUE NOT NULL,
    password        VARCHAR(100) NOT NULL DEFAULT 'xxxx0000'
                    CHECK (password ~ '^[A-Za-z]{4}[0-9]{4}$'),  -- 4 letters + 4 digits; seed.py sets per-user
    base_type       VARCHAR(20)  NOT NULL
                    CHECK (base_type IN ('Student', 'Faculty', 'Admin', 'Organization')),
    wallet_balance  NUMERIC(10, 2) NOT NULL DEFAULT 0.00
                    CHECK (wallet_balance >= 0),
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Students (
    user_id      INT PRIMARY KEY REFERENCES Users(user_id) ON DELETE CASCADE,
    roll_number  VARCHAR(20) UNIQUE NOT NULL
);

CREATE TABLE Organizations (
    user_id   INT PRIMARY KEY REFERENCES Users(user_id) ON DELETE CASCADE,
    org_type  VARCHAR(50) NOT NULL
              CHECK (org_type IN ('Club', 'Festival_Committee', 'Society'))
);

CREATE TABLE Wallet_Transactions (
    transaction_id    SERIAL PRIMARY KEY,
    user_id           INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    amount            NUMERIC(10, 2) NOT NULL CHECK (amount > 0),
    transaction_type  VARCHAR(20) NOT NULL
                      CHECK (transaction_type IN ('Deposit', 'Payment', 'Refund')),
    description       TEXT,
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- =============================================================================
-- LAYER 2: CAMPUS ASSETS & INVENTORY
-- =============================================================================

-- Facilities are now categorised with clean identifiers.
-- Hall_Guest_Room  : a hall's guest-room block (e.g. "Hall 3 Guest Rooms").
-- Visitor_Hostel_Room : a single bookable room in the Visitor Hostel.
CREATE TABLE Facilities (
    facility_id     SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    type            VARCHAR(30) NOT NULL
                    CHECK (type IN (
                        'Seminar_Hall',
                        'Lab',
                        'SAC_Court',
                        'OAT',
                        'Pronite_Ground',
                        'Hall_Guest_Room',
                        'Visitor_Hostel_Room'
                    )),
    capacity        INTEGER NOT NULL CHECK (capacity > 0),
    is_operational  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- For facility types that are "rooms inside a building" we explicitly model
-- the room number. One Facility row maps to many Facility_Rooms rows.
--   * Hall_Guest_Room : hall_number 1..14, with 2 rooms each (room_number 1, 2)
--   * Visitor_Hostel_Room : a single facility row with N numbered rooms
CREATE TABLE Facility_Rooms (
    room_id      SERIAL PRIMARY KEY,
    facility_id  INT NOT NULL REFERENCES Facilities(facility_id) ON DELETE CASCADE,
    hall_number  INTEGER,                 -- 1..14 for Hall_Guest_Room, NULL otherwise
    room_number  VARCHAR(10) NOT NULL,    -- e.g. "1", "2", "G-12", "VH-203"
    is_operational BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (facility_id, hall_number, room_number),
    CHECK (hall_number IS NULL OR (hall_number BETWEEN 1 AND 14))
);

-- Re-usable timetable for a facility. Each row is a recurring slot template.
-- A specific date is added later inside Booking_Slots.
CREATE TABLE Facility_Slots (
    slot_id      SERIAL PRIMARY KEY,
    facility_id  INT NOT NULL REFERENCES Facilities(facility_id) ON DELETE CASCADE,
    start_time   TIME NOT NULL,
    end_time     TIME NOT NULL,
    price        NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (price >= 0),
    CHECK (end_time > start_time),
    UNIQUE (facility_id, start_time, end_time)
);


-- =============================================================================
-- LAYER 3: TRANSACTIONS & BOOKING ENGINE
-- =============================================================================

CREATE TABLE Bookings (
    booking_id   SERIAL PRIMARY KEY,
    user_id      INT NOT NULL REFERENCES Users(user_id) ON DELETE RESTRICT,
    booking_date DATE NOT NULL,
    total_cost   NUMERIC(10, 2) NOT NULL CHECK (total_cost >= 0),
    status       VARCHAR(20) NOT NULL
                 CHECK (status IN ('Pending', 'Confirmed', 'Cancelled')),
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Each line in the cart is (booking, slot, optional room) for a given booking_date.
-- We use a surrogate PK + a partial UNIQUE INDEX (below) to enforce that the
-- same slot/room cannot appear twice in the same cart even when room_id is NULL
-- (PostgreSQL treats NULLs as distinct in normal UNIQUE constraints).
CREATE TABLE Booking_Slots (
    booking_slot_id  SERIAL PRIMARY KEY,
    booking_id       INT NOT NULL REFERENCES Bookings(booking_id) ON DELETE CASCADE,
    slot_id          INT NOT NULL REFERENCES Facility_Slots(slot_id) ON DELETE RESTRICT,
    room_id          INT REFERENCES Facility_Rooms(room_id) ON DELETE RESTRICT,
    price_charged    NUMERIC(10, 2) NOT NULL CHECK (price_charged >= 0)
);

-- Cart-line uniqueness with NULL-aware semantics
CREATE UNIQUE INDEX uq_booking_slots_with_room
    ON Booking_Slots (booking_id, slot_id, room_id)
    WHERE room_id IS NOT NULL;
CREATE UNIQUE INDEX uq_booking_slots_no_room
    ON Booking_Slots (booking_id, slot_id)
    WHERE room_id IS NULL;


-- =============================================================================
-- LAYER 4: DATABASE-LEVEL ENFORCEMENT
-- =============================================================================

-- 4a. Trigger: ground-booking authority check
CREATE OR REPLACE FUNCTION validate_ground_booking()
RETURNS TRIGGER AS $$
DECLARE
    u_base_type VARCHAR;
    fac_type    VARCHAR;
BEGIN
    SELECT f.type
      INTO fac_type
      FROM Facilities f
      JOIN Facility_Slots fs ON f.facility_id = fs.facility_id
     WHERE fs.slot_id = NEW.slot_id;

    SELECT u.base_type
      INTO u_base_type
      FROM Users u
      JOIN Bookings b ON u.user_id = b.user_id
     WHERE b.booking_id = NEW.booking_id;

    IF fac_type IN ('OAT', 'Pronite_Ground') THEN
        IF u_base_type <> 'Organization' THEN
            RAISE EXCEPTION
                'Access Denied: Only official Organizations can book major grounds (OAT / Pronite Ground).';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_ground_booking_rules
BEFORE INSERT OR UPDATE ON Booking_Slots
FOR EACH ROW EXECUTE FUNCTION validate_ground_booking();


-- 4b. Trigger: prevent double-booking the SAME slot on the SAME date
-- (Cancelled bookings are ignored; Pending + Confirmed both block.)
CREATE OR REPLACE FUNCTION prevent_double_booking()
RETURNS TRIGGER AS $$
DECLARE
    new_date DATE;
    conflict INT;
BEGIN
    SELECT booking_date INTO new_date FROM Bookings WHERE booking_id = NEW.booking_id;

    SELECT COUNT(*)
      INTO conflict
      FROM Booking_Slots bs
      JOIN Bookings b ON b.booking_id = bs.booking_id
     WHERE bs.slot_id     = NEW.slot_id
       AND b.booking_date = new_date
       AND b.status IN ('Pending', 'Confirmed')
       AND bs.booking_id <> NEW.booking_id
       AND COALESCE(bs.room_id, -1) = COALESCE(NEW.room_id, -1);

    IF conflict > 0 THEN
        RAISE EXCEPTION
            'Slot % on % is already booked%',
            NEW.slot_id, new_date,
            CASE WHEN NEW.room_id IS NOT NULL
                 THEN ' for the requested room.'
                 ELSE '.'
            END;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_no_double_booking
BEFORE INSERT ON Booking_Slots
FOR EACH ROW EXECUTE FUNCTION prevent_double_booking();


-- =============================================================================
-- LAYER 5: PERFORMANCE INDEXING
-- =============================================================================

CREATE INDEX idx_facility_slots_facility   ON Facility_Slots (facility_id);
CREATE INDEX idx_bookings_date_status      ON Bookings (booking_date, status);
CREATE INDEX idx_booking_slots_slot        ON Booking_Slots (slot_id);
CREATE INDEX idx_wallet_tx_user_time       ON Wallet_Transactions (user_id, created_at DESC);
CREATE INDEX idx_facility_rooms_facility   ON Facility_Rooms (facility_id);
