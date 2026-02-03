from datetime import datetime, timezone
from flask import current_app
from mindstack_app.models import db, LearningSession, User
from mindstack_app.utils.db_session import safe_commit

class LearningSessionService:
    """
    Service layer for managing database-backed learning sessions.
    Follows 3-Layer Architecture (Layer 2: DB + Orchestration).
    """

    @staticmethod
    def create_session(user_id, learning_mode, mode_config_id, set_id_data, total_items=0):
        """Create a new session in the database."""
        try:
            # [UPDATED] Enforce Single Active Mode Policy for Vocabulary
            # A user can only have ONE active vocabulary session per set at a time.
            # (e.g. Cannot have Flashcard AND MCQ active for Set A simultaneously)
            VOCABULARY_MODES = ['flashcard', 'mcq', 'typing', 'listening', 'matching']
            
            if learning_mode in VOCABULARY_MODES:
                # Cancel ALL active vocabulary sessions for this set
                LearningSessionService.cancel_active_sessions(
                    user_id=user_id, 
                    learning_mode=VOCABULARY_MODES, # Pass the list to cancel any of them
                    set_id_data=set_id_data
                )
            else:
                # Default behavior for non-vocab modes (e.g. Quiz) -> Just cancel same mode
                LearningSessionService.cancel_active_sessions(
                    user_id=user_id, 
                    learning_mode=learning_mode, 
                    set_id_data=set_id_data
                )
            # OLD: LearningSessionService.cancel_active_sessions(user_id, learning_mode, set_id_data)

            new_session = LearningSession(
                user_id=user_id,
                learning_mode=learning_mode,
                mode_config_id=mode_config_id,
                set_id_data=set_id_data,
                total_items=total_items,
                status='active',
                processed_item_ids=[]
            )
            db.session.add(new_session)
            safe_commit(db.session)
            return new_session
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating learning session: {e}", exc_info=True)
            return None

    @staticmethod
    def get_active_sessions(user_id, learning_mode=None):
        """Get all active sessions for a user."""
        query = LearningSession.query.filter_by(user_id=user_id, status='active')
        if learning_mode:
            query = query.filter_by(learning_mode=learning_mode)
        return query.order_by(LearningSession.start_time.desc()).all()

    @staticmethod
    def get_active_session(user_id, learning_mode=None, set_id_data=None):
        """Get the most recent active session for a user."""
        query = LearningSession.query.filter_by(user_id=user_id, status='active')
        if learning_mode:
            query = query.filter_by(learning_mode=learning_mode)
        
        # [UPDATED] Filter by set_id if provided
        if set_id_data is not None:
            # Note: exact match on JSON column can be tricky, but for simple int/list it works in SQLAlchemy
            # if the driver supports it. For now assuming set_id_data is int/simple.
            # Ideally we check existence.
            if isinstance(set_id_data, int):
                 # For postgres/sqlite json search is specific, assuming exact match for now
                 # or using simple equality if the DB stores it as simple value (it's JSON type)
                 # We will rely on Python filtering if DB query is complex, 
                 # BUT for now let's assume exact match works for the creation/retrieval parity.
                 query = query.filter(LearningSession.set_id_data == set_id_data)
        
        return query.order_by(LearningSession.start_time.desc()).first()

    @staticmethod
    def get_any_active_vocabulary_session(user_id, set_id_data):
        """Get ANY active session within the vocabulary group for a specific set."""
        # Include all relevant modes
        VOCABULARY_MODES = ['flashcard', 'mcq', 'typing', 'listening', 'matching', 'speed']
        
        # 1. Fetch ALL active sessions for this user (robust against JSON query limitations)
        candidates = LearningSession.query.filter_by(user_id=user_id, status='active').all()
        
        target_str = str(set_id_data)
        
        # 2. Filter in Python to handle JSON type variances (int vs str vs list)
        valid_sessions = []
        for sess in candidates:
            if sess.learning_mode not in VOCABULARY_MODES:
                continue
                
            stored = sess.set_id_data
            
            # Direct match (handling string/int diff)
            if str(stored) == target_str:
                valid_sessions.append(sess)
                continue
                
            # Legacy list support (some old sessions might store [id])
            if isinstance(stored, list) and len(stored) > 0 and str(stored[0]) == target_str:
                valid_sessions.append(sess)
                continue
        
        # Return the most recent one
        if valid_sessions:
            valid_sessions.sort(key=lambda x: x.start_time, reverse=True)
            return valid_sessions[0]
            
        return None

    @staticmethod
    def update_progress(session_id, item_id, result_type, points=0):
        """Update session progress and stats."""
        try:
            session = db.session.get(LearningSession, session_id)
            if not session or session.status != 'active':
                return False

            processed_ids = list(session.processed_item_ids or [])
            if item_id not in processed_ids:
                processed_ids.append(item_id)
                session.processed_item_ids = processed_ids

                if result_type == 'correct':
                    session.correct_count += 1
                elif result_type == 'incorrect':
                    session.incorrect_count += 1
                elif result_type == 'vague':
                    session.vague_count += 1
                
                if points > 0:
                    session.points_earned += points

                # [NEW] Clear current_item_id if it matched the finished item
                if session.current_item_id == item_id:
                    session.current_item_id = None

                db.session.add(session)
                safe_commit(db.session)
                return True
            return False
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating session progress: {e}", exc_info=True)
            return False

    @staticmethod
    def complete_session(session_id):
        """Mark a session as completed."""
        try:
            session = db.session.get(LearningSession, session_id)
            if session:
                session.status = 'completed'
                session.end_time = datetime.now(timezone.utc)
                db.session.add(session)
                safe_commit(db.session)
                return True
            return False
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error completing session: {e}", exc_info=True)
            return False

    @staticmethod
    def cancel_session(session_id):
        """
        Cancel a specific session by ID.
        Used for administrative cleanup or manual session termination.
        """
        try:
            session = db.session.get(LearningSession, session_id)
            if session and session.status == 'active':
                session.status = 'cancelled'
                session.end_time = datetime.now(timezone.utc)
                session.current_item_id = None
                db.session.add(session)
                safe_commit(db.session)
                return True
            return False
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error cancelling session {session_id}: {e}", exc_info=True)
            return False

    @staticmethod
    def cancel_active_sessions(user_id, learning_mode, set_id_data=None):
        """
        Cancel active sessions.
        learning_mode: Can be a single string 'flashcard' OR a list ['flashcard', 'mcq']
        """
        try:
            query = LearningSession.query.filter_by(
                user_id=user_id, 
                status='active'
            )
            
            # [UPDATED] Handle list of modes (IN clause) or single mode (Equal)
            if isinstance(learning_mode, list):
                query = query.filter(LearningSession.learning_mode.in_(learning_mode))
            else:
                query = query.filter(LearningSession.learning_mode == learning_mode)
            
            if set_id_data is not None:
                query = query.filter(LearningSession.set_id_data == set_id_data)
                
            active_sessions = query.all()
            
            for session in active_sessions:
                session.status = 'cancelled'
                session.end_time = datetime.now(timezone.utc)
                db.session.add(session)
            
            if active_sessions:
                safe_commit(db.session)
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error cancelling active sessions: {e}", exc_info=True)
            return False

    @staticmethod
    def get_session_by_id(session_id):
        return db.session.get(LearningSession, session_id)

    @staticmethod
    def get_session_history(user_id, limit=50):
        """Get completed or cancelled sessions for a user."""
        return LearningSession.query.filter(
            LearningSession.user_id == user_id,
            LearningSession.status.in_(['completed', 'cancelled'])
        ).order_by(LearningSession.end_time.desc()).limit(limit).all()

    @staticmethod
    def set_current_item(session_id, item_id):
        """Update the active item for a session (for persistence)."""
        try:
            session = db.session.get(LearningSession, session_id)
            if session and session.status == 'active':
                session.current_item_id = item_id
                db.session.add(session)
                safe_commit(db.session)
                return True
            return False
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error setting current item in session: {e}", exc_info=True)
            return False
