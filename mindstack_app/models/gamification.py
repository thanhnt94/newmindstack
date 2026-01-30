from mindstack_app.core.extensions import db
from sqlalchemy.sql import func
from datetime import datetime

class Badge(db.Model):
    """Mô hình Huy hiệu."""
    __tablename__ = 'badges'
    
    badge_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    icon_class = db.Column(db.String(50), default='fas fa-medal') # FontAwesome class
    
    # Logic điều kiện
    condition_type = db.Column(db.String(50), nullable=False) # STREAK, TOTAL_SCORE, etc.
    condition_value = db.Column(db.Integer, nullable=False)
    
    reward_points = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # Constants cho loại điều kiện
    TYPE_STREAK = 'STREAK'
    TYPE_TOTAL_SCORE = 'TOTAL_SCORE'
    TYPE_FLASHCARD_COUNT = 'FLASHCARD_COUNT'
    TYPE_QUIZ_COUNT = 'QUIZ_COUNT'

    def __repr__(self):
        return f'<Badge {self.name}>'

class UserBadge(db.Model):
    """Mô hình User đã đạt huy hiệu."""
    __tablename__ = 'user_badges'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badges.badge_id'), nullable=False)
    earned_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    badge = db.relationship('Badge')
    # User relationship backref is defined in User model (recommended) or here lazily.
    # Let's keep it simple here.
    
    __table_args__ = (db.UniqueConstraint('user_id', 'badge_id', name='_user_badge_uc'),)

    def to_dict(self):
        return {
            'id': self.id,
            'badge_name': self.badge.name,
            'badge_description': self.badge.description,
            'icon_class': self.badge.icon_class,
            'earned_at': self.earned_at.isoformat() if self.earned_at else None
        }

class ScoreLog(db.Model):
    """History of score changes for a user."""
    __tablename__ = 'score_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('learning_items.item_id'), nullable=True)
    score_change = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    item_type = db.Column(db.String(50), nullable=True)

    __table_args__ = (
        db.Index('ix_score_logs_user_timestamp', 'user_id', 'timestamp'),
        db.Index('ix_score_logs_timestamp', 'timestamp'),
    )

    def to_dict(self):
        return {
            'log_id': self.log_id,
            'score_change': self.score_change,
            'amount': self.score_change,
            'reason': self.reason,
            'item_type': self.item_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class Streak(db.Model):
    """Stores user streak information."""
    __tablename__ = 'user_streaks'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
    current_streak = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)
    last_activity_date = db.Column(db.Date)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())
