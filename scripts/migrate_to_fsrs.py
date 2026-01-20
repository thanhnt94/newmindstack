"""
FSRS Data Migration Script

Migrates existing LearningProgress records to use native FSRS columns.
Run this script AFTER the database migration adds the new columns.

Usage:
    python migrate_to_fsrs.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mindstack_app import create_app
from mindstack_app.models import db, LearningProgress


# FSRS State Mapping (string -> int)
STATE_MAP = {
    'new': LearningProgress.FSRS_STATE_NEW,
    'learning': LearningProgress.FSRS_STATE_LEARNING,
    're-learning': LearningProgress.FSRS_STATE_RELEARNING,
    'review': LearningProgress.FSRS_STATE_REVIEW,
}


def migrate_progress_records():
    """Migrate all LearningProgress records to native FSRS columns."""
    
    # Query all progress records
    total = LearningProgress.query.count()
    print(f"Found {total} progress records to migrate.")
    
    if total == 0:
        print("No records to migrate.")
        return
    
    # Process in batches
    BATCH_SIZE = 500
    migrated = 0
    legacy_converted = 0
    fsrs_migrated = 0
    skipped = 0
    
    for offset in range(0, total, BATCH_SIZE):
        batch = LearningProgress.query.offset(offset).limit(BATCH_SIZE).all()
        
        for progress in batch:
            mode_data = progress.mode_data or {}
            
            # Skip if already migrated (has valid fsrs_stability > 0)
            if progress.fsrs_stability is not None and progress.fsrs_stability > 0:
                skipped += 1
                continue
            
            # Check if this is an FSRS v5 card (has fsrs_stability in mode_data)
            if 'fsrs_stability' in mode_data:
                # Copy from mode_data to native columns
                progress.fsrs_stability = mode_data.get('fsrs_stability', 0.0)
                progress.fsrs_difficulty = mode_data.get('fsrs_difficulty', 5.0)
                
                # Map state string to int
                custom_state = mode_data.get('custom_state', 'new')
                progress.fsrs_state = STATE_MAP.get(custom_state, LearningProgress.FSRS_STATE_NEW)
                
                # Copy last_reviewed to fsrs_last_review
                progress.fsrs_last_review = progress.last_reviewed
                
                fsrs_migrated += 1
                
            elif mode_data.get('is_fsrs_v5') or progress.easiness_factor is not None:
                # Legacy FSRS hybrid: EF was used for stability
                # NOTE: This is incorrect data but we try to salvage what we can
                
                # Use interval as approximate stability (if interval was in days)
                if progress.interval and progress.interval > 0:
                    # interval is in minutes, convert to days for stability
                    progress.fsrs_stability = progress.interval / 1440.0
                else:
                    progress.fsrs_stability = 0.0
                
                # Default difficulty
                progress.fsrs_difficulty = 5.0
                
                # Determine state based on reps
                if progress.repetitions and progress.repetitions > 0:
                    progress.fsrs_state = LearningProgress.FSRS_STATE_REVIEW
                else:
                    progress.fsrs_state = LearningProgress.FSRS_STATE_NEW
                
                progress.fsrs_last_review = progress.last_reviewed
                
                legacy_converted += 1
                
            else:
                # Brand new card - set to defaults
                progress.fsrs_stability = 0.0
                progress.fsrs_difficulty = 5.0
                progress.fsrs_state = LearningProgress.FSRS_STATE_NEW
                progress.fsrs_last_review = None
                
                legacy_converted += 1
            
            migrated += 1
        
        # Commit batch
        db.session.commit()
        print(f"Processed {min(offset + BATCH_SIZE, total)}/{total} records...")
    
    print(f"\n=== Migration Complete ===")
    print(f"Total processed: {migrated}")
    print(f"FSRS cards migrated: {fsrs_migrated}")
    print(f"Legacy cards converted: {legacy_converted}")
    print(f"Already migrated (skipped): {skipped}")


def verify_migration():
    """Verify migration was successful."""
    
    # Count records with valid FSRS data
    with_stability = LearningProgress.query.filter(
        LearningProgress.fsrs_stability.isnot(None)
    ).count()
    
    total = LearningProgress.query.count()
    
    print(f"\n=== Migration Verification ===")
    print(f"Total records: {total}")
    print(f"Records with fsrs_stability: {with_stability}")
    print(f"Migration coverage: {(with_stability/total*100):.1f}%" if total > 0 else "N/A")


if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        print("=" * 50)
        print("FSRS Data Migration Script")
        print("=" * 50)
        print()
        
        # Confirm before running
        response = input("This will migrate all LearningProgress records. Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            sys.exit(0)
        
        print("\nStarting migration...")
        migrate_progress_records()
        
        print("\nVerifying migration...")
        verify_migration()
        
        print("\nDone!")
