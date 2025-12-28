"""
Script to drop review_history columns from flashcard_progress and quiz_progress tables.
Run this directly: python drop_review_history_columns.py
"""
import sqlite3

db_path = r'C:\Code\MindStack\database\mindstack_new.db'

def drop_column_from_table(cursor, table_name, column_to_drop):
    """Drop a column from a table by recreating it without that column."""
    
    # Get current columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    all_columns = cursor.fetchall()
    existing_columns = {col[1] for col in all_columns}
    
    if column_to_drop not in existing_columns:
        print(f"  Column '{column_to_drop}' not found in {table_name}, skipping")
        return
    
    # Get columns to keep
    columns_to_keep = [col for col in all_columns if col[1] != column_to_drop]
    column_names = [col[1] for col in columns_to_keep]
    
    # Build column definitions
    column_defs = []
    for col in columns_to_keep:
        cid, name, dtype, notnull, default, pk = col
        parts = [name, dtype]
        if pk:
            parts.append("PRIMARY KEY")
        if notnull and not pk:
            parts.append("NOT NULL")
        if default is not None:
            parts.append(f"DEFAULT {default}")
        column_defs.append(" ".join(parts))
    
    print(f"  Dropping '{column_to_drop}' from {table_name}...")
    print(f"  Keeping columns: {column_names}")
    
    # Create new table
    columns_str = ", ".join(column_defs)
    cursor.execute(f"CREATE TABLE {table_name}_new ({columns_str})")
    
    # Copy data
    keep_cols = ", ".join(column_names)
    cursor.execute(f"INSERT INTO {table_name}_new ({keep_cols}) SELECT {keep_cols} FROM {table_name}")
    
    # Drop old table and rename new
    cursor.execute(f"DROP TABLE {table_name}")
    cursor.execute(f"ALTER TABLE {table_name}_new RENAME TO {table_name}")
    
    print(f"  SUCCESS: Dropped '{column_to_drop}' from {table_name}")


conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== DROP REVIEW_HISTORY COLUMNS ===\n")

# Confirm
confirm = input("This will drop review_history columns from flashcard_progress and quiz_progress. Proceed? (yes/no): ")
if confirm.lower() != 'yes':
    print("Aborted.")
    conn.close()
    exit(0)

try:
    print("\n--- flashcard_progress ---")
    drop_column_from_table(cursor, 'flashcard_progress', 'review_history')
    
    print("\n--- quiz_progress ---")
    drop_column_from_table(cursor, 'quiz_progress', 'review_history')
    
    conn.commit()
    print("\n=== DONE ===")
    
    # Verify
    print("\nVerifying final schema:")
    for table in ['flashcard_progress', 'quiz_progress']:
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [col[1] for col in cursor.fetchall()]
        print(f"  {table}: {cols}")

except Exception as e:
    print(f"\nERROR: {e}")
    conn.rollback()

conn.close()
