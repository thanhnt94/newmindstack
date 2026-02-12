
import sqlite3
import os

db_path = r'c:\Code\MindStack\database\mindstack_new.db'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables:")
for table in tables:
    print(table[0])
    # Print schema for user related tables
    if 'user' in table[0].lower():
        cursor.execute(f"PRAGMA table_info({table[0]})")
        columns = cursor.fetchall()
        print(f"  Schema for {table[0]}:")
        for col in columns:
             print(f"    {col[1]} ({col[2]})")

conn.close()
