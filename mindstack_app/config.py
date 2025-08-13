# Tệp: web/mindstack_app/config.py
# Mục đích: Chứa các cấu hình cơ bản cho ứng dụng, đã được cập nhật
# để tương thích với cấu trúc thư mục mới.

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
    # Khóa bí mật để bảo vệ session
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_key_for_the_new_app'

    # Cấu hình đường dẫn đến cơ sở dữ liệu
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'

    # Tắt tính năng theo dõi sự thay đổi của SQLAlchemy để tiết kiệm tài nguyên
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Đảm bảo thư mục database tồn tại khi ứng dụng khởi chạy
    db_dir = os.path.dirname(DATABASE_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)