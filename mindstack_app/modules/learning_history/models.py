from datetime import datetime, timezone
from sqlalchemy.types import JSON
from mindstack_app.core.extensions import db

class StudyLog(db.Model):
    """
    Scribe model for recording all learning interactions.
    Replaces the legacy ReviewLog.
    """
    __tablename__ = 'study_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    
    # Loose relationships (IDs only) to minimize coupling
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False, index=True)
    
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    # Performance Data
    rating = db.Column(db.Integer, nullable=False) # 1-4 (Again, Hard, Good, Easy) or other scales
    user_answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, default=False)
    review_duration = db.Column(db.Integer, default=0) # milliseconds
    
    # Context Data
    session_id = db.Column(db.Integer, db.ForeignKey('learning_sessions.session_id'), nullable=True, index=True)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=True, index=True)
    learning_mode = db.Column(db.String(50), nullable=True) # flashcard, quiz, typing, etc.
    
    # Snapshot Data (JSON)
    fsrs_snapshot = db.Column(JSON, nullable=True)
    gamification_snapshot = db.Column(JSON, nullable=True)
    context_snapshot = db.Column(JSON, nullable=True)
    
    __table_args__ = (
        db.Index('ix_study_logs_user_timestamp', 'user_id', 'timestamp'),
    )
