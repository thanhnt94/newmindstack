from mindstack_app.models import LearningSession, db, User, LearningContainer, LearningItem
from mindstack_app.modules.learning.sub_modules.flashcard.services.session_service import LearningSessionService
from mindstack_app.modules.learning.sub_modules.flashcard.engine import FlashcardSessionManager

def login_client(client, user_id):
    with client.session_transaction() as session:
        session['_user_id'] = str(user_id)
        session['_fresh'] = True

def test_create_and_resume_session(app, client):
    """Test creating a session and then resuming it from the DB."""
    with app.app_context():
        # 1. Setup User and Data
        user = User(username='testuser', email='test@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        user_id = user.user_id
        
        container = LearningContainer(creator_user_id=user_id, container_type='FLASHCARD_SET', title='Test Set')
        db.session.add(container)
        db.session.commit()
        set_id = container.container_id
        
        item = LearningItem(container_id=set_id, item_type='FLASHCARD', content={'front': 'F', 'back': 'B'}, order_in_container=1)
        db.session.add(item)
        db.session.commit()
        item_id = item.item_id

        # 2. Login
        login_client(client, user_id)
        
        # 3. Create a session via Manager
        from flask_login import login_user
        with app.test_request_context():
            login_user(user)
            success, message = FlashcardSessionManager.start_new_flashcard_session(set_id, 'new_only')
            assert success is True, message
            
            active_session = LearningSessionService.get_active_session(user_id, learning_mode='flashcard')
            assert active_session is not None
            session_id = active_session.session_id
            
            # Simulate answering
            LearningSessionService.update_progress(session_id, item_id, 'correct', points=10)
            
        # 4. Resume via API route
        # Clear session to force DB resume
        with client.session_transaction() as sess:
            sess.pop('flashcard_session', None)
            
        response = client.get('/learn/vocabulary/flashcard/session')
        assert response.status_code == 200
        
        # Verify Flask session is restored
        with client.session_transaction() as sess:
            assert 'flashcard_session' in sess
            assert sess['flashcard_session']['db_session_id'] == session_id
            
        # 5. End session
        LearningSessionService.complete_session(session_id)
        final_session = db.session.get(LearningSession, session_id)
        assert final_session.status == 'completed'

def test_cancel_old_sessions(app):
    """Test that starting a new session cancels the old one."""
    with app.app_context():
        user = User(username='testuser2', email='test2@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        user_id = user.user_id
        
        # Create first session
        LearningSessionService.create_session(user_id, 'flashcard', 'new_only', 1)
        active1 = LearningSessionService.get_active_session(user_id, 'flashcard')
        assert active1 is not None
        
        # Create second session
        LearningSessionService.create_session(user_id, 'flashcard', 'due_only', 2)
        
        # First one should be cancelled
        db.session.refresh(active1)
        assert active1.status == 'cancelled'
        
        # Second one should be active
        active2 = LearningSessionService.get_active_session(user_id, 'flashcard')
        assert active2.mode_config_id == 'due_only'
