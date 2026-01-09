import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from mindstack_app import create_app, db
from mindstack_app.models.learning_session import LearningSession

def migrate():
    app = create_app()
    with app.app_context():
        print("Starting migration...")
        try:
            # Check if table already exists
            inspector = db.inspect(db.engine)
            if 'learning_sessions' in inspector.get_table_names():
                print("Table 'learning_sessions' already exists. Skipping creation.")
            else:
                db.create_all()
                print("Table 'learning_sessions' created successfully!")
        except Exception as e:
            print(f"Error during migration: {e}")
            sys.exit(1)

if __name__ == "__main__":
    migrate()
