
import sys
import os
from datetime import datetime, timezone
from mindstack_app.modules.stats.services.vocabulary_stats_service import VocabularyStatsService
from mindstack_app.models import LearningItem, User

# Setup Flask context
from start_mindstack_app import create_app
app = create_app()

def verify_item_stats():
    with app.app_context(), app.test_request_context():
        # Find a suitable item and user
        item = LearningItem.query.first()
        if not item:
            print("No items found.")
            return

        user_id = item.container.creator_user_id
        if not user_id:
            user = User.query.first()
            if user:
                user_id = user.user_id
            else:
                print("No users found.")
                return

        print(f"Verifying stats for Item {item.item_id} (User {user_id})...")
        
        try:
            stats = VocabularyStatsService.get_item_stats(user_id, item.item_id)
            if not stats:
                print("Stats returned None.")
                return

            print("Stats Structure Found:", stats.keys())

            # Check Progress FSRS Stats
            if 'progress' in stats:
                p = stats['progress']
                print("\n[Progress FSRS Stats]")
                print(f"  fsrs_stability: {p.get('fsrs_stability')}")
                print(f"  fsrs_difficulty: {p.get('fsrs_difficulty')}")
                print(f"  fsrs_state: {p.get('fsrs_state')}")
                
                assert 'fsrs_stability' in p
                assert 'fsrs_difficulty' in p
                assert 'fsrs_state' in p
            else:
                print("FAIL: 'progress' key missing.")

            # Check History Snapshots
            if 'history' in stats:
                h = stats['history']
                print(f"\n[History] Found {len(h)} entries.")
                if h:
                    first_log = h[0]
                    print("  Sample Log Keys:", first_log.keys())
                    print(f"  fsrs_snapshot present: {'fsrs_snapshot' in first_log}")
                    
                    assert 'fsrs_snapshot' in first_log, "fsrs_snapshot missing from history log"
            else:
                print("FAIL: 'history' key missing.")

            print("\nVerification SUCCESS: API returns expected FSRS data structure.")

        except Exception as e:
            print(f"Verification FAILED with error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    verify_item_stats()
