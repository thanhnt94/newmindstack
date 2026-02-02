import sqlite3
import os

db_path = r'C:\Code\MindStack\database\mindstack_new.db'

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def fix_table(table_name, expected_columns):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns_info = cursor.fetchall()
    existing_columns = [col[1] for col in columns_info]
    print(f"Checking table '{table_name}'. Existing columns: {existing_columns}")
    
    for col_name, col_type in expected_columns:
        if col_name not in existing_columns:
            print(f"Adding column '{col_name}' ({col_type}) to '{table_name}'")
            try:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                print(f"Added {col_name}")
            except Exception as e:
                print(f"Failed to add {col_name}: {e}")

expected_memory = [
    ('stability', 'FLOAT DEFAULT 0.0'),
    ('difficulty', 'FLOAT DEFAULT 0.0'),
    ('state', 'INTEGER DEFAULT 0'),
    ('due_date', 'DATETIME'),
    ('last_review', 'DATETIME'),
    ('repetitions', 'INTEGER DEFAULT 0'),
    ('lapses', 'INTEGER DEFAULT 0'),
    ('streak', 'INTEGER DEFAULT 0'),
    ('incorrect_streak', 'INTEGER DEFAULT 0'),
    ('times_correct', 'INTEGER DEFAULT 0'),
    ('times_incorrect', 'INTEGER DEFAULT 0'),
    ('data', 'JSON'),
    ('created_at', 'DATETIME'),
    ('updated_at', 'DATETIME')
]

expected_logs = [
    ('rating', 'INTEGER'),
    ('user_answer', 'TEXT'),
    ('is_correct', 'BOOLEAN'),
    ('review_duration', 'INTEGER DEFAULT 0'),
    ('session_id', 'INTEGER'),
    ('container_id', 'INTEGER'),
    ('learning_mode', 'VARCHAR(50)'),
    ('fsrs_snapshot', 'JSON'),
    ('gamification_snapshot', 'JSON')
]

fix_table('item_memory_states', expected_memory)
fix_table('study_logs', expected_logs)

conn.commit()
conn.close()
print("Migration successful.")
