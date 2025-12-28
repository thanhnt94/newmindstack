"""
Database Migration Script: Progress Tables Unification
=======================================================

This script migrates data from the legacy progress tables:
- flashcard_progress (55 rows)
- quiz_progress (271 rows)  
- memrise_progress (9 rows)
- course_progress (0 rows)

To the new unified learning_progress table.

Usage:
    python scripts/migrate_progress_tables.py [--dry-run] [--verify-only]
    
Options:
    --dry-run       Show what would be migrated without making changes
    --verify-only   Only verify existing migration, don't migrate
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from mindstack_app import create_app
from mindstack_app.models import db
from mindstack_app.models.user import (
    FlashcardProgress, QuizProgress, CourseProgress
)
from mindstack_app.models.memrise import MemriseProgress
from mindstack_app.models.learning_progress import LearningProgress


def count_legacy_records():
    """Count records in legacy tables."""
    return {
        'flashcard': FlashcardProgress.query.count(),
        'quiz': QuizProgress.query.count(),
        'memrise': MemriseProgress.query.count(),
        'course': CourseProgress.query.count(),
    }


def count_unified_records():
    """Count records in unified table by mode."""
    counts = {}
    for mode in ['flashcard', 'quiz', 'memrise', 'course']:
        counts[mode] = LearningProgress.query.filter_by(learning_mode=mode).count()
    return counts


def migrate_flashcard_progress(dry_run=False):
    """Migrate FlashcardProgress records to LearningProgress."""
    records = FlashcardProgress.query.all()
    migrated = 0
    skipped = 0
    
    for fp in records:
        # Check if already migrated
        existing = LearningProgress.query.filter_by(
            user_id=fp.user_id,
            item_id=fp.item_id,
            learning_mode='flashcard'
        ).first()
        
        if existing:
            skipped += 1
            continue
        
        if not dry_run:
            lp = LearningProgress(
                user_id=fp.user_id,
                item_id=fp.item_id,
                learning_mode='flashcard',
                status=fp.status or 'new',
                due_time=fp.due_time,
                easiness_factor=fp.easiness_factor or 2.5,
                interval=fp.interval or 0,
                repetitions=fp.repetitions or 0,
                last_reviewed=fp.last_reviewed,
                first_seen=fp.first_seen_timestamp,
                mastery=fp.mastery or 0.0,
                times_correct=fp.times_correct or 0,
                times_incorrect=fp.times_incorrect or 0,
                times_vague=fp.times_vague or 0,
                correct_streak=fp.correct_streak or 0,
                incorrect_streak=fp.incorrect_streak or 0,
                vague_streak=fp.vague_streak or 0,
                mode_data=None
            )
            db.session.add(lp)
        
        migrated += 1
    
    return migrated, skipped


def migrate_quiz_progress(dry_run=False):
    """Migrate QuizProgress records to LearningProgress."""
    records = QuizProgress.query.all()
    migrated = 0
    skipped = 0
    
    for qp in records:
        existing = LearningProgress.query.filter_by(
            user_id=qp.user_id,
            item_id=qp.item_id,
            learning_mode='quiz'
        ).first()
        
        if existing:
            skipped += 1
            continue
        
        if not dry_run:
            lp = LearningProgress(
                user_id=qp.user_id,
                item_id=qp.item_id,
                learning_mode='quiz',
                status=qp.status or 'new',
                due_time=None,  # Quiz doesn't use SRS scheduling
                easiness_factor=2.5,
                interval=0,
                repetitions=0,
                last_reviewed=qp.last_reviewed,
                first_seen=qp.first_seen_timestamp,
                mastery=qp.mastery or 0.0,
                times_correct=qp.times_correct or 0,
                times_incorrect=qp.times_incorrect or 0,
                times_vague=0,  # Quiz doesn't have vague
                correct_streak=qp.correct_streak or 0,
                incorrect_streak=qp.incorrect_streak or 0,
                vague_streak=0,
                mode_data=None
            )
            db.session.add(lp)
        
        migrated += 1
    
    return migrated, skipped


def migrate_memrise_progress(dry_run=False):
    """Migrate MemriseProgress records to LearningProgress."""
    records = MemriseProgress.query.all()
    migrated = 0
    skipped = 0
    
    for mp in records:
        existing = LearningProgress.query.filter_by(
            user_id=mp.user_id,
            item_id=mp.item_id,
            learning_mode='memrise'
        ).first()
        
        if existing:
            skipped += 1
            continue
        
        # Determine status based on memory level
        if mp.memory_level >= 7:
            status = 'mastered'
        elif mp.memory_level >= 4:
            status = 'reviewing'
        elif mp.memory_level >= 1:
            status = 'learning'
        else:
            status = 'new'
        
        if not dry_run:
            lp = LearningProgress(
                user_id=mp.user_id,
                item_id=mp.item_id,
                learning_mode='memrise',
                status=status,
                due_time=mp.due_time,
                easiness_factor=2.5,
                interval=mp.interval or 0,
                repetitions=0,
                last_reviewed=mp.last_reviewed,
                first_seen=mp.first_seen,
                mastery=mp.memory_level / 7.0 if mp.memory_level else 0.0,
                times_correct=mp.times_correct or 0,
                times_incorrect=mp.times_incorrect or 0,
                times_vague=0,
                correct_streak=0,
                incorrect_streak=0,
                vague_streak=0,
                mode_data={
                    'memory_level': mp.memory_level or 0,
                    'current_streak': mp.current_streak or 0,
                    'session_reps': mp.session_reps or 0,
                }
            )
            db.session.add(lp)
        
        migrated += 1
    
    return migrated, skipped


def migrate_course_progress(dry_run=False):
    """Migrate CourseProgress records to LearningProgress."""
    records = CourseProgress.query.all()
    migrated = 0
    skipped = 0
    
    for cp in records:
        existing = LearningProgress.query.filter_by(
            user_id=cp.user_id,
            item_id=cp.item_id,
            learning_mode='course'
        ).first()
        
        if existing:
            skipped += 1
            continue
        
        # Determine status based on completion
        if cp.completion_percentage >= 100:
            status = 'mastered'
        elif cp.completion_percentage > 0:
            status = 'learning'
        else:
            status = 'new'
        
        if not dry_run:
            lp = LearningProgress(
                user_id=cp.user_id,
                item_id=cp.item_id,
                learning_mode='course',
                status=status,
                mastery=cp.completion_percentage / 100.0,
                last_reviewed=cp.last_updated,
                mode_data={
                    'completion_percentage': cp.completion_percentage or 0,
                }
            )
            db.session.add(lp)
        
        migrated += 1
    
    return migrated, skipped


def run_migration(dry_run=False):
    """Run full migration."""
    print("=" * 60)
    print("Progress Tables Migration")
    print("=" * 60)
    
    if dry_run:
        print(">>> DRY RUN MODE - No changes will be made <<<\n")
    
    # Count legacy records
    print("Legacy record counts:")
    legacy_counts = count_legacy_records()
    for mode, count in legacy_counts.items():
        print(f"  {mode}_progress: {count}")
    print()
    
    # Run migrations
    results = {}
    
    print("Migrating flashcard_progress...")
    results['flashcard'] = migrate_flashcard_progress(dry_run)
    print(f"  Migrated: {results['flashcard'][0]}, Skipped: {results['flashcard'][1]}")
    
    print("Migrating quiz_progress...")
    results['quiz'] = migrate_quiz_progress(dry_run)
    print(f"  Migrated: {results['quiz'][0]}, Skipped: {results['quiz'][1]}")
    
    print("Migrating memrise_progress...")
    results['memrise'] = migrate_memrise_progress(dry_run)
    print(f"  Migrated: {results['memrise'][0]}, Skipped: {results['memrise'][1]}")
    
    print("Migrating course_progress...")
    results['course'] = migrate_course_progress(dry_run)
    print(f"  Migrated: {results['course'][0]}, Skipped: {results['course'][1]}")
    
    if not dry_run:
        print("\nCommitting changes...")
        db.session.commit()
        print("Done!")
    
    # Verify
    print("\nUnified table record counts:")
    unified_counts = count_unified_records()
    for mode, count in unified_counts.items():
        expected = legacy_counts[mode]
        status = "✓" if count == expected else f"⚠ Expected {expected}"
        print(f"  learning_progress (mode={mode}): {count} {status}")
    
    return results


def verify_migration():
    """Verify that migration was successful."""
    print("=" * 60)
    print("Migration Verification")
    print("=" * 60)
    
    legacy_counts = count_legacy_records()
    unified_counts = count_unified_records()
    
    all_match = True
    for mode in ['flashcard', 'quiz', 'memrise', 'course']:
        expected = legacy_counts[mode]
        actual = unified_counts[mode]
        status = "✓ MATCH" if actual == expected else f"✗ MISMATCH"
        if actual != expected:
            all_match = False
        print(f"  {mode}: legacy={expected}, unified={actual} {status}")
    
    return all_match


def create_table_if_not_exists():
    """Create learning_progress table if it doesn't exist."""
    # Check if table exists
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    if 'learning_progress' not in inspector.get_table_names():
        print("Creating learning_progress table...")
        LearningProgress.__table__.create(db.engine)
        print("Table created successfully.")
    else:
        print("learning_progress table already exists.")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate progress tables to unified model')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated')
    parser.add_argument('--verify-only', action='store_true', help='Only verify existing migration')
    args = parser.parse_args()
    
    app = create_app()
    
    with app.app_context():
        if args.verify_only:
            success = verify_migration()
            sys.exit(0 if success else 1)
        else:
            create_table_if_not_exists()
            run_migration(dry_run=args.dry_run)
