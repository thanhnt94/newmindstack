"""
Script to drop deprecated columns from users table.
These columns have been moved to user_sessions table.

Run this directly: python drop_deprecated_user_columns.py
"""
import sqlite3

db_path = r'C:\Code\MindStack\database\mindstack_new.db'

# Columns to drop from users table
DEPRECATED_COLUMNS = [
    'current_flashcard_container_id',
    'current_quiz_container_id', 
    'current_course_container_id',
    'current_flashcard_mode',
    'current_quiz_mode',
    'current_quiz_batch_size',
    'flashcard_button_count'
]

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get current columns
cursor.execute("PRAGMA table_info(users)")
current_columns = {col[1]: col for col in cursor.fetchall()}
print(f"Current columns in users table: {list(current_columns.keys())}")

# Find which deprecated columns exist
columns_to_drop = [col for col in DEPRECATED_COLUMNS if col in current_columns]
print(f"\nColumns to drop: {columns_to_drop}")

if not columns_to_drop:
    print("No deprecated columns found to drop!")
    conn.close()
    exit(0)

# SQLite doesn't support DROP COLUMN directly for older versions
# We need to recreate the table without the deprecated columns

# Get columns to keep
columns_to_keep = [col for col in current_columns.keys() if col not in DEPRECATED_COLUMNS]
print(f"\nColumns to keep: {columns_to_keep}")

# Get column definitions for columns to keep
column_defs = []
for col_name in columns_to_keep:
    col_info = current_columns[col_name]
    # col_info: (cid, name, type, notnull, default, pk)
    cid, name, dtype, notnull, default, pk = col_info
    
    parts = [name, dtype]
    if pk:
        parts.append("PRIMARY KEY")
    if notnull and not pk:
        parts.append("NOT NULL")
    if default is not None:
        parts.append(f"DEFAULT {default}")
    
    column_defs.append(" ".join(parts))

print(f"\nNew column definitions:")
for cd in column_defs:
    print(f"  {cd}")

# Confirm before proceeding
confirm = input("\nProceed with dropping columns? (yes/no): ")
if confirm.lower() != 'yes':
    print("Aborted.")
    conn.close()
    exit(0)

try:
    # Create new table without deprecated columns
    columns_str = ", ".join(column_defs)
    cursor.execute(f"CREATE TABLE users_new ({columns_str})")
    
    # Copy data
    keep_cols = ", ".join(columns_to_keep)
    cursor.execute(f"INSERT INTO users_new ({keep_cols}) SELECT {keep_cols} FROM users")
    
    # Drop old table
    cursor.execute("DROP TABLE users")
    
    # Rename new table
    cursor.execute("ALTER TABLE users_new RENAME TO users")
    
    conn.commit()
    print("\nSUCCESS: Deprecated columns dropped!")
    
    # Verify
    cursor.execute("PRAGMA table_info(users)")
    new_columns = [col[1] for col in cursor.fetchall()]
    print(f"New columns: {new_columns}")
    
except Exception as e:
    print(f"\nERROR: {e}")
    conn.rollback()

conn.close()
print("\nDone!")
