from datetime import datetime, timezone
from mindstack_app.core.extensions import db

class ItemMemoryState(db.Model):
    """
    Tracks the memory state of a learning item for a user using FSRS parameters.
    Replaces the legacy LearningProgress model.
    """
    __tablename__ = 'item_memory_states'

    state_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=False, index=True)
    
    # FSRS State
    stability = db.Column(db.Float, default=0.0)
    difficulty = db.Column(db.Float, default=0.0)
    state = db.Column(db.Integer, default=0) # 0=New, 1=Learning, 2=Review, 3=Relearning
    
    # Scheduling
    due_date = db.Column(db.DateTime(timezone=True), index=True)
    last_review = db.Column(db.DateTime(timezone=True))
    
    # Metrics
    repetitions = db.Column(db.Integer, default=0)
    lapses = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0) # Correct streak
    incorrect_streak = db.Column(db.Integer, default=0)
    
    times_correct = db.Column(db.Integer, default=0)
    times_incorrect = db.Column(db.Integer, default=0)
    
    # Generic Data (e.g. course completion, legacy flags)
    data = db.Column(db.JSON, nullable=True)
    
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'item_id', name='uq_user_item_memory'),
    )

    def to_dict(self):
        return {
            'state_id': self.state_id,
            'user_id': self.user_id,
            'item_id': self.item_id,
            'stability': self.stability,
            'difficulty': self.difficulty,
            'state': self.state,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'last_review': self.last_review.isoformat() if self.last_review else None,
            'repetitions': self.repetitions,
            'lapses': self.lapses
        }
