"""
Script to add new columns to review_logs table.
Run this directly: python migrate_review_logs_schema.py
"""
import sqlite3

db_path = r'C:\Code\MindStack\database\mindstack_new.db'

# New columns to add
NEW_COLUMNS = [
    ('user_answer', 'VARCHAR(10)'),
    ('is_correct', 'BOOLEAN'),
    ('score_change', 'INTEGER'),
    ('mastery_snapshot', 'REAL'),
    ('memory_power_snapshot', 'REAL'),
]

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get current columns
cursor.execute("PRAGMA table_info(review_logs)")
existing_columns = {col[1] for col in cursor.fetchall()}
print(f"Existing columns: {existing_columns}")

added = []
for col_name, col_type in NEW_COLUMNS:
    if col_name in existing_columns:
        print(f"  Column '{col_name}' already exists, skipping")
    else:
        print(f"  Adding column '{col_name}' ({col_type})...")
        try:
            cursor.execute(f"ALTER TABLE review_logs ADD COLUMN {col_name} {col_type}")
            added.append(col_name)
        except Exception as e:
            print(f"    ERROR: {e}")

conn.commit()

# Verify
cursor.execute("PRAGMA table_info(review_logs)")
new_columns = [col[1] for col in cursor.fetchall()]
print(f"\nFinal columns: {new_columns}")
print(f"Added: {added}")

conn.close()
print("\nDone!")
