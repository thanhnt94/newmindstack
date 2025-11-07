"""System and administration related models."""

from __future__ import annotations

from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from ..db_instance import db


class SystemSetting(db.Model):
    """Key/value configuration stored at application level."""

    __tablename__ = 'system_settings'

    setting_id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(JSON, nullable=False)
    description = db.Column(db.Text)


class BackgroundTask(db.Model):
    """Track state of background workers."""

    __tablename__ = 'background_tasks'

    task_id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(50), default='idle')
    progress = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    message = db.Column(db.Text)
    stop_requested = db.Column(db.Boolean, default=False)
    is_enabled = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())


class ApiKey(db.Model):
    """Persisted API keys."""

    __tablename__ = 'api_keys'

    key_id = db.Column(db.Integer, primary_key=True)
    key_value = db.Column(db.String(255), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_exhausted = db.Column(db.Boolean, default=False)
    last_used_timestamp = db.Column(db.DateTime(timezone=True))
    notes = db.Column(db.Text)
