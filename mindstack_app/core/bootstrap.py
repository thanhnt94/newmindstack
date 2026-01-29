"""Bootstrap helpers for configuring the Flask application."""

from __future__ import annotations

import logging
import os
from typing import Callable

from flask import Flask
from flask_login import current_user

from sqlalchemy import inspect, or_, text

from ..config import BASE_DIR
from ..extensions import csrf_protect, db, login_manager, scheduler, migrate
from mindstack_app.utils.bbcode_parser import bbcode_to_html
from .module_registry import register_default_modules
from .error_handlers import register_error_handlers


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
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf_protect.init_app(app)

    # Scheduler Configuration
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        from apscheduler.schedulers import SchedulerAlreadyRunningError
        try:
            scheduler.init_app(app)
            if not scheduler.running:
                scheduler.start()
            
            # WAL Checkpoint job - merge WAL to main DB every 30 minutes
            def checkpoint_wal():
                """Checkpoint WAL file to merge changes into main database."""
                try:
                    with app.app_context():
                        db.session.execute(db.text('PRAGMA wal_checkpoint(PASSIVE)'))
                        app.logger.info("WAL checkpoint completed successfully.")
                except Exception as e:
                    app.logger.error(f"WAL checkpoint failed: {e}")
            
            if not scheduler.get_job('wal_checkpoint'):
                scheduler.add_job(
                    id='wal_checkpoint',
                    func=checkpoint_wal,
                    trigger='interval',
                    minutes=30,
                    replace_existing=True
                )
                app.logger.info("Đã đăng ký job WAL Checkpoint (mỗi 30 phút).")
            
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


def configure_static_media_routes(app: Flask) -> None:
    """Configure specialized routes for media and theme assets."""
    from flask import send_from_directory
    import os

    # 1. User Media (Stateful - Uploads)
    @app.route('/media/<path:filename>')
    def media_uploads(filename):
        """Serve files from UPLOAD_FOLDER."""
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # 2. Theme Assets (Stateless - Source Code)
    @app.route('/theme-assets/<theme_name>/<path:filename>')
    def theme_assets(theme_name, filename):
        """Serve static assets from within theme directories."""
        theme_path = os.path.join(app.template_folder, theme_name, 'assets')
        return send_from_directory(theme_path, filename)

    # 3. Keep standard favicon routes from root static if needed, 
    # but preferred way is to move them to theme assets later.
    @app.route('/favicon.ico')
    def favicon_ico():
        return send_from_directory(
            os.path.join(app.root_path, 'static'),
            'favicon.ico',
            mimetype='image/x-icon'
        )

    @app.route('/favicon.png')
    def favicon_png():
        return send_from_directory(
            os.path.join(app.root_path, 'static'),
            'favicon.png',
            mimetype='image/png'
        )

    app.logger.info("Core routes configured: /media/ (uploads) and /theme-assets/ (themes)")


def register_context_processors(app: Flask) -> None:
    """Register global template context processors."""

    @app.context_processor
    def inject_template_version() -> dict[str, str]:
        """Inject _v (template version) into all templates from database."""
        from mindstack_app.services.template_service import TemplateService
        version = TemplateService.get_active_version()
        return {"_v": version, "template_version": version}

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

    @app.template_filter('media_url')
    def media_url_filter(path):
        """Converts a stored media path to a /media/ URL."""
        if not path:
            return ''
        
        p = str(path).strip().replace('\\', '/')
        
        if p.startswith(('http://', 'https://', '/')):
            return p
            
        # Normalize: remove legacy prefixes
        if p.startswith('static/'):
            p = p[7:]
        if p.startswith('uploads/'):
            p = p[8:]
            
        return f"/media/{p.lstrip('/')}"

    @app.template_filter('user_timezone')
    def user_timezone_filter(dt, fmt='%Y-%m-%d %H:%M:%S'):
        """Converts a UTC datetime to the user's timezone."""
        if not dt:
            return ''
        
        # Ensure timezone-aware (assume UTC if naive)
        if dt.tzinfo is None:
            from datetime import timezone
            dt = dt.replace(tzinfo=timezone.utc)
            
        # Determine target timezone
        tz_name = 'UTC'
        if current_user.is_authenticated and getattr(current_user, 'timezone', None):
            tz_name = current_user.timezone
        else:
            # Get from app.config (loaded from AppSettings by config_service)
            if app.config.get('SYSTEM_TIMEZONE'):
                tz_name = app.config.get('SYSTEM_TIMEZONE')

        try:
            # Try using zoneinfo (Python 3.9+)
            try:
                from zoneinfo import ZoneInfo
                tz = ZoneInfo(tz_name)
            except ImportError:
                # Fallback to pytz
                import pytz
                tz = pytz.timezone(tz_name)
                
            local_dt = dt.astimezone(tz)
            return local_dt.strftime(fmt)
        except Exception:
            return dt.strftime(fmt)


def register_blueprints(app: Flask) -> None:
    """Register all default blueprints with the app."""

    register_default_modules(app)


def initialize_database(app: Flask) -> None:
    """Create database tables and ensure the default data exists."""

    from ..models import BackgroundTask, User

    # === Startup WAL Checkpoint ===
    # Gộp tất cả thay đổi từ WAL file vào database chính khi khởi động
    # Sử dụng TRUNCATE để dọn dẹp WAL file hoàn toàn
    try:
        with db.engine.connect() as conn:
            result = conn.execute(db.text('PRAGMA wal_checkpoint(TRUNCATE)'))
            checkpoint_result = result.fetchone()
            if checkpoint_result and checkpoint_result[0] == 0:
                app.logger.info(
                    f"Startup WAL checkpoint thành công: "
                    f"{checkpoint_result[1]} pages đã gộp, "
                    f"{checkpoint_result[2]} pages không thể gộp."
                )
            else:
                app.logger.warning(f"WAL checkpoint kết quả: {checkpoint_result}")
    except Exception as e:
        app.logger.warning(f"Startup WAL checkpoint failed (non-critical): {e}")

    db.create_all()

    inspector = inspect(db.engine)
    
    # MANUAL MIGRATIONS REMOVED - Using Flask-Migrate instead.

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
    
    # Khởi tạo huy hiệu Gamification
    from .gamification_seeds import seed_badges
    badges_added = seed_badges()
    if badges_added > 0:
        app.logger.info(f"Đã khởi tạo thành công {badges_added} huy hiệu mới.")

    db.session.commit()
