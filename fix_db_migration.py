import os
import sqlite3
from flask import current_app
from mindstack_app import create_app
from mindstack_app.core.extensions import db

def fix_database():
    app = create_app()
    with app.app_context():
        # Get SQLite path from config
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if not db_uri.startswith('sqlite:///'):
            print(f"Not a SQLite database: {db_uri}")
            return
        
        db_path = db_uri.replace('sqlite:///', '')
        if not os.path.isabs(db_path):
            db_path = os.path.join(app.root_path, '..', db_path)
        
        db_path = os.path.abspath(db_path)
        print(f"Target Database: {db_path}")
        
        if not os.path.exists(db_path):
            print("Database file not found!")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Check if column exists
            cursor.execute("PRAGMA table_info(study_logs)")
            columns = [info[1] for info in cursor.fetchall()]
            
            if 'context_snapshot' not in columns:
                print("Adding 'context_snapshot' column to 'study_logs' table...")
                cursor.execute("ALTER TABLE study_logs ADD COLUMN context_snapshot JSON")
                conn.commit()
                print("Successfully added column.")
            else:
                print("'context_snapshot' column already exists.")

            # Double check other columns I might have added or need
            if 'gamification_snapshot' not in columns:
                print("Adding 'gamification_snapshot' column to 'study_logs' table...")
                cursor.execute("ALTER TABLE study_logs ADD COLUMN gamification_snapshot JSON")
                conn.commit()
            
            if 'fsrs_snapshot' not in columns:
                print("Adding 'fsrs_snapshot' column to 'study_logs' table...")
                cursor.execute("ALTER TABLE study_logs ADD COLUMN fsrs_snapshot JSON")
                conn.commit()

        except Exception as e:
            print(f"Error: {e}")
        finally:
            conn.close()

if __name__ == '__main__':
    fix_database()
