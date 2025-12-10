"""Bootstrap helpers for configuring the Flask application."""

from __future__ import annotations

import logging
import os
from typing import Callable

from flask import Flask
from flask_login import current_user

from sqlalchemy import inspect, or_, text

from ..config import BASE_DIR
from ..extensions import csrf_protect, db, login_manager, scheduler
from ..modules.shared.utils.bbcode_parser import bbcode_to_html
from .module_registry import register_default_modules


def configure_logging(app: Flask) -> None:
    """Configure application logging if no handlers are present."""

    if app.logger.handlers:
        return

    app.logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.propagate = False
    app.logger.info("Flask app logger configured successfully.")


def register_extensions(app: Flask) -> None:
    """Initialize shared extensions with the Flask app instance."""

    db.init_app(app)
    login_manager.init_app(app)
    csrf_protect.init_app(app)

    # Scheduler Configuration
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        from apscheduler.schedulers import SchedulerAlreadyRunningError
        try:
            scheduler.init_app(app)
            if not scheduler.running:
                scheduler.start()
            
            try:
                from ..modules.telegram_bot.tasks import send_daily_study_reminder
                if not scheduler.get_job('telegram_daily_reminder'):
                    scheduler.add_job(
                        id='telegram_daily_reminder',
                        func=send_daily_study_reminder,
                        trigger='cron',
                        hour=7,
                        minute=0,
                        replace_existing=True
                    )
                    app.logger.info("Đã đăng ký job Telegram Reminder (7:00 AM).")
            except ImportError:
                app.logger.warning("Module telegram_bot chưa sẵn sàng hoặc bị lỗi import.")
        except SchedulerAlreadyRunningError:
            app.logger.info("Scheduler đã chạy, bỏ qua khởi tạo lại.")
        except Exception as e:
            app.logger.error(f"Lỗi khởi tạo Scheduler: {e}")


def configure_static_uploads(app: Flask) -> None:
    """Point Flask's static handling to the uploads directory."""

    app.static_folder = os.path.join(BASE_DIR, "uploads")
    app.static_url_path = "/uploads"
    app.logger.info("Đã cấu hình thư mục tĩnh 'uploads' tại URL: %s", app.static_url_path)


def register_context_processors(app: Flask) -> None:
    """Register global template context processors."""

    @app.context_processor
    def inject_utility_functions() -> dict[str, Callable[..., str]]:
        return {"bbcode_to_html": bbcode_to_html}

    @login_manager.user_loader
    def load_user(user_id: str):
        from ..models import User

        return User.query.get(int(user_id))

    @app.context_processor
    def inject_user() -> dict[str, object]:
        return {"current_user": current_user}


def register_blueprints(app: Flask) -> None:
    """Register all default blueprints with the app."""

    register_default_modules(app)


def initialize_database(app: Flask) -> None:
    """Create database tables and ensure the default data exists."""

    from ..models import BackgroundTask, User

    db.create_all()

    inspector = inspect(db.engine)
    
    # Migrate flashcard_collab_rooms
    room_columns = {column['name'] for column in inspector.get_columns('flashcard_collab_rooms')}
    if 'button_count' not in room_columns:
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE flashcard_collab_rooms "
                    "ADD COLUMN button_count INTEGER NOT NULL DEFAULT 3"
                )
            )
        app.logger.info("Đã thêm cột button_count vào flashcard_collab_rooms (migrate in place).")

    # Migrate api_keys
    api_key_columns = {column['name'] for column in inspector.get_columns('api_keys')}
    if 'provider' not in api_key_columns:
        with db.engine.begin() as connection:
            # SQLite doesn't support adding a non-null column without a default value in a simple way 
            # if there are existing rows. We add it with a default.
            connection.execute(
                text(
                    "ALTER TABLE api_keys "
                    "ADD COLUMN provider VARCHAR(50) NOT NULL DEFAULT 'gemini'"
                )
            )
        app.logger.info("Đã thêm cột provider vào api_keys (migrate in place).")

    # Migrate users (timezone)
    user_columns = {column['name'] for column in inspector.get_columns('users')}
    if 'timezone' not in user_columns:
        with db.engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN timezone VARCHAR(50) DEFAULT 'UTC'"
                )
            )
        app.logger.info("Đã thêm cột timezone vào users (migrate in place).")

    admin_user = User.query.filter(
        or_(
            User.user_role == User.ROLE_ADMIN,
            User.username == "admin",
            User.email == "admin@example.com",
        )
    ).first()
    if admin_user is None:
        admin = User(username="admin", email="admin@example.com", user_role=User.ROLE_ADMIN)
        admin.set_password("admin")
        db.session.add(admin)
        db.session.commit()
        app.logger.info("Đã tạo user admin mặc định.")
    else:
        app.logger.info("Đã phát hiện user admin sẵn có, bỏ qua bước khởi tạo mặc định.")

    for task_name in [
        "generate_audio_cache",
        "clean_audio_cache",
        "generate_image_cache",
        "clean_image_cache",
        "generate_ai_explanations",
    ]:
        if not BackgroundTask.query.filter_by(task_name=task_name).first():
            task = BackgroundTask(task_name=task_name, message="Sẵn sàng", is_enabled=True)
            db.session.add(task)
    db.session.commit()
