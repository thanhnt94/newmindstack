
import os
import sys
from flask import Flask

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mindstack_app import create_app
from mindstack_app.models import db, User, ScoreLog, LearningItem
from mindstack_app.modules.scoring.interface import ScoringInterface

def test_award_points():
    app = create_app()
    with app.app_context():
        # 1. Create a dummy user
        test_user = User.query.filter_by(username='test_scoring_user').first()
        if not test_user:
            test_user = User(username='test_scoring_user', email='test_scoring@example.com')
            test_user.set_password('password')
            db.session.add(test_user)
            db.session.commit()
            print(f"Created test user: {test_user.user_id}")
        else:
            print(f"Using existing test user: {test_user.user_id}")

        initial_score = test_user.total_score or 0
        print(f"Initial score: {initial_score}")

        # 2. Award points via interface
        amount = 12
        activity = 'VOCAB_MCQ_CORRECT_BONUS'
        success = ScoringInterface.award_points(
            user_id=test_user.user_id,
            activity_type=activity,
            amount=amount,
            item_id=None,
            item_type='mcq'
        )

        if not success:
            print("FAILED: ScoringInterface.award_points returned False")
            return

        # 3. Verify User Score
        db.session.refresh(test_user)
        new_score = test_user.total_score
        print(f"New score: {new_score}")
        
        if new_score != initial_score + amount:
            print(f"FAILED: Score mismatch. Expected {initial_score + amount}, got {new_score}")
        else:
            print("SUCCESS: User score updated correctly.")

        # 4. Verify ScoreLog
        log = ScoreLog.query.filter_by(user_id=test_user.user_id).order_by(ScoreLog.timestamp.desc()).first()
        if not log:
            print("FAILED: No ScoreLog found for test user.")
        elif log.score_change != amount:
            print(f"FAILED: ScoreLog amount mismatch. Expected {amount}, got {log.score_change}")
        elif log.reason != activity:
            print(f"FAILED: ScoreLog reason mismatch. Expected {activity}, got {log.reason}")
        else:
            print("SUCCESS: ScoreLog entry verified.")

if __name__ == '__main__':
    test_award_points()
