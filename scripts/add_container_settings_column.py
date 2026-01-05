import sys
import os

# Create a migration script to add the settings column to learning_containers if it doesn't exist

sys.path.append(os.getcwd())
try:
    from mindstack_app import create_app, db
    from sqlalchemy import text

    app = create_app()

    def add_column():
        with app.app_context():
            try:
                # Check if column exists
                with db.engine.connect() as conn:
                    # SQLite specific check
                    result = conn.execute(text("PRAGMA table_info(learning_containers)"))
                    columns = [row[1] for row in result.fetchall()]
                    
                    if 'settings' in columns:
                        print("Column 'settings' already exists in 'learning_containers'.")
                    else:
                        print("Adding 'settings' column to 'learning_containers'...")
                        # SQLite syntax for adding generic column. JSON type is stored as TEXT/JSON in modern SQLite
                        conn.execute(text("ALTER TABLE learning_containers ADD COLUMN settings JSON DEFAULT '{}'"))
                        conn.commit()
                        print("Column added successfully.")
            except Exception as e:
                print(f"Error executing migration: {e}")

    if __name__ == "__main__":
        add_column()
except ImportError:
    # Failback if imports fail (e.g. running from wrong dir)
    print("Could not import app. Run from project root.")
