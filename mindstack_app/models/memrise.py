# File: mindstack_app/models/memrise.py
# Phiên bản: 1.0
# Mục đích: Model cho tiến trình học Memrise với SRS

from sqlalchemy.sql import func
from ..db_instance import db


# ==============================================================================
# Memory Level Constants
# ==============================================================================

# Intervals in minutes for each memory level (after correct answer)
MEMORY_INTERVALS = {
    0: 0,           # Not started
    1: 10,          # Just seen - 10 minutes
    2: 60,          # Learning - 1 hour
    3: 240,         # Learning - 4 hours
    4: 1440,        # Learning - 1 day
    5: 4320,        # Learning - 3 days
    6: 10080,       # Learning - 1 week
    7: 43200,       # Planted - 30 days
}

RELEARNING_INTERVAL = 10  # Reset to 10 minutes when wrong


class MemriseProgress(db.Model):
    """
    Tracks SRS progress for Memrise learning.
    Each user-item pair has a memory level (0-7) representing the "memory tree".
    """
    
    __tablename__ = 'memrise_progress'
    
    progress_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False)
    
    # Memory Level (0-7): The memory tree
    # 0 = not learned, 1-6 = learning, 7 = planted (fully learned)
    memory_level = db.Column(db.Integer, default=0, nullable=False)
    
    # SRS Fields
    due_time = db.Column(db.DateTime(timezone=True))
    interval = db.Column(db.Integer, default=0)  # minutes until next review
    
    # Statistics
    times_correct = db.Column(db.Integer, default=0, nullable=False)
    times_incorrect = db.Column(db.Integer, default=0, nullable=False)
    last_reviewed = db.Column(db.DateTime(timezone=True))
    first_seen = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # Session tracking
    current_streak = db.Column(db.Integer, default=0, nullable=False)  # Consecutive correct in session
    session_reps = db.Column(db.Integer, default=0, nullable=False)    # Times shown in current session
    
    # Relationships
    user = db.relationship('User', backref=db.backref('memrise_progress', lazy='dynamic'))
    item = db.relationship('LearningItem', backref=db.backref('memrise_progress', lazy='dynamic'))
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'item_id', name='_user_memrise_item_uc'),
        db.Index('ix_memrise_progress_due', 'user_id', 'due_time'),
    )
    
    def to_dict(self):
        return {
            'progress_id': self.progress_id,
            'item_id': self.item_id,
            'memory_level': self.memory_level,
            'due_time': self.due_time.isoformat() if self.due_time else None,
            'interval': self.interval,
            'times_correct': self.times_correct,
            'times_incorrect': self.times_incorrect,
            'current_streak': self.current_streak,
            'is_planted': self.memory_level >= 7,
        }
    
    @property
    def level_name(self):
        """Human-readable name for the memory level."""
        names = {
            0: 'Chưa học',
            1: 'Mới xem',
            2: 'Đang nhớ',
            3: 'Tạm nhớ',
            4: 'Nhớ khá',
            5: 'Nhớ tốt',
            6: 'Gần thuộc',
            7: 'Đã thuộc',
        }
        return names.get(self.memory_level, 'Unknown')
    
    @property
    def level_percentage(self):
        """Progress percentage (0-100)."""
        return min(100, int((self.memory_level / 7) * 100))
