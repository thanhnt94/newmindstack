"""
Database Migration: Rename FSRS Columns

This script renames columns from legacy prefixed names to clean FSRS names:
- fsrs_stability -> stability
- fsrs_difficulty -> difficulty
- fsrs_state -> state
- due_time -> due
- last_reviewed -> last_review

Run: python scripts/rename_fsrs_columns.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mindstack_app import create_app
from mindstack_app.models import db
from sqlalchemy import text, inspect


def rename_columns():
    """Rename FSRS columns to clean names."""
    
    inspector = inspect(db.engine)
    existing_columns = [col['name'] for col in inspector.get_columns('learning_progress')]
    
    print(f"Existing columns: {existing_columns}")
    
    # Column renames: (old_name, new_name)
    renames = [
        ('fsrs_stability', 'stability'),
        ('fsrs_difficulty', 'difficulty'),
        ('fsrs_state', 'state'),
        ('due_time', 'due'),
        ('last_reviewed', 'last_review'),
    ]
    
    renamed = []
    skipped = []
    
    for old_name, new_name in renames:
        if old_name not in existing_columns:
            if new_name in existing_columns:
                skipped.append(f"{old_name} -> {new_name} (new already exists)")
            else:
                skipped.append(f"{old_name} (source not found)")
            continue
        
        if new_name in existing_columns:
            skipped.append(f"{old_name} -> {new_name} (new already exists)")
            continue
        
        try:
            # SQLite doesn't support direct column rename until 3.25.0
            # For safety, use ALTER TABLE RENAME COLUMN
            sql = f"ALTER TABLE learning_progress RENAME COLUMN {old_name} TO {new_name}"
            db.session.execute(text(sql))
            renamed.append(f"{old_name} -> {new_name}")
            print(f"✓ Renamed: {old_name} -> {new_name}")
        except Exception as e:
            print(f"✗ Failed to rename {old_name}: {e}")
    
    db.session.commit()
    
    print(f"\n=== Migration Complete ===")
    print(f"Renamed: {renamed}")
    print(f"Skipped: {skipped}")


def drop_legacy_columns():
    """Drop legacy SM2 columns (optional, run after verifying everything works)."""
    
    inspector = inspect(db.engine)
    existing_columns = [col['name'] for col in inspector.get_columns('learning_progress')]
    
    legacy_columns = ['easiness_factor', 'times_vague', 'vague_streak', 'status', 'mastery', 'fsrs_last_review']
    
    print("\n⚠️ WARNING: About to DROP columns. This cannot be undone!")
    print(f"Columns to drop: {[c for c in legacy_columns if c in existing_columns]}")
    
    response = input("Continue? [y/N]: ")
    if response.lower() != 'y':
        print("Drop cancelled.")
        return
    
    for col in legacy_columns:
        if col not in existing_columns:
            continue
        
        try:
            # SQLite doesn't support DROP COLUMN directly before 3.35.0
            # This may fail on older SQLite versions
            sql = f"ALTER TABLE learning_progress DROP COLUMN {col}"
            db.session.execute(text(sql))
            print(f"✓ Dropped: {col}")
        except Exception as e:
            print(f"✗ Failed to drop {col}: {e}")
    
    db.session.commit()


if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        print("=" * 50)
        print("FSRS Column Rename Migration")
        print("=" * 50)
        print()
        
        # Step 1: Rename columns
        response = input("Step 1: Rename columns? [y/N]: ")
        if response.lower() == 'y':
            rename_columns()
        
        # Step 2: Drop legacy columns (optional)
        response = input("\nStep 2: Drop legacy columns? [y/N]: ")
        if response.lower() == 'y':
            drop_legacy_columns()
        
        print("\nDone!")
