"""
Stats Module Models
Defines aggregate statistics and metrics for users.
"""
from datetime import datetime, timezone
from mindstack_app.core.extensions import db

class UserMetric(db.Model):
    """
    Stores accumulated global metrics for a user.
    Example key: 'total_cards_learned', 'total_study_time_seconds', 'highest_streak'.
    """
    __tablename__ = 'user_metrics'

    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
    metric_key = db.Column(db.String(50), primary_key=True)
    metric_value = db.Column(db.Float, default=0.0)
    
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<UserMetric {self.user_id} {self.metric_key}={self.metric_value}>'

class DailyStat(db.Model):
    """
    Stores daily aggregate statistics for a user.
    Example key: 'cards_reviewed', 'quiz_points', 'study_time_seconds'.
    """
    __tablename__ = 'daily_stats'

    stat_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    metric_key = db.Column(db.String(50), nullable=False)
    metric_value = db.Column(db.Float, default=0.0)
    
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', 'metric_key', name='_user_date_metric_uc'),
        db.Index('ix_daily_stats_user_date', 'user_id', 'date'),
    )

    def __repr__(self):
        return f'<DailyStat {self.user_id} {self.date} {self.metric_key}={self.metric_value}>'

class Achievement(db.Model):
    """
    Records of specific achievements or recognized milestones.
    """
    __tablename__ = 'stat_achievements'

    achievement_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    achievement_code = db.Column(db.String(50), nullable=False)
    achieved_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    data = db.Column(db.JSON, nullable=True) # Any extra metadata

    __table_args__ = (
        db.UniqueConstraint('user_id', 'achievement_code', name='_user_achievement_uc'),
    )

    def __repr__(self):
        return f'<Achievement {self.user_id} {self.achievement_code}>'
