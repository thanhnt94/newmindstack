
import os
import sys

sys.path.append(os.getcwd())

from mindstack_app import create_app
from mindstack_app.models import db, User, LearningItem, LearningSession
from mindstack_app.modules.vocabulary.flashcard.engine.core import FlashcardEngine

app = create_app()
with app.app_context():
    user = User.query.get(1)
    item = LearningItem.query.filter_by(item_type='FLASHCARD').first()
    session_id = "88" # STRING
    
    if not item:
        print("No flashcard item found")
        exit()
        
    print(f"Simulating answer for User 1, Item {item.item_id}, Session {session_id} (STRING)")
    FlashcardEngine.process_answer(
        user_id=user.user_id,
        item_id=item.item_id,
        quality=3,
        current_user_total_score=user.total_score,
        session_id=session_id,
        update_srs=True,
        learning_mode='flashcard'
    )
    print("Simulation finished")
