import sqlite3
import os
from datetime import UTC, datetime

def parse_time(value):
    if not value: return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

db_path = "data/reservation.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

for row in conn.execute("SELECT * FROM machine_states").fetchall():
    if row["machine_name"] == "1번 세탁기":
        ends_at = parse_time(row["ends_at"])
        remaining_seconds = 0
        if ends_at:
            remaining_seconds = max(0, int((ends_at - datetime.now(UTC)).total_seconds()))
        in_use = bool(row["in_use"]) and remaining_seconds > 0
        print(f"Name: {row['machine_name']}, in_use: {in_use}, remaining: {remaining_seconds}, ends_at: {ends_at}, now: {datetime.now(UTC)}")
conn.close()
