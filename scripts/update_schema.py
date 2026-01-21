"""
Database Schema Update Script
Adds missing columns for FSRS v5 Native support.
"""
import sys
import os
from sqlalchemy import text, inspect

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mindstack_app import create_app
from mindstack_app.models import db

def add_column_if_not_exists(table_name, column_name, column_type):
    engine = db.engine
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    
    if column_name not in columns:
        print(f"Adding column '{column_name}' to table '{table_name}'...")
        with engine.connect() as conn:
            # PostgreSQL/SQLite syntax compatible for simple ADD COLUMN
            # Note: SQLite has limited ALTER TABLE support, but ADD COLUMN is usually supported.
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
            conn.commit()
    else:
        print(f"Column '{column_name}' already exists in '{table_name}'.")

def update_schema():
    app = create_app()
    with app.app_context():
        print("Checking schema...")
        
        # LearningProgress
        add_column_if_not_exists('learning_progress', 'lapses', 'INTEGER DEFAULT 0')
        add_column_if_not_exists('learning_progress', 'last_review_duration', 'INTEGER DEFAULT 0')
        add_column_if_not_exists('learning_progress', 'current_interval', 'FLOAT DEFAULT 0')
        
        # Make sure FSRS core columns exist (if they weren't added before)
        add_column_if_not_exists('learning_progress', 'fsrs_stability', 'FLOAT DEFAULT 0')
        add_column_if_not_exists('learning_progress', 'fsrs_difficulty', 'FLOAT DEFAULT 0')
        add_column_if_not_exists('learning_progress', 'fsrs_state', 'INTEGER DEFAULT 0')
        # DateTime columns might need specific handling for SQLite/Postgres
        # Assume SQLite/Postgres standard
        add_column_if_not_exists('learning_progress', 'fsrs_due', 'TIMESTAMP') 
        add_column_if_not_exists('learning_progress', 'fsrs_last_review', 'TIMESTAMP')

        # ReviewLog (Table: review_logs)
        add_column_if_not_exists('review_logs', 'scheduled_days', 'FLOAT DEFAULT 0')
        add_column_if_not_exists('review_logs', 'elapsed_days', 'FLOAT DEFAULT 0')
        add_column_if_not_exists('review_logs', 'review_duration', 'INTEGER DEFAULT 0')
        add_column_if_not_exists('review_logs', 'state', 'INTEGER DEFAULT 0')
        
        # Snapshots in ReviewLog
        add_column_if_not_exists('review_logs', 'fsrs_stability', 'FLOAT DEFAULT 0')
        add_column_if_not_exists('review_logs', 'fsrs_difficulty', 'FLOAT DEFAULT 0')

        print("Schema update complete.")

if __name__ == '__main__':
    update_schema()
