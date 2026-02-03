
import os
import sys
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mindstack_app import create_app
from mindstack_app.models import db, User, LearningItem, ItemMemoryState
from mindstack_app.modules.vocab_flashcard.engine.services.query_builder import FlashcardQueryBuilder

app = create_app()

def test_anki_selection():
    with app.app_context():
        user = User.query.first()
        if not user:
            print("No user found.")
            return

        # 1. Clear existing progress for this test user to have a clean slate
        # (Be careful on production, but this is a dev/test environment)
        # ItemMemoryState.query.filter_by(user_id=user.user_id).delete()
        # db.session.commit()

        # 2. Setup test items
        # We need at least 5 items in a set
        items = LearningItem.query.filter_by(item_type='FLASHCARD').limit(10).all()
        if len(items) < 5:
            print("Not enough items for test.")
            return
        
        # Mark 2 cards as DUE (R < 90%)
        # Mark 3 cards as NEW
        
        now = datetime.now(timezone.utc)
        
        # Set 1 & 2 as Due
        for i in range(2):
            item_id = items[i].item_id
            state = ItemMemoryState.query.filter_by(user_id=user.user_id, item_id=item_id).first()
            if not state:
                state = ItemMemoryState(user_id=user.user_id, item_id=item_id)
            state.state = 2 # Review
            state.due_date = now - timedelta(days=1) # Overdue
            db.session.add(state)
        
        # Set 3, 4, 5 as New (ensure no record or state=0)
        for i in range(2, 5):
            item_id = items[i].item_id
            state = ItemMemoryState.query.filter_by(user_id=user.user_id, item_id=item_id).first()
            if state:
                state.state = 0
                state.due_date = None
                db.session.add(state)
        
        db.session.commit()
        
        print("Setup complete: Items 0,1 are DUE. Items 2,3,4 are NEW.")

        # 3. Run Query
        qb = FlashcardQueryBuilder(user.user_id)
        qb.filter_by_containers([items[0].container_id])
        qb.filter_mixed()
        
        results = qb.get_query().limit(10).all()
        
        print(f"Query returned {len(results)} items.")
        
        # 4. Verify Priority
        # First 2 should be the Due ones (0 or 1)
        due_ids = [items[0].item_id, items[1].item_id]
        new_ids = [items[2].item_id, items[3].item_id, items[4].item_id]
        
        first_two = [r.item_id for r in results[:2]]
        print(f"First two items: {first_two}")
        
        if all(id in due_ids for id in first_two):
            print("SUCCESS: Due cards appear first.")
        else:
            print("FAIL: Due cards are not prioritized.")

        # 5. Verify Sequential for New
        # Next 3 should be New cards in order
        next_three = [r.item_id for r in results[2:5]]
        print(f"Next three items: {next_three}")
        
        # Check if they follow order_in_container
        # We assume items[2,3,4] are in order in the DB fetch
        expected_new_order = sorted(new_ids, key=lambda x: LearningItem.query.get(x).order_in_container)
        
        if next_three == expected_new_order:
            print("SUCCESS: New cards follow sequential order.")
        else:
            print(f"FAIL: New cards order mismatch. Expected {expected_new_order}, got {next_three}")

if __name__ == "__main__":
    test_anki_selection()
