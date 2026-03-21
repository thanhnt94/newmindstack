import os

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(repo_root, 'database', 'watchtogether.sqlite')

print(f"Patching DB at: {db_path}")

from watchtogether.database import init_db
import sqlite3

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("ALTER TABLE wt_users ADD COLUMN total_watch_minutes INTEGER DEFAULT 0;")
    conn.commit()
    conn.close()
    print("Column total_watch_minutes added successfully.")
except sqlite3.OperationalError as e:
    print(f"Error adding column: {e}")

print("Running auto metadata creation for wt_memberships...")
init_db()
print("Done patching.")
