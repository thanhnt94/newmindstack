import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from mindstack_app import create_app
from mindstack_app.core.extensions import db
from mindstack_app.modules.learning_history.models import StudyLog
from sqlalchemy import text

def parse_datetime(dt_val):
    if isinstance(dt_val, datetime):
        return dt_val
    if isinstance(dt_val, str):
        try:
            # Handle formats like '2026-01-28 18:54:15.182280'
            if '.' in dt_val:
                return datetime.strptime(dt_val, '%Y-%m-%d %H:%M:%S.%f')
            else:
                return datetime.strptime(dt_val, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            print(f"Warning: Could not parse datetime string: {dt_val}")
            return datetime.utcnow()
    return datetime.utcnow()

def migrate_review_logs():
    app = create_app()
    with app.app_context():
        print("Starting migration from 'review_logs' to 'study_logs'...")
        
        # 1. Ensure StudyLog table exists
        db.create_all()
        print("Ensured 'study_logs' table exists.")
        
        # 2. Check if review_logs exists
        inspector = db.inspect(db.engine)
        if 'review_logs' not in inspector.get_table_names():
            print("Table 'review_logs' does not exist. Skipping migration.")
            return

        # 3. Fetch old logs
        query = text("SELECT * FROM review_logs ORDER BY timestamp ASC")
        result = db.session.execute(query)
        old_logs = result.fetchall()
        
        print(f"Found {len(old_logs)} records in 'review_logs'.")
        
        count = 0
        
        for row in old_logs:
            # Map Row to Dict for easier access
            # SQLAlchemy rows are accessible by column name or index
            
            # Construct Snapshots
            fsrs_snapshot = {
                'stability': getattr(row, 'fsrs_stability', 0.0),
                'difficulty': getattr(row, 'fsrs_difficulty', 0.0),
                'state': getattr(row, 'state', 0),
                'scheduled_days': getattr(row, 'scheduled_days', 0.0),
                'elapsed_days': getattr(row, 'elapsed_days', 0.0)
            }
            
            gamification_snapshot = {
                'score_change': getattr(row, 'score_change', 0),
                'streak_position': getattr(row, 'streak_position', 0)
            }
            
            # Determine Mode
            mode = getattr(row, 'review_type', None) or getattr(row, 'mode', 'flashcard')
            
            # Ensure timestamp is datetime object
            ts = parse_datetime(row.timestamp)
            
            new_log = StudyLog(
                user_id=row.user_id,
                item_id=row.item_id,
                timestamp=ts,
                
                rating=getattr(row, 'rating', 0),
                user_answer=getattr(row, 'user_answer', None),
                is_correct=getattr(row, 'is_correct', False),
                review_duration=getattr(row, 'review_duration', 0),
                
                session_id=getattr(row, 'session_id', None),
                container_id=getattr(row, 'container_id', None),
                learning_mode=mode,
                
                fsrs_snapshot=fsrs_snapshot,
                gamification_snapshot=gamification_snapshot
            )
            
            db.session.add(new_log)
            count += 1
            
            if count % 100 == 0:
                print(f"Processed {count} records...")
        
        db.session.commit()
        print(f"Migration complete. Migrated {count} records.")

if __name__ == '__main__':
    migrate_review_logs()