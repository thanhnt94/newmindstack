"""Bootstrap helpers for configuring the Flask application."""

from __future__ import annotations

import logging
import os
from typing import Callable

from flask import Flask
from flask_login import current_user

from ..config import BASE_DIR
from ..extensions import csrf_protect, db, login_manager
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

    admin_user = User.query.filter_by(username="admin").first()
    if admin_user is None:
        admin = User(username="admin", email="admin@example.com", user_role=User.ROLE_ADMIN)
        admin.set_password("admin")
        db.session.add(admin)
        db.session.commit()
        app.logger.info("Đã tạo user admin mặc định.")

    for task_name in [
        "generate_audio_cache",
        "clean_audio_cache",
        "generate_image_cache",
        "clean_image_cache",
    ]:
        if not BackgroundTask.query.filter_by(task_name=task_name).first():
            task = BackgroundTask(task_name=task_name, message="Sẵn sàng", is_enabled=True)
            db.session.add(task)
    db.session.commit()
