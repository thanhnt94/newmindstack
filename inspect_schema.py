
import sqlite3

db_path = 'c:/Code/MindStack/database/mindstack_new.db.last_corrupted'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Listing all tables and their types:")
cursor.execute("SELECT name, type, sql FROM sqlite_master WHERE type='table'")
for name, type_, sql in cursor.fetchall():
    print(f"Name: {name}, Type: {type_}")
    if sql and 'VIRTUAL' in sql:
        print(f"  [VIRTUAL TABLE] SQL: {sql}")

print("\nListing all indices:")
cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index'")
for name, sql in cursor.fetchall():
    if sql:
        print(f"Index: {name}")

conn.close()
