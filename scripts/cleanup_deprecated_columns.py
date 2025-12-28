"""
Schema Cleanup Script - Deprecated Columns
============================================

This script documents deprecated columns that SHOULD be removed once
the UserSession table is confirmed working in production.

SQLite does not support DROP COLUMN directly, so a full table rebuild
is required. This is a HIGH-RISK operation.

DEPRECATED COLUMNS IN `users` TABLE:
- current_flashcard_container_id  (moved to user_sessions)
- current_quiz_container_id       (moved to user_sessions)
- current_course_container_id     (moved to user_sessions)
- current_flashcard_mode          (moved to user_sessions)
- current_quiz_mode               (moved to user_sessions)
- current_quiz_batch_size         (moved to user_sessions)
- flashcard_button_count          (moved to user_sessions)

INSTRUCTIONS:
    1. Verify all features work with UserSession table
    2. Create full database backup
    3. Run this script with --execute flag
    4. Test application thoroughly
    5. Keep backup for 2 weeks

Usage:
    python scripts/cleanup_deprecated_columns.py --verify
    python scripts/cleanup_deprecated_columns.py --execute
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from mindstack_app import create_app
from mindstack_app.models import db


DEPRECATED_USER_COLUMNS = [
    'current_flashcard_container_id',
    'current_quiz_container_id',
    'current_course_container_id',
    'current_flashcard_mode',
    'current_quiz_mode',
    'current_quiz_batch_size',
    'flashcard_button_count',
]


def verify_user_sessions():
    """Check if UserSession table has data."""
    from mindstack_app.models import UserSession, User
    
    user_count = User.query.count()
    session_count = UserSession.query.count()
    
    print(f"Users: {user_count}")
    print(f"UserSessions: {session_count}")
    
    if session_count < user_count:
        print(f"\n⚠️  WARNING: Only {session_count}/{user_count} users have session records!")
        print("Some users may not have migrated to UserSession table yet.")
        return False
    
    print("\n✓ All users have UserSession records")
    return True


def check_deprecated_column_usage():
    """Check if deprecated columns have any non-null data."""
    connection = db.engine.connect()
    
    print("\nChecking deprecated column data:")
    
    for col in DEPRECATED_USER_COLUMNS:
        try:
            result = connection.execute(
                text(f"SELECT COUNT(*) FROM users WHERE {col} IS NOT NULL")
            )
            count = result.scalar()
            status = "✓ empty" if count == 0 else f"⚠️ {count} non-null values"
            print(f"  {col}: {status}")
        except Exception as e:
            print(f"  {col}: ERROR - {e}")
    
    connection.close()


def show_migration_sql():
    """Show the SQL needed to remove deprecated columns."""
    print("\n" + "=" * 60)
    print("SQL TO REMOVE DEPRECATED COLUMNS")
    print("=" * 60)
    print("""
-- SQLite does not support DROP COLUMN directly
-- Must recreate table without deprecated columns

-- Step 1: Create new table without deprecated columns
CREATE TABLE users_new (
    user_id INTEGER PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    user_role VARCHAR(50) NOT NULL DEFAULT 'free',
    total_score INTEGER DEFAULT 0,
    last_seen DATETIME,
    telegram_chat_id VARCHAR(100) UNIQUE,
    timezone VARCHAR(50) DEFAULT 'UTC',
    last_preferences TEXT DEFAULT '{}'
);

-- Step 2: Copy data
INSERT INTO users_new 
SELECT user_id, username, email, password_hash, user_role, 
       total_score, last_seen, telegram_chat_id, timezone, last_preferences
FROM users;

-- Step 3: Drop old table
DROP TABLE users;

-- Step 4: Rename new table
ALTER TABLE users_new RENAME TO users;

-- Step 5: Recreate indexes
CREATE UNIQUE INDEX ix_users_username ON users(username);
CREATE UNIQUE INDEX ix_users_email ON users(email);
""")


def run_verification():
    """Run all verification checks."""
    print("=" * 60)
    print("Schema Cleanup - Verification")
    print("=" * 60)
    
    verify_user_sessions()
    check_deprecated_column_usage()
    show_migration_sql()
    
    print("\n" + "=" * 60)
    print("RECOMMENDATION")
    print("=" * 60)
    print("""
The deprecated columns can be safely removed IF:
1. All users have UserSession records
2. The application has been tested with UserSession for at least 2 weeks
3. No production errors related to session state

To proceed with removal:
1. Create full database backup
2. Run the SQL commands shown above manually
3. Update User model to remove deprecated column definitions
""")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Schema cleanup for deprecated columns')
    parser.add_argument('--verify', action='store_true', help='Run verification checks')
    parser.add_argument('--execute', action='store_true', help='Execute cleanup (NOT IMPLEMENTED)')
    args = parser.parse_args()
    
    app = create_app()
    
    with app.app_context():
        if args.execute:
            print("⚠️  EXECUTE mode is disabled for safety.")
            print("Run the SQL manually after creating a backup.")
            print("\nRun with --verify first to see the SQL.")
        else:
            run_verification()
