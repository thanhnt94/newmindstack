
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mindstack_app import create_app
from mindstack_app.models import db, User, LearningSession, LearningItem
from mindstack_app.modules.vocab_flashcard.engine.session_manager import FlashcardSessionManager
from mindstack_app.modules.session.interface import SessionInterface

app = create_app()

def test_resume():
    with app.app_context():
        # Setup: Find a user and a set
        user = User.query.first()
        if not user:
            print("No user found.")
            return

        # Find or create a flashcard set
        item = LearningItem.query.filter_by(item_type='FLASHCARD').first()
        if not item:
            print("No flashcard items found.")
            return
        
        set_id = item.container_id
        
        print(f"Testing with User: {user.username}, Set: {set_id}")

        # 1. Start a new session
        from flask import session
        with app.test_request_context():
            from flask_login import login_user
            login_user(user)
            
            success, msg, session_id = FlashcardSessionManager.start_new_flashcard_session(set_id, 'mixed_srs', session_size=10)
            if not success:
                print(f"Failed to start session: {msg}")
                return
            
            manager = FlashcardSessionManager.from_dict(session['flashcard_session'])
            
            # 2. Get first card
            batch = manager.get_next_batch(1)
            first_item_id = batch['items'][0]['item_id']
            print(f"First card fetched: {first_item_id}")
            
            # Verify it's in DB
            db_sess = SessionInterface.get_session_by_id(session_id)
            print(f"DB Current Item: {db_sess.current_item_id}")
            if db_sess.current_item_id != first_item_id:
                print("FAIL: DB current_item_id does not match fetched item.")
                return

            # 3. Simulate Resume (e.g. on another device/reload)
            # Reconstruct from DB
            manager_reloaded = FlashcardSessionManager.from_db_session(db_sess)
            print(f"Reloaded manager processed count: {len(manager_reloaded.processed_item_ids)}")
            print(f"Reloaded manager current item: {manager_reloaded.current_item_id}")

            # 4. Get next batch on reloaded manager
            batch_resume = manager_reloaded.get_next_batch(1)
            resume_item_id = batch_resume['items'][0]['item_id']
            print(f"Resumed card fetched: {resume_item_id}")

            if resume_item_id == first_item_id:
                print("SUCCESS: Resumed session shows the same card.")
            else:
                print(f"FAIL: Resumed session shows card {resume_item_id} instead of {first_item_id}.")

            # 5. Answer the card
            manager_reloaded.process_flashcard_answer(resume_item_id, 3) # Good
            print(f"Card {resume_item_id} answered.")
            
            # Check DB
            db_sess_after = SessionInterface.get_session_by_id(session_id)
            print(f"DB processed IDs: {db_sess_after.processed_item_ids}")
            print(f"DB Current Item after answer: {db_sess_after.current_item_id}")
            
            if db_sess_after.current_item_id is not None:
                print("FAIL: DB current_item_id was not cleared after answer.")
                return
            
            if resume_item_id not in db_sess_after.processed_item_ids:
                print("FAIL: Item not added to processed list in DB.")
                return

            # 6. Get next card
            batch_next = manager_reloaded.get_next_batch(1)
            next_item_id = batch_next['items'][0]['item_id']
            print(f"Next card fetched: {next_item_id}")
            
            if next_item_id == first_item_id:
                print("FAIL: Fetched the same card again after answering.")
            else:
                print("SUCCESS: Next card is different.")

if __name__ == "__main__":
    test_resume()
