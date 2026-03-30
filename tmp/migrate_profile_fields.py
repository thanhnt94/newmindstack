import sqlite3
import os

# Database path
MINDSTACK_DB = r"c:\Code\Ecosystem\Storage\database\Mindstack.db"

def migrate():
    print(f"Connecting to MindStack database: {MINDSTACK_DB}")
    if not os.path.exists(MINDSTACK_DB):
        print("Database not found!")
        return

    conn = sqlite3.connect(MINDSTACK_DB)
    cursor = conn.cursor()

    try:
        # 1. Check existing columns
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # 2. Add full_name column if missing
        if "full_name" not in columns:
            print("Adding 'full_name' column to 'users' table...")
            cursor.execute("ALTER TABLE users ADD COLUMN full_name VARCHAR(255)")
            print("Successfully added 'full_name'.")
        else:
            print("'full_name' column already exists.")

        conn.commit()
        print("Migration finished successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
