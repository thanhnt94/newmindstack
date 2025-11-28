"""Application-wide extensions.

This module centralizes extension instances so they can be imported without
causing circular dependencies. Centralizing extension configuration makes it
simpler to reuse the same initialization logic across blueprints and services.
"""

from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_apscheduler import APScheduler

from .db_instance import db

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Vui lòng đăng nhập để truy cập trang này."
login_manager.login_message_category = "info"

csrf_protect = CSRFProtect()
scheduler = APScheduler()

__all__ = ["db", "login_manager", "csrf_protect", "scheduler"]
