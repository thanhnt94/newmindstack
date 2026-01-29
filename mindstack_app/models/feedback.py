from datetime import datetime, timezone
from mindstack_app.db_instance import db
from sqlalchemy.sql import func

class Feedback(db.Model):
    """
    Unified Feedback Model.
    Supports system-wide feedback, error reporting, and feature requests.
    """
    __tablename__ = 'feedbacks'

    feedback_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    
    # Type: 'BUG', 'FEATURE', 'PRAISE', 'CONTENT_ERROR', 'OTHER'
    type = db.Column(db.String(50), default='OTHER', nullable=False)
    
    content = db.Column(db.Text, nullable=False)
    
    # URL where the feedback was initiated (context)
    context_url = db.Column(db.String(500), nullable=True)
    
    # Status: 'NEW', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'
    status = db.Column(db.String(50), default='NEW')
    
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    
    # Metadata for specific context (e.g., error logs, browser info)
    meta_data = db.Column(db.JSON, nullable=True)

    # Relationship to attachments
    attachments = db.relationship('FeedbackAttachment', backref='feedback', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.feedback_id,
            'user_id': self.user_id,
            'type': self.type,
            'content': self.content,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'context_url': self.context_url,
            'attachments': [a.file_path for a in self.attachments]
        }


class FeedbackAttachment(db.Model):
    """Stores paths to files attached to feedback."""
    __tablename__ = 'feedback_attachments'

    attachment_id = db.Column(db.Integer, primary_key=True)
    feedback_id = db.Column(db.Integer, db.ForeignKey('feedbacks.feedback_id'), nullable=False)
    
    file_path = db.Column(db.String(500), nullable=False) # Relative path in /uploads/feedback
    file_type = db.Column(db.String(50)) # 'image/png', 'application/pdf'
    
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
