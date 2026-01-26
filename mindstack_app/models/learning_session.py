from datetime import datetime, timezone
from sqlalchemy.sql import func
from sqlalchemy.types import JSON
from ..db_instance import db

class LearningSession(db.Model):
    """
    Model for tracking learning sessions across devices and providing session-level statistics.
    """
    __tablename__ = 'learning_sessions'
    
    session_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    
    # Metadata
    learning_mode = db.Column(db.String(50), nullable=False)  # flashcard, quiz, etc.
    mode_config_id = db.Column(db.String(50), nullable=False)  # due_only, new_only, etc.
    set_id_data = db.Column(JSON, nullable=False)  # Stores set_id (int or list)
    status = db.Column(db.String(20), default='active', index=True)  # active, completed, paused, cancelled
    
    # Session Stats
    total_items = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    incorrect_count = db.Column(db.Integer, default=0)
    vague_count = db.Column(db.Integer, default=0)
    points_earned = db.Column(db.Integer, default=0)
    
    # Progress Tracking
    # List of item IDs that have been processed in this session
    processed_item_ids = db.Column(JSON, default=list)
    
    # Timestamps
    start_time = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    last_activity = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime(timezone=True))

    # Relationships
    user = db.relationship(
        'User',
        backref=db.backref('learning_sessions', lazy='dynamic', cascade='all, delete-orphan'),
        lazy=True
    )

    def to_dict(self):
        """Serialize session to dictionary."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'learning_mode': self.learning_mode,
            'mode_config_id': self.mode_config_id,
            'set_id_data': self.set_id_data,
            'status': self.status,
            'total_items': self.total_items,
            'correct_count': self.correct_count,
            'incorrect_count': self.incorrect_count,
            'vague_count': self.vague_count,
            'points_earned': self.points_earned,
            'processed_item_ids': self.processed_item_ids or [],
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }

    @property
    def is_active(self):
        return self.status == 'active'

    @property
    def progress_percentage(self):
        if not self.total_items or self.total_items == 0:
            return 0
        processed_count = len(self.processed_item_ids) if self.processed_item_ids else 0
        return min(100, int((processed_count / self.total_items) * 100))
