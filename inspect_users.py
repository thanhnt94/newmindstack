
import sqlite3
import os

db_path = r'c:\Code\MindStack\database\mindstack_new.db'
if not os.path.exists(db_path):
    # Try alternate paths if local dev env
    db_path = r'instance/mindstack.sqlite'
    if not os.path.exists(db_path):
        print(f"DB not found")
        exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("SELECT id, email, password_hash FROM user LIMIT 5")
    rows = cursor.fetchall()
    print("Users found:")
    for row in rows:
        print(f"ID: {row[0]}, Email: {row[1]}")
except Exception as e:
    print(f"Error querying users: {e}")
    try:
        cursor.execute("SELECT user_id, email FROM users LIMIT 5")
        rows = cursor.fetchall()
        for row in rows:
            print(f"ID: {row[0]}, Email: {row[1]}")
    except Exception as e2:
        print(f"Error querying users table: {e2}")

conn.close()
