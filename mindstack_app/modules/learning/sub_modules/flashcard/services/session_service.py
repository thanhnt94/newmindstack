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
            # Cancel any existing active sessions of the same mode AND set for this user
            # [UPDATED] Scoped to set_id to allow multiple active sessions for different sets
            LearningSessionService.cancel_active_sessions(user_id, learning_mode, set_id_data)

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
    def cancel_active_sessions(user_id, learning_mode, set_id_data=None):
        """Cancel all active sessions for a user, mode, and optionally set."""
        try:
            query = LearningSession.query.filter_by(
                user_id=user_id, 
                learning_mode=learning_mode, 
                status='active'
            )
            
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
