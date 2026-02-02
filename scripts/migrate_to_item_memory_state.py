
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from mindstack_app import create_app
from mindstack_app.core.extensions import db
from mindstack_app.modules.fsrs.models import ItemMemoryState
from sqlalchemy import text, inspect

def migrate_learning_progress():
    app = create_app()
    with app.app_context():
        print("Starting migration from 'learning_progress' to 'item_memory_states'...")
        
        # 1. Ensure ItemMemoryState table exists
        db.create_all()
        print("Ensured 'item_memory_states' table exists.")
        
        inspector = inspect(db.engine)
        if 'learning_progress' not in inspector.get_table_names():
            print("Table 'learning_progress' does not exist. Skipping data migration.")
            return

        # 2. Fetch old progress records
        # Using raw SQL because LearningProgress model is deleted
        query = text("SELECT * FROM learning_progress")
        try:
            result = db.session.execute(query)
            old_progress = result.fetchall()
        except Exception as e:
            print(f"Error fetching learning_progress: {e}")
            return
        
        print(f"Found {len(old_progress)} records in 'learning_progress'.")
        
        count = 0
        skipped = 0
        
        for row in old_progress:
            user_id = row.user_id
            item_id = row.item_id
            
            # Check if state already exists (Unified Memory: one state per item per user)
            existing = ItemMemoryState.query.filter_by(user_id=user_id, item_id=item_id).first()
            
            if existing:
                # Merge logic? Or skip?
                # If we have multiple modes (flashcard, quiz) for same item, we need to decide.
                # Priority: Flashcard > Quiz > Others?
                # Or just merge counts.
                # Let's simple merge: Max stability, sum counts.
                existing.repetitions = max(existing.repetitions, getattr(row, 'repetitions', 0))
                existing.lapses += getattr(row, 'lapses', 0)
                existing.times_correct += getattr(row, 'times_correct', 0)
                existing.times_incorrect += getattr(row, 'times_incorrect', 0)
                
                # Update data json
                if row.mode_data:
                    try:
                        old_data = json.loads(row.mode_data) if isinstance(row.mode_data, str) else row.mode_data
                        if not existing.data: existing.data = {}
                        existing.data.update(old_data)
                    except: pass
                
                # Flag modified
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(existing, 'data')
                
                skipped += 1
                continue

            # Create new state
            fsrs_state = getattr(row, 'fsrs_state', 0)
            stability = getattr(row, 'fsrs_stability', 0.0)
            difficulty = getattr(row, 'fsrs_difficulty', 0.0)
            
            # Handle timestamps
            created_at = row.first_seen if hasattr(row, 'first_seen') else datetime.utcnow()
            if isinstance(created_at, str):
                try: created_at = datetime.fromisoformat(created_at)
                except: created_at = datetime.utcnow()
                
            last_review = row.fsrs_last_review if hasattr(row, 'fsrs_last_review') else None
            if isinstance(last_review, str):
                try: last_review = datetime.fromisoformat(last_review)
                except: last_review = None
                
            due_date = row.fsrs_due if hasattr(row, 'fsrs_due') else None
            if isinstance(due_date, str):
                try: due_date = datetime.fromisoformat(due_date)
                except: due_date = None

            # Mode data
            mode_data = {}
            if hasattr(row, 'mode_data') and row.mode_data:
                try:
                    mode_data = json.loads(row.mode_data) if isinstance(row.mode_data, str) else row.mode_data
                except: pass

            new_state = ItemMemoryState(
                user_id=user_id,
                item_id=item_id,
                state=fsrs_state,
                stability=stability,
                difficulty=difficulty,
                due_date=due_date,
                last_review=last_review,
                repetitions=getattr(row, 'repetitions', 0),
                lapses=getattr(row, 'lapses', 0),
                streak=getattr(row, 'correct_streak', 0),
                times_correct=getattr(row, 'times_correct', 0),
                times_incorrect=getattr(row, 'times_incorrect', 0),
                created_at=created_at,
                data=mode_data
            )
            
            db.session.add(new_state)
            count += 1
            
            if count % 100 == 0:
                print(f"Processed {count} records...")
        
        db.session.commit()
        print(f"Migration complete. Created {count} new states. Merged/Skipped {skipped}.")

if __name__ == '__main__':
    migrate_learning_progress()
