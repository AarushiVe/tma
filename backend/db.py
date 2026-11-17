import sqlite3
from flask import g
from werkzeug.security import generate_password_hash
import config

TABLES = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    phone TEXT,
    role TEXT NOT NULL,              -- admin / staff / trekker
    status TEXT NOT NULL DEFAULT 'active',   -- active / deactivated / blacklisted
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS staff_profiles (
    user_id INTEGER PRIMARY KEY,
    experience_years INTEGER DEFAULT 0,
    specialization TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS treks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    difficulty TEXT NOT NULL,        -- Easy / Moderate / Hard
    duration_days INTEGER NOT NULL,
    total_slots INTEGER NOT NULL,
    available_slots INTEGER NOT NULL,
    price REAL DEFAULT 0,
    description TEXT,
    instructions TEXT,
    staff_id INTEGER,
    status TEXT NOT NULL DEFAULT 'Pending',  -- Pending / Approved / Open / Closed / Completed
    is_started INTEGER DEFAULT 0,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    FOREIGN KEY (staff_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    trek_id INTEGER NOT NULL,
    people INTEGER NOT NULL,         -- how many people in this booking (1 to 10)
    status TEXT NOT NULL DEFAULT 'Booked',   -- Booked / Cancelled / Completed
    payment_status TEXT NOT NULL DEFAULT 'Pending',  -- Pending / Paid
    booking_date TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (trek_id) REFERENCES treks(id)
);

CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    phone TEXT,
    FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS exports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending',  -- Pending / Done / Failed
    filename TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


def connect():
    conn = sqlite3.connect(config.DATABASE, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    # one connection per request
    if "db" not in g:
        g.db = connect()
    return g.db


def close_db(error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def query(sql, args=()):
    """returns a list of dicts"""
    rows = get_db().execute(sql, args).fetchall()
    return [dict(r) for r in rows]


def query_one(sql, args=()):
    rows = query(sql, args)
    return rows[0] if rows else None


def execute(sql, args=()):
    """runs insert/update/delete and saves it. returns the new row id"""
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def create_tables_and_admin():
    conn = connect()
    conn.executescript(TABLES)
    admin = conn.execute("SELECT id FROM users WHERE role='admin'").fetchone()
    if admin is None:
        conn.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'admin')",
            ("Admin", config.ADMIN_EMAIL, generate_password_hash(config.ADMIN_PASSWORD)),
        )
        conn.commit()
        print("Admin created:", config.ADMIN_EMAIL)
    conn.close()
