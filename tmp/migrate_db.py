import sqlite3
import os

# Define database path based on configuration
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATABASE_PATH = r"c:\Code\Ecosystem\Storage\database\Mindstack.db"

def migrate():
    print(f"Connecting to database: {DATABASE_PATH}")
    if not os.path.exists(DATABASE_PATH):
        print("Database file not found!")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Get existing columns
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Existing columns in 'users': {columns}")

    # Add central_auth_id if missing
    if "central_auth_id" not in columns:
        print("Adding column 'central_auth_id'...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN central_auth_id VARCHAR(255)")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_central_auth_id ON users (central_auth_id)")
            print("Successfully added 'central_auth_id'.")
        except Exception as e:
            print(f"Error adding 'central_auth_id': {e}")
    else:
        print("'central_auth_id' already exists.")

    # Add last_preferences if missing
    if "last_preferences" not in columns:
        print("Adding column 'last_preferences'...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN last_preferences TEXT")
            print("Successfully added 'last_preferences'.")
        except Exception as e:
            print(f"Error adding 'last_preferences': {e}")
    else:
        print("'last_preferences' already exists.")

    conn.commit()
    conn.close()
    print("Migration finished.")

if __name__ == "__main__":
    migrate()
