from datetime import datetime, timezone
from mindstack_app.core.extensions import db
from ..models import Feedback

class FeedbackService:
    @staticmethod
    def resolve_feedback(feedback_id: int, admin_user_id: int):
        """Mark feedback as resolved."""
        feedback = Feedback.query.get(feedback_id)
        if feedback:
            feedback.status = 'RESOLVED'
            feedback.resolved_by_id = admin_user_id
            feedback.resolved_at = datetime.now(timezone.utc)
            db.session.commit()
            return True
        return False

    @staticmethod
    def close_feedback(feedback_id: int, admin_user_id: int):
        """Close feedback without resolving."""
        feedback = Feedback.query.get(feedback_id)
        if feedback:
            feedback.status = 'CLOSED'
            feedback.resolved_by_id = admin_user_id
            feedback.resolved_at = datetime.now(timezone.utc)
            db.session.commit()
            return True
        return False
