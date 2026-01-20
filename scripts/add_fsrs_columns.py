"""
Direct Database Migration: Add FSRS Columns

This script adds native FSRS columns directly to the database
without requiring Flask-Migrate setup.

Run: python scripts/add_fsrs_columns.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mindstack_app import create_app
from mindstack_app.models import db
from sqlalchemy import text, inspect


def add_fsrs_columns():
    """Add native FSRS columns to learning_progress table."""
    
    inspector = inspect(db.engine)
    existing_columns = [col['name'] for col in inspector.get_columns('learning_progress')]
    
    columns_to_add = [
        ('fsrs_stability', 'FLOAT DEFAULT 0.0'),
        ('fsrs_difficulty', 'FLOAT DEFAULT 5.0'),
        ('fsrs_state', 'INTEGER DEFAULT 0'),
        ('fsrs_last_review', 'DATETIME'),
    ]
    
    added = []
    skipped = []
    
    for col_name, col_type in columns_to_add:
        if col_name in existing_columns:
            skipped.append(col_name)
            continue
        
        try:
            sql = f"ALTER TABLE learning_progress ADD COLUMN {col_name} {col_type}"
            db.session.execute(text(sql))
            added.append(col_name)
            print(f"✓ Added column: {col_name}")
        except Exception as e:
            print(f"✗ Failed to add {col_name}: {e}")
    
    db.session.commit()
    
    print(f"\n=== Migration Complete ===")
    print(f"Added: {added}")
    print(f"Skipped (already exist): {skipped}")


if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        print("=" * 50)
        print("Add Native FSRS Columns")
        print("=" * 50)
        print()
        
        add_fsrs_columns()
        
        print("\nDone!")
