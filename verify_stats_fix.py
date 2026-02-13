# File: verify_stats_fix.py
import os
import sys
from datetime import datetime, timezone

# Add parent dir to path
sys.path.append(os.getcwd())

from mindstack_app import create_app
from mindstack_app.core.extensions import db
from mindstack_app.modules.fsrs.models import ItemMemoryState
from mindstack_app.modules.fsrs.schemas import CardStateDTO, CardStateEnum
from mindstack_app.modules.fsrs.engine.core import FSRSEngine
from mindstack_app.modules.vocabulary.flashcard.engine.core import FlashcardEngine

app = create_app()

def verify_retention():
    print("\n--- Verifying Robust Retention Calculation ---")
    engine = FSRSEngine()
    
    # Simulate user's case: stability=3.2, difficulty=5.3, state=REVIEW, repetitions=0
    # last_review might be some time ago
    last_review = datetime.now(timezone.utc)
    card = CardStateDTO(
        stability=3.2,
        difficulty=5.3,
        state=CardStateEnum.REVIEW,
        reps=0,
        last_review=last_review
    )
    
    retention = engine.get_realtime_retention(card, datetime.now(timezone.utc))
    print(f"Retention for REVIEW card with 0 reps: {retention*100:.1f}%")
    if retention > 0.9:
        print(" SUCCESS: Retention is non-zero and reasonable.")
    else:
        print(" FAILURE: Retention is still zero or too low.")

def verify_fallback_stats():
    print("\n--- Verifying Fallback Stats for Empty Logs ---")
    with app.app_context():
        # Create a mock record if not exists
        user_id = 1
        item_id = 999999 # Fake ID
        
        # Clean up existing fake data
        ItemMemoryState.query.filter_by(user_id=user_id, item_id=item_id).delete()
        
        # Create state with 0 reps but high state
        state = ItemMemoryState(
            user_id=user_id,
            item_id=item_id,
            stability=5.0,
            difficulty=3.0,
            state=2, # REVIEW
            repetitions=5, # Fallback should use this
            last_review=datetime.now(timezone.utc)
        )
        db.session.add(state)
        # We don't need StudyLogs for this test - we want to see fallback
        
        stats = FlashcardEngine.get_item_statistics(user_id, item_id)
        print(f"Times Reviewed: {stats.get('times_reviewed')}")
        print(f"Repetitions: {stats.get('repetitions')}")
        print(f"Retrievability: {stats.get('retrievability')}%")
        
        if stats.get('times_reviewed') == 5:
            print(" SUCCESS: Fallback used repetitions for times_reviewed.")
        else:
            print(" FAILURE: Fallback did not work.")

if __name__ == "__main__":
    verify_retention()
    verify_fallback_stats()
