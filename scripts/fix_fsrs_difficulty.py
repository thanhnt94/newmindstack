"""
FSRS Difficulty Data Repair Script

Fixes legacy data where `fsrs_difficulty` and/or `mode_data['precise_interval']`
were incorrectly set to values > 10.0 (out of FSRS Difficulty range 1-10).

This caused cards to be treated as "maximum difficulty" resulting in tiny intervals.

Run: python scripts/fix_fsrs_difficulty.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mindstack_app import create_app
from mindstack_app.models import db, LearningProgress
from sqlalchemy.orm.attributes import flag_modified


# FSRS Difficulty range
MIN_DIFFICULTY = 1.0
MAX_DIFFICULTY = 10.0
DEFAULT_DIFFICULTY = 5.0  # Medium difficulty


def fix_fsrs_difficulty():
    """Fix all LearningProgress records with out-of-range difficulty values."""
    
    total = LearningProgress.query.count()
    print(f"Found {total} progress records to check.")
    
    if total == 0:
        print("No records to check.")
        return
    
    # Process in batches
    BATCH_SIZE = 500
    fixed_native = 0
    fixed_mode_data = 0
    checked = 0
    
    for offset in range(0, total, BATCH_SIZE):
        batch = LearningProgress.query.offset(offset).limit(BATCH_SIZE).all()
        
        for progress in batch:
            needs_save = False
            
            # Fix 1: Native fsrs_difficulty column
            if progress.fsrs_difficulty is not None:
                if progress.fsrs_difficulty > MAX_DIFFICULTY:
                    old_val = progress.fsrs_difficulty
                    progress.fsrs_difficulty = DEFAULT_DIFFICULTY
                    fixed_native += 1
                    needs_save = True
                    print(f"  Fixed native D: {old_val:.1f} → {DEFAULT_DIFFICULTY} (Progress ID: {progress.progress_id})")
                elif progress.fsrs_difficulty < MIN_DIFFICULTY:
                    progress.fsrs_difficulty = MIN_DIFFICULTY
                    fixed_native += 1
                    needs_save = True
            
            # Fix 2: mode_data['precise_interval'] (legacy D storage)
            mode_data = progress.mode_data or {}
            if 'precise_interval' in mode_data:
                precise_interval = mode_data['precise_interval']
                if isinstance(precise_interval, (int, float)) and precise_interval > MAX_DIFFICULTY:
                    old_val = precise_interval
                    mode_data['precise_interval'] = DEFAULT_DIFFICULTY
                    progress.mode_data = mode_data
                    flag_modified(progress, 'mode_data')
                    fixed_mode_data += 1
                    needs_save = True
                    print(f"  Fixed mode_data D: {old_val:.1f} → {DEFAULT_DIFFICULTY} (Progress ID: {progress.progress_id})")
            
            # Fix 3: mode_data['fsrs_difficulty'] (alternate location)
            if 'fsrs_difficulty' in mode_data:
                fsrs_d = mode_data['fsrs_difficulty']
                if isinstance(fsrs_d, (int, float)) and fsrs_d > MAX_DIFFICULTY:
                    mode_data['fsrs_difficulty'] = DEFAULT_DIFFICULTY
                    progress.mode_data = mode_data
                    flag_modified(progress, 'mode_data')
                    fixed_mode_data += 1
                    needs_save = True
            
            checked += 1
        
        # Commit batch
        db.session.commit()
        print(f"Checked {min(offset + BATCH_SIZE, total)}/{total} records...")
    
    print(f"\n=== Repair Complete ===")
    print(f"Total checked: {checked}")
    print(f"Fixed native fsrs_difficulty: {fixed_native}")
    print(f"Fixed mode_data entries: {fixed_mode_data}")


def verify_fix():
    """Verify all difficulty values are within range."""
    
    # Count records outside range
    out_of_range = LearningProgress.query.filter(
        LearningProgress.fsrs_difficulty > MAX_DIFFICULTY
    ).count()
    
    print(f"\n=== Verification ===")
    print(f"Records with fsrs_difficulty > 10: {out_of_range}")
    
    if out_of_range == 0:
        print("✓ All difficulty values are within valid range!")
    else:
        print("⚠ Some records still have invalid difficulty values.")


if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        print("=" * 50)
        print("FSRS Difficulty Data Repair Script")
        print("=" * 50)
        print(f"\nThis script fixes difficulty values outside range [{MIN_DIFFICULTY}-{MAX_DIFFICULTY}]")
        print(f"Invalid values will be reset to {DEFAULT_DIFFICULTY} (Medium).\n")
        
        # Confirm before running
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Repair cancelled.")
            sys.exit(0)
        
        print("\nStarting repair...")
        fix_fsrs_difficulty()
        
        print("\nVerifying fix...")
        verify_fix()
        
        print("\nDone!")
