import os

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(repo_root, 'database', 'watchtogether.sqlite')

import sqlite3

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("ALTER TABLE wt_rooms ADD COLUMN password VARCHAR(50);")
    cur.execute("ALTER TABLE wt_rooms ADD COLUMN is_public BOOLEAN DEFAULT 1;")
    conn.commit()
    conn.close()
    print("Columns password and is_public added to wt_rooms successfully.")
except sqlite3.OperationalError as e:
    print(f"Error adding columns (maybe they exist): {e}")

