
from mindstack_app import create_app, db
from mindstack_app.models import LearningProgress

def cleanup_hard_items():
    app = create_app()
    with app.app_context():
        # Find all records with status='hard'
        hard_items = LearningProgress.query.filter_by(status='hard').all()
        
        count = len(hard_items)
        if count == 0:
            print("No items with status='hard' found. Database is clean.")
            return

        print(f"Found {count} items with status='hard'. Resetting to 'learning'...")
        
        for item in hard_items:
            # We reset to 'learning' but preserve other stats
            # This allows the SRS algorithm to naturally pick it up again
            item.status = 'learning'
            print(f" - Fixed Item {item.item_id} (User {item.user_id}, Mode {item.learning_mode})")
            
        try:
            db.session.commit()
            print("Successfully updated all records.")
        except Exception as e:
            db.session.rollback()
            print(f"Error saving changes: {e}")

if __name__ == "__main__":
    cleanup_hard_items()
