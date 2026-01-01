# File: web/mindstack_app/config.py
# Phiên bản: 1.7
# MỤC ĐÍCH: Thêm cấu hình cho thư mục BACKUP_FOLDER.

import os

# Xác định thư mục gốc của dự án (thư mục Mindstack)
# File config.py này nằm ở Mindstack/web/mindstack_app/
# nên chúng ta cần đi lên 2 cấp để đến thư mục gốc.
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Đường dẫn đến file database SQLite mới, nằm trong thư mục database/ ở gốc
DATABASE_PATH = os.path.join(BASE_DIR, "database", "mindstack_new.db")

class Config:
    """
    Lớp cấu hình cho ứng dụng Flask.
    """
    # Khóa bí mật để bảo vệ session (luôn ưu tiên biến môi trường)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_key_for_the_new_app'

    # Cấu hình đường dẫn đến cơ sở dữ liệu (ưu tiên biến môi trường)
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or f'sqlite:///{DATABASE_PATH}'

    # Tăng thời gian chờ kết nối để giảm lỗi "database is locked" của SQLite
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'connect_args': {
            'timeout': 30,
        },
    }

    # Tắt tính năng theo dõi sự thay đổi của SQLAlchemy để tiết kiệm tài nguyên
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Cấu hình phân trang
    ITEMS_PER_PAGE = 12 # Số mục trên mỗi trang

    # Cấu hình thư mục lưu trữ file tải lên (media)
    # HARDCODED FOR TESTING
    UPLOAD_FOLDER = r'C:\Code\MindStack\uploads'
    
    # THÊM MỚI: Cấu hình thư mục sao lưu (backup)
    # Đặt thư mục backups ở thư mục gốc của dự án
    BACKUP_FOLDER = os.path.join(BASE_DIR, 'backups')

    # Định nghĩa thư mục con cho cache audio và hình ảnh của flashcard
    FLASHCARD_AUDIO_CACHE_DIR = os.path.join(UPLOAD_FOLDER, 'flashcard', 'audio', 'cache')
    FLASHCARD_IMAGE_CACHE_DIR = os.path.join(UPLOAD_FOLDER, 'flashcard', 'images', 'cache')

    # Đảm bảo thư mục database tồn tại khi ứng dụng khởi chạy
    db_dir = os.path.dirname(DATABASE_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    # Đảm bảo thư mục upload và các thư mục con cần thiết tồn tại khi ứng dụng khởi chạy
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(FLASHCARD_AUDIO_CACHE_DIR, exist_ok=True)
    os.makedirs(FLASHCARD_IMAGE_CACHE_DIR, exist_ok=True)
    
    # VAPID Keys for Web Push
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY') or 'vBQf0zqOP5TLHh-c2WHtDtDTXiu1Ob8u-C7trsxJovM'
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY') or 'BIoWOOLv0kTB0pee0MDsAOFrS0HdQoJOntmlwXOGRt84vh46XJns0lYspcAm5lPo82u3gbcHBEcVUqwJgAEODaQ'
    VAPID_EMAIL = os.environ.get('VAPID_EMAIL') or 'mailto:admin@mindstack.app'

    # THÊM MỚI: Đảm bảo thư mục backup tồn tại khi ứng dụng khởi chạy
    os.makedirs(BACKUP_FOLDER, exist_ok=True)
