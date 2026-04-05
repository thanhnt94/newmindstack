# File: mindstack_app/core/config.py
# Refactored to Core Infrastructure Layer

import os
from dotenv import load_dotenv

load_dotenv()

# Xác định thư mục gốc của dự án (thư mục Mindstack)
# File này nằm ở mindstack_app/core/ nên cần đi lên 3 cấp
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Đường dẫn đến file database SQLite tại thư mục Storage chung
DATABASE_PATH = os.path.join(BASE_DIR, "Storage", "database", "Mindstack.db")

class Config:
    """Cấu hình ứng dụng Mindstack."""
    
    # Security Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        # Fallback for development, though env is preferred
        SECRET_KEY = 'dev-secret-key-replace-in-production'
    
    SESSION_COOKIE_NAME = 'mindstack_session'
    
    # Session Configuration
    SESSION_TYPE = 'sqlalchemy'
    SESSION_SQLALCHEMY_TABLE = 'sessions'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = 30 * 24 * 60 * 60 # 30 Days

    WTF_CSRF_TIME_LIMIT = None  # Disable CSRF token expiration for troubleshooting

    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'connect_args': {'timeout': 30},
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ITEMS_PER_PAGE = 12
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "Storage" "MindStack", 'uploads')
    BACKUP_FOLDER = os.path.join(BASE_DIR, "Storage" "MindStack", 'backups')

    FLASHCARD_AUDIO_CACHE_DIR = os.path.join(UPLOAD_FOLDER, 'flashcard', 'audio', 'cache')
    FLASHCARD_IMAGE_CACHE_DIR = os.path.join(UPLOAD_FOLDER, 'flashcard', 'images', 'cache')
    COVERS_FOLDER = os.path.join(UPLOAD_FOLDER, 'covers')

    # Themes Configuration
    ACTIVE_THEME = os.environ.get('ACTIVE_THEME', 'aura_mobile')
    
    # VAPID Keys for Web Push
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY')
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY')
    VAPID_EMAIL = os.environ.get('VAPID_EMAIL')

    # Auth Provider Configuration
    AUTH_PROVIDER = os.environ.get('AUTH_PROVIDER', 'central')
    CENTRAL_AUTH_API_URL = os.environ.get('CENTRAL_AUTH_API_URL')
    CENTRAL_SSO_WEB_URL = os.environ.get('CENTRAL_SSO_WEB_URL')
    CENTRAL_AUTH_CLIENT_ID = os.environ.get('CENTRAL_AUTH_CLIENT_ID')
    CENTRAL_AUTH_CLIENT_SECRET = os.environ.get('CENTRAL_AUTH_CLIENT_SECRET')

    @classmethod
    def init_app(cls, app):
        """Khởi tạo các thư mục cần thiết."""
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(cls.FLASHCARD_AUDIO_CACHE_DIR, exist_ok=True)
        os.makedirs(cls.FLASHCARD_IMAGE_CACHE_DIR, exist_ok=True)
        os.makedirs(cls.COVERS_FOLDER, exist_ok=True)
        os.makedirs(cls.BACKUP_FOLDER, exist_ok=True)
