# File: mindstack_app/core/extensions.py
# Infrastructure Layer: Flask Extensions initialization

import sqlite3
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_apscheduler import APScheduler
from flask_migrate import Migrate
from sqlalchemy import event
from sqlalchemy.engine import Engine

# 1. Database Initialization
db = SQLAlchemy()

@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, _connection_record):
    """Enable WAL mode and extend the busy timeout for SQLite connections."""
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
    finally:
        cursor.close()

# 2. Login Management
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Vui lòng đăng nhập để truy cập trang này."
login_manager.login_message_category = "info"

# 3. Security & Utilities
csrf_protect = CSRFProtect()
scheduler = APScheduler()
migrate = Migrate()

__all__ = ["db", "login_manager", "csrf_protect", "scheduler", "migrate"]
