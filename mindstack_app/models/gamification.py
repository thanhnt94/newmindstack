from mindstack_app.db_instance import db
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
