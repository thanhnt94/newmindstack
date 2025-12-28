from mindstack_app import create_app, db
from mindstack_app.models import LearningItem, ReviewLog, LearningProgress, User
from mindstack_app.modules.learning.sub_modules.vocabulary.stats.item_stats import VocabularyItemStats

app = create_app()

with app.app_context():
    print("Testing VocabularyItemStats...")
    
    # 1. Find a user and an item with logs
    log = ReviewLog.query.order_by(ReviewLog.timestamp.desc()).first()
    
    if not log:
        print("No logs found to test with.")
        exit()
        
    user_id = log.user_id
    item_id = log.item_id
    
    print(f"Testing for User {user_id} and Item {item_id}")
    
    # 2. Get Stats
    stats = VocabularyItemStats.get_item_stats(user_id, item_id)
    
    if not stats:
        print("Stats returned None.")
    else:
        print("\n--- ITEM SUMMARY ---")
        print(f"Front: {stats['item']['front']}")
        print(f"Back: {stats['item']['back']}")
        
        print("\n--- PROGRESS ---")
        p = stats['progress']
        print(f"Status: {p['status']}")
        print(f"Mastery: {p['mastery']}%")
        print(f"Streak: {p['streak']}")
        print(f"Ease: {p['ease_factor']}")
        
        print("\n--- PERFORMANCE ---")
        perf = stats['performance']
        print(f"Total Reviews: {perf['total_reviews']}")
        print(f"Accuracy: {perf['accuracy']}%")
        print(f"Total Time: {perf['total_time_ms']}ms")
        print(f"Avg Time: {perf['avg_time_ms']}ms")
        
        print("\n--- MODES ---")
        for mode, data in stats['modes'].items():
            print(f"{mode}: {data['count']} reviews ({data['correct']} correct)")
            
        print("\n--- HISTORY (Last 3) ---")
        for log in stats['history'][:3]:
            print(f"[{log['timestamp']}] {log['mode']} - {log['result']} - Ans: {log['user_answer']}")
            
    print("\nTest Complete.")

