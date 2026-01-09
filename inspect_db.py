import sqlite3
import os

db_path = r'c:\Code\MindStack\database\mindstack_new.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]

with open('db_info.txt', 'w', encoding='utf-8') as f:
    f.write(f"Full Table List: {tables}\n")
    for table in tables:
        if 'learning_sessions' in table.lower():
            f.write(f"\nSchema for {table}:\n")
            cursor.execute(f"PRAGMA table_info({table})")
            cols = cursor.fetchall()
            for col in cols:
                f.write(f"{col}\n")

conn.close()
