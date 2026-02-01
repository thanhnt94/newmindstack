"""System and administration related models."""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.inspection import inspect
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from mindstack_app.core.extensions import db

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
