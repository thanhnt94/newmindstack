"""Goal management models."""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.sql import func
from mindstack_app.core.extensions import db

class Goal(db.Model):
    """
    System-defined goal templates/definitions.
    Defines the available goal types that users can subscribe to or be assigned.
    """
    __tablename__ = 'goals'

    goal_code = db.Column(db.String(50), primary_key=True) # e.g. 'daily_cards_reviewed', 'weekly_xp'
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    
    # Classification
    domain = db.Column(db.String(50), default='general') # flashcard, quiz, general
    metric = db.Column(db.String(50), nullable=False) # items_reviewed, new_items, points, etc.
    
    # Defaults
    default_period = db.Column(db.String(20), default='daily') # daily, weekly
    default_target = db.Column(db.Integer, default=10)
    icon = db.Column(db.String(50), default='star')
    
    is_active = db.Column(db.Boolean, default=True) # If false, users can't create new goals of this type

    # Relationships
    user_goals = db.relationship('UserGoal', backref='definition', lazy=True)

    def __repr__(self):
        return f'<Goal {self.goal_code}>'


class UserGoal(db.Model):
    """
    User-specific instance of a goal.
    """
    __tablename__ = 'user_goals'

    user_goal_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    goal_code = db.Column(db.String(50), db.ForeignKey('goals.goal_code'), nullable=False)
    
    # Configuration
    target_value = db.Column(db.Integer, nullable=False)
    period = db.Column(db.String(20), nullable=False) # daily, weekly (usually inherits from Goal)
    
    # Scope (Optional - for container specific goals)
    scope = db.Column(db.String(50), default='global') # global, container
    reference_id = db.Column(db.Integer, nullable=True) # container_id if scope=container

    # Lifecycle
    start_date = db.Column(db.Date, default=func.current_date())
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    # Relationships
    progress_logs = db.relationship('GoalProgress', backref='user_goal', lazy='dynamic', cascade='all, delete-orphan')
    user = db.relationship('User', backref=db.backref('user_goals_v2', lazy=True))

    def __repr__(self):
        return f'<UserGoal {self.user_goal_id} - {self.goal_code}>'


class GoalProgress(db.Model):
    """
    Daily/Weekly progress tracking for a UserGoal.
    """
    __tablename__ = 'goal_progress_logs'

    progress_id = db.Column(db.Integer, primary_key=True)
    user_goal_id = db.Column(db.Integer, db.ForeignKey('user_goals.user_goal_id'), nullable=False)
    
    date = db.Column(db.Date, nullable=False) # The date this record represents
    
    current_value = db.Column(db.Integer, default=0)
    target_snapshot = db.Column(db.Integer, default=0) # Target at that time
    is_met = db.Column(db.Boolean, default=False)
    
    last_updated = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        db.UniqueConstraint('user_goal_id', 'date', name='_user_goal_progress_uc'),
        db.Index('ix_goal_progress_date', 'date'),
    )

    def __repr__(self):
        return f'<GoalProgress {self.user_goal_id} - {self.date}: {self.current_value}/{self.target_snapshot}>'
