import sqlite3
import os

db_path = "data/reservation.db"
if not os.path.exists(db_path):
    print("DB file not found")
else:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print("--- Machines ---")
    for row in conn.execute("SELECT * FROM machine_states").fetchall():
        print(dict(row))
        
    print("\n--- Reservations ---")
    for row in conn.execute("SELECT * FROM reservations").fetchall():
        print(dict(row))
        
    conn.close()
