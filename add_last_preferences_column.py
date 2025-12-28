"""
Script to add last_preferences JSON column to users table.
Run this directly: python add_last_preferences_column.py
"""
import sqlite3
import os

# Database path based on config.py: BASE_DIR/../database/mindstack_new.db
# From newmindstack folder, go up to MindStack, then to database folder
db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'mindstack_new.db')
db_path = os.path.abspath(db_path)

print(f"Looking for database at: {db_path}")
print(f"Exists: {os.path.exists(db_path)}")

if not os.path.exists(db_path):
    print("ERROR: Database file not found!")
    print("Please provide the correct path to your mindstack.db file")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if column already exists
cursor.execute("PRAGMA table_info(users)")
columns = [col[1] for col in cursor.fetchall()]
print(f"Current columns in users table: {columns}")

if 'last_preferences' in columns:
    print("Column 'last_preferences' already exists!")
else:
    print("Adding 'last_preferences' column...")
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN last_preferences TEXT DEFAULT '{}'")
        conn.commit()
        print("SUCCESS: Column 'last_preferences' added!")
    except Exception as e:
        print(f"ERROR: {e}")

conn.close()
print("Done!")
