import sqlite3
import os

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(repo_root, 'database', 'watchtogether.sqlite')

print(f"Patching DB at: {db_path}")
conn = sqlite3.connect(db_path)
cur = conn.cursor()
try:
    cur.execute("ALTER TABLE wt_rooms ADD COLUMN allow_guest_control BOOLEAN DEFAULT 0;")
    print("Column added successfully.")
except sqlite3.OperationalError as e:
    print(f"Error (maybe column exists): {e}")
conn.commit()
conn.close()
