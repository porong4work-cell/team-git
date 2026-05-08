import sqlite3
from datetime import UTC, datetime

from config import DATA_DIR, DB_FILE


def now_text():
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_time(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def connect_db():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reservations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                machine_name TEXT NOT NULL,
                machine_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS machine_states (
                machine_name TEXT PRIMARY KEY,
                signal_value INTEGER NOT NULL DEFAULT 0,
                in_use INTEGER NOT NULL DEFAULT 0,
                started_at TEXT,
                ends_at TEXT,
                updated_at TEXT NOT NULL
            );
            """
        )
