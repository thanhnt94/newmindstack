from typing import Optional, List, Dict, Any
from .schemas import FeedbackDTO
from .models import Feedback
from mindstack_app.core.extensions import db

def submit_feedback(user_id: int, content: str, feedback_type: str = 'OTHER', context_url: Optional[str] = None) -> FeedbackDTO:
    """Public API to submit feedback."""
    feedback = Feedback(
        user_id=user_id,
        content=content,
        type=feedback_type,
        context_url=context_url
    )
    db.session.add(feedback)
    db.session.commit()
    
    return FeedbackDTO(
        id=feedback.feedback_id,
        user_id=feedback.user_id,
        type=feedback.type,
        content=feedback.content,
        status=feedback.status,
        created_at=feedback.created_at,
        context_url=feedback.context_url
    )

def list_user_feedback(user_id: int) -> List[FeedbackDTO]:
    """Get all feedback submitted by a user."""
    feedbacks = Feedback.query.filter_by(user_id=user_id).order_by(Feedback.created_at.desc()).all()
    return [
        FeedbackDTO(
            id=f.feedback_id,
            user_id=f.user_id,
            type=f.type,
            content=f.content,
            status=f.status,
            created_at=f.created_at,
            context_url=f.context_url
        ) for f in feedbacks
    ]
