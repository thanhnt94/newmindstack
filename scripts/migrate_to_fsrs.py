"""
FSRS v5 Data Migration Script (Hard Reset)

Refactors existing LearningProgress records to FSRS v5 Native.
STRATEGY: Hard Reset
- Stability (S) -> 0.0 (All cards treated as fresh)
- Difficulty (D) -> 5.0 (Default)
- Lapses -> times_incorrect (Proxy for historical failures)
- State -> NEW (0) implies fresh start for scheduling

Usage:
    python scripts/migrate_to_fsrs.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mindstack_app import create_app
from mindstack_app.models import db, LearningProgress, LearningItem

def migrate_progress_records():
    """Migrate all LearningProgress records to native FSRS columns."""
    
    total = LearningProgress.query.count()
    print(f"Found {total} progress records to migrate.")
    
    if total == 0:
        return
    
    BATCH_SIZE = 1000
    migrated = 0
    
    # Process in batches
    for offset in range(0, total, BATCH_SIZE):
        batch = LearningProgress.query.offset(offset).limit(BATCH_SIZE).all()
        
        for progress in batch:
            # === FSRS v5 HARD RESET ===
            
            # 1. Reset FSRS State
            # Default Difficulty (D) = 5.0 (Center of 1-10 scale)
            progress.fsrs_difficulty = 5.0
            
            # Stability (S) = 0.0
            # Treating all cards as fresh for the new algorithm to re-learn patterns
            progress.fsrs_stability = 0.0
            
            # State = NEW (0)
            # Since S=0, it's effectively a new card for the algorithm
            progress.fsrs_state = LearningProgress.STATE_NEW
            
            # 2. Migrate History to Lapses
            # Lapses are critical for FSRS. Proxy using times_incorrect.
            incorrect_count = progress.times_incorrect or 0
            progress.lapses = incorrect_count
            
            # 3. Ensure other fields are defaults
            if progress.repetitions is None:
                progress.repetitions = 0
            
            # 4. Clear/Update Legacy Fields
            # Assuming 'current_interval' is the new field, we can reset it or keep it 0
            progress.current_interval = 0.0
            
            migrated += 1
        
        try:
            db.session.commit()
            print(f"Processed {min(offset + BATCH_SIZE, total)}/{total} records...")
        except Exception as e:
            db.session.rollback()
            print(f"Error executing batch: {e}")
            
    print(f"\n=== Migration Complete ===")
    print(f"Total processed: {migrated}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("=" * 50)
        print("FSRS Data Migration (Hard Reset)")
        print("=" * 50)
        print("WARNING: This will reset stability to 0.0 and difficulty to 5.0 for ALL cards.")
        print("This treats all cards as new for the scheduling algorithm.")
        
        # confirm = input("Continue? [y/N]: ")
        # if confirm.lower() != 'y':
        #     sys.exit()
            
        migrate_progress_records()
