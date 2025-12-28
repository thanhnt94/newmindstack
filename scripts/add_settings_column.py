import sys
import os

# Create a migration script to add the column if it doesn't exist
# This is safer than relying on implicit migrations in this context

sys.path.append(os.getcwd())
from mindstack_app import create_app, db
from sqlalchemy import text

app = create_app()

def add_column():
    with app.app_context():
        try:
            # Check if column exists
            with db.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(user_container_states)"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'settings' in columns:
                    print("Column 'settings' already exists in 'user_container_states'.")
                else:
                    print("Adding 'settings' column to 'user_container_states'...")
                    # SQLite syntax for adding generic column. JSON type is stored as TEXT/JSON in modern SQLite
                    conn.execute(text("ALTER TABLE user_container_states ADD COLUMN settings JSON DEFAULT '{}'"))
                    conn.commit()
                    print("Column added successfully.")
        except Exception as e:
            print(f"Error executing migration: {e}")

if __name__ == "__main__":
    add_column()
