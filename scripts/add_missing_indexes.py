"""
Database Index Migration Script
================================

Adds missing indexes to improve query performance for:
- SRS queries (due items, status filtering)
- Analytics queries (review logs, score logs)
- Content queries (learning items ordering)

Usage:
    python scripts/add_missing_indexes.py [--dry-run]
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from mindstack_app import create_app
from mindstack_app.models import db


# Define indexes to add
INDEXES_TO_ADD = [
    # SRS Performance - FlashcardProgress (legacy table)
    {
        'name': 'ix_flashcard_progress_user_due',
        'table': 'flashcard_progress',
        'columns': ['user_id', 'due_time'],
        'description': 'Optimizes SRS due item queries'
    },
    {
        'name': 'ix_flashcard_progress_user_status',
        'table': 'flashcard_progress',
        'columns': ['user_id', 'status'],
        'description': 'Optimizes status filtering'
    },
    
    # SRS Performance - QuizProgress (legacy table)
    {
        'name': 'ix_quiz_progress_user_status',
        'table': 'quiz_progress',
        'columns': ['user_id', 'status'],
        'description': 'Optimizes quiz status queries'
    },
    
    # Analytics - ReviewLog
    {
        'name': 'ix_review_logs_user_time',
        'table': 'review_logs',
        'columns': ['user_id', 'timestamp'],
        'description': 'Optimizes review history lookups'
    },
    {
        'name': 'ix_review_logs_item_time',
        'table': 'review_logs',
        'columns': ['item_id', 'timestamp'],
        'description': 'Optimizes item-specific history'
    },
    
    # Analytics - ScoreLog
    {
        'name': 'ix_score_logs_user_time',
        'table': 'score_logs',
        'columns': ['user_id', 'timestamp'],
        'description': 'Optimizes score history and leaderboards'
    },
    
    # Content - LearningItems
    {
        'name': 'ix_learning_items_container_order',
        'table': 'learning_items',
        'columns': ['container_id', 'order_in_container'],
        'description': 'Optimizes sorted item listing'
    },
    {
        'name': 'ix_learning_items_container_type',
        'table': 'learning_items',
        'columns': ['container_id', 'item_type'],
        'description': 'Optimizes type-filtered queries'
    },
    
    # Goals
    {
        'name': 'ix_goal_daily_history_goal_date',
        'table': 'goal_daily_history',
        'columns': ['goal_id', 'date'],
        'description': 'Optimizes goal progress lookups'
    },
    
    # User Container States (Dashboard)
    {
        'name': 'ix_user_container_states_user_access',
        'table': 'user_container_states',
        'columns': ['user_id', 'is_archived', 'last_accessed'],
        'description': 'Optimizes dashboard container queries'
    },
    
    # Containers (Creator lookup)
    {
        'name': 'ix_learning_containers_creator_public',
        'table': 'learning_containers',
        'columns': ['creator_user_id', 'is_public'],
        'description': 'Optimizes user container listing'
    },
    
    # Collaborative Flashcard Rooms (Public discovery)
    {
        'name': 'ix_flashcard_collab_rooms_status_public',
        'table': 'flashcard_collab_rooms',
        'columns': ['status', 'is_public'],
        'description': 'Optimizes public room discovery'
    },
    
    # Quiz Battle Rooms (Public discovery)
    {
        'name': 'ix_quiz_battle_rooms_status_public',
        'table': 'quiz_battle_rooms',
        'columns': ['status', 'is_public'],
        'description': 'Optimizes public battle room discovery'
    },
    
    # User Badges
    {
        'name': 'ix_user_badges_user_id',
        'table': 'user_badges',
        'columns': ['user_id'],
        'description': 'Optimizes user badge listing'
    },
    
    # Learning Progress (Item lookup)
    {
        'name': 'ix_learning_progress_item_mode',
        'table': 'learning_progress',
        'columns': ['item_id', 'learning_mode'],
        'description': 'Optimizes item statistics lookup'
    },
]


def get_existing_indexes(connection):
    """Get list of existing index names."""
    result = connection.execute(
        text("SELECT name FROM sqlite_master WHERE type='index'")
    )
    return {row[0] for row in result}


def create_index_sql(index_def):
    """Generate CREATE INDEX SQL statement."""
    columns = ', '.join(index_def['columns'])
    return f"CREATE INDEX IF NOT EXISTS {index_def['name']} ON {index_def['table']} ({columns})"


def run_migration(dry_run=False):
    """Add missing indexes."""
    print("=" * 60)
    print("Database Index Migration")
    print("=" * 60)
    
    if dry_run:
        print(">>> DRY RUN MODE - No changes will be made <<<\n")
    
    connection = db.engine.connect()
    existing = get_existing_indexes(connection)
    
    print(f"Found {len(existing)} existing indexes\n")
    
    added = 0
    skipped = 0
    
    for index_def in INDEXES_TO_ADD:
        name = index_def['name']
        
        if name in existing:
            print(f"  [SKIP] {name} - already exists")
            skipped += 1
            continue
        
        sql = create_index_sql(index_def)
        print(f"  [ADD]  {name}")
        print(f"         {index_def['description']}")
        print(f"         SQL: {sql}")
        
        if not dry_run:
            try:
                connection.execute(text(sql))
                connection.commit()
                added += 1
            except Exception as e:
                print(f"         ERROR: {e}")
        else:
            added += 1
        
        print()
    
    print("-" * 60)
    print(f"Summary: {added} indexes added, {skipped} skipped")
    
    if not dry_run:
        print("\nIndexes committed to database.")
    
    connection.close()
    return added, skipped


def verify_indexes():
    """List all indexes for relevant tables."""
    print("=" * 60)
    print("Current Index Status")
    print("=" * 60)
    
    connection = db.engine.connect()
    
    tables = [
        'flashcard_progress', 'quiz_progress', 'learning_progress',
        'review_logs', 'score_logs', 'learning_items', 'goal_daily_history'
    ]
    
    for table in tables:
        result = connection.execute(
            text(f"SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='{table}'")
        )
        indexes = [row[0] for row in result]
        print(f"\n{table}:")
        if indexes:
            for idx in indexes:
                print(f"  - {idx}")
        else:
            print("  (no indexes)")
    
    connection.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Add missing database indexes')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be added')
    parser.add_argument('--verify', action='store_true', help='List current indexes')
    args = parser.parse_args()
    
    app = create_app()
    
    with app.app_context():
        if args.verify:
            verify_indexes()
        else:
            run_migration(dry_run=args.dry_run)
