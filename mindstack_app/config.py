# File: web/mindstack_app/config.py
# Phiên bản: 1.1
# Mục đích: Chứa các cấu hình cơ bản cho ứng dụng, đã được cập nhật
# để tương thích với cấu trúc thư mục mới và thêm cấu hình phân trang.
# ĐÃ SỬA: Thêm cấu hình cho thư mục lưu trữ file media (ảnh và audio).

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

    # Cấu hình phân trang
    ITEMS_PER_PAGE = 12 # Số mục trên mỗi trang

    # Cấu hình thư mục lưu trữ file tải lên (media)
    # Thư mục gốc cho tất cả các file tải lên
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    # Thư mục con cho hình ảnh
    UPLOAD_IMAGE_FOLDER = os.path.join(UPLOAD_FOLDER, 'images')
    # Thư mục con cho audio
    UPLOAD_AUDIO_FOLDER = os.path.join(UPLOAD_FOLDER, 'audio')

    # Đảm bảo thư mục database tồn tại khi ứng dụng khởi chạy
    db_dir = os.path.dirname(DATABASE_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # Đảm bảo các thư mục upload tồn tại khi ứng dụng khởi chạy
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(UPLOAD_IMAGE_FOLDER):
        os.makedirs(UPLOAD_IMAGE_FOLDER)
    if not os.path.exists(UPLOAD_AUDIO_FOLDER):
        os.makedirs(UPLOAD_AUDIO_FOLDER)

