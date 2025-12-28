"""System and administration related models."""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.inspection import inspect
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from ..db_instance import db

# SystemSetting class REMOVED - replaced by AppSettings in app_settings.py


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
    last_updated = db.Column(
        db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BackgroundTaskLog(db.Model):
    """Audit log entries for task state transitions and messages."""

    __tablename__ = 'background_task_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, nullable=False)
    task_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    progress = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    message = db.Column(db.Text)
    stop_requested = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())


class ApiKey(db.Model):
    """Persisted API keys."""

    __tablename__ = 'api_keys'

    key_id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), default='gemini', nullable=False)
    key_value = db.Column(db.String(255), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_exhausted = db.Column(db.Boolean, default=False)
    last_used_timestamp = db.Column(db.DateTime(timezone=True))
    notes = db.Column(db.Text)


def _task_has_state_changes(target: BackgroundTask) -> bool:
    """Check whether tracked fields have changed to decide if a log should be created."""

    state = inspect(target)
    tracked_fields = ('status', 'progress', 'total', 'message', 'stop_requested', 'is_enabled')
    return any(state.attrs[field].history.has_changes() for field in tracked_fields)


def _insert_task_log(connection, target: BackgroundTask) -> None:
    connection.execute(
        BackgroundTaskLog.__table__.insert().values(
            task_id=target.task_id,
            task_name=target.task_name,
            status=target.status,
            progress=target.progress,
            total=target.total,
            message=target.message,
            stop_requested=target.stop_requested,
        )
    )


@event.listens_for(BackgroundTask, 'after_insert')
def create_log_after_insert(mapper, connection, target):  # pylint: disable=unused-argument
    """Capture initial state when a task record is created."""

    _insert_task_log(connection, target)


@event.listens_for(BackgroundTask, 'after_update')
def create_log_after_update(mapper, connection, target):  # pylint: disable=unused-argument
    """Persist a log entry whenever a tracked field changes."""

    if not _task_has_state_changes(target):
        return
    _insert_task_log(connection, target)


class AILog(db.Model):
    """Log entry for AI generation requests (auditing and quotas)."""

    __tablename__ = 'ai_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    user_id = db.Column(db.Integer, nullable=True)  # Optional, if triggered by a user action
    
    provider = db.Column(db.String(50), nullable=False)   # 'gemini', 'huggingface', etc.
    model_name = db.Column(db.String(100), nullable=False) # e.g. 'gemini-1.5-flash'
    key_id = db.Column(db.Integer, db.ForeignKey('api_keys.key_id'), nullable=True)
    
    # Context
    request_type = db.Column(db.String(50)) # e.g. 'explanation', 'translation', 'chat'
    item_info = db.Column(db.String(255))   # Description of what was processed (e.g. "Card #123")
    
    # Metrics
    prompt_chars = db.Column(db.Integer, default=0)
    response_chars = db.Column(db.Integer, default=0)
    processing_time_ms = db.Column(db.Integer, default=0)
    
    # Status
    status = db.Column(db.String(20), default='success') # 'success', 'error'
    error_message = db.Column(db.Text, nullable=True)

    # Relationships
    api_key = db.relationship('ApiKey', backref='logs')
