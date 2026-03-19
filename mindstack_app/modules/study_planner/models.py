"""Database models for the Study Planner module."""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.sql import func
from mindstack_app.core.extensions import db


class StudyPlan(db.Model):
    """
    Represents a user's study plan for completing a specific learning container.
    
    A plan tracks the goal of learning all new cards in a container by a target date,
    automatically adjusting daily targets based on actual progress.
    """
    __tablename__ = 'study_plans'

    plan_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    container_id = db.Column(db.Integer, db.ForeignKey('learning_containers.container_id'), nullable=False, index=True)
    
    title = db.Column(db.String(200), nullable=True)  # Default = container title
    
    # Timeline
    start_date = db.Column(db.Date, nullable=False)
    target_end_date = db.Column(db.Date, nullable=False)
    
    # Snapshot at plan creation
    total_items = db.Column(db.Integer, nullable=False, default=0)
    initial_learned = db.Column(db.Integer, nullable=False, default=0)
    
    # Lifecycle
    status = db.Column(db.String(20), nullable=False, default='active')  # active, completed, cancelled, paused
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    daily_logs = db.relationship(
        'StudyPlanDailyLog', 
        backref='plan', 
        lazy='dynamic', 
        cascade='all, delete-orphan',
        order_by='StudyPlanDailyLog.date'
    )
    user = db.relationship('User', backref=db.backref('study_plans', lazy='dynamic'))
    container = db.relationship('LearningContainer', backref=db.backref('study_plans', lazy='dynamic'))
    
    __table_args__ = (
        # Only one active plan per user per container
        db.Index('ix_study_plan_user_container_status', 'user_id', 'container_id', 'status'),
    )

    def __repr__(self):
        return f'<StudyPlan {self.plan_id} user={self.user_id} container={self.container_id} status={self.status}>'
    
    @property
    def items_to_learn(self) -> int:
        """Total items that need to be learned from plan start."""
        return self.total_items - self.initial_learned

    def to_dict(self):
        return {
            'plan_id': self.plan_id,
            'user_id': self.user_id,
            'container_id': self.container_id,
            'title': self.title,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'target_end_date': self.target_end_date.isoformat() if self.target_end_date else None,
            'total_items': self.total_items,
            'initial_learned': self.initial_learned,
            'items_to_learn': self.items_to_learn,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class StudyPlanDailyLog(db.Model):
    """
    Tracks daily progress for a study plan.
    
    Each record represents one day's target and actual learning count.
    The system creates/updates these records as the user learns cards.
    """
    __tablename__ = 'study_plan_daily_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('study_plans.plan_id', ondelete='CASCADE'), nullable=False, index=True)
    
    date = db.Column(db.Date, nullable=False)
    
    # Targets & Actuals
    target_new_cards = db.Column(db.Integer, nullable=False, default=0)
    actual_new_cards = db.Column(db.Integer, nullable=False, default=0)
    
    # Cumulative progress
    cumulative_learned = db.Column(db.Integer, nullable=False, default=0)
    
    # Status
    is_met = db.Column(db.Boolean, default=False)
    
    # Optional note
    note = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        db.UniqueConstraint('plan_id', 'date', name='uq_plan_date_log'),
        db.Index('ix_daily_log_date', 'date'),
    )

    def __repr__(self):
        return f'<DailyLog plan={self.plan_id} date={self.date} actual={self.actual_new_cards}/{self.target_new_cards}>'

    def to_dict(self):
        return {
            'log_id': self.log_id,
            'plan_id': self.plan_id,
            'date': self.date.isoformat() if self.date else None,
            'target_new_cards': self.target_new_cards,
            'actual_new_cards': self.actual_new_cards,
            'cumulative_learned': self.cumulative_learned,
            'is_met': self.is_met,
            'note': self.note,
        }
