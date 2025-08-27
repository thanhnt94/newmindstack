# File: web/mindstack_app/__init__.py
# Version: 2.9
# ĐÃ SỬA: Khắc phục lỗi `Error: Could not locate a Flask application`
#         bằng cách thêm một đối tượng `app` ở cấp cao nhất để Flask CLI có thể tìm thấy.
# ĐÃ SỬA: Khắc phục AttributeError: 'Config' object has no attribute 'BASE_DIR'
#         bằng cách import BASE_DIR trực tiếp từ module config.
# ĐÃ SỬA: Cấu hình Flask để phục vụ các file tĩnh từ thư mục 'uploads'.
# ĐÃ SỬA: Thêm email mặc định khi tạo tài khoản admin để khắc phục lỗi IntegrityError.
# ĐÃ SỬA: Đăng ký Blueprint mới cho module learning mà không làm mất code gốc.
# ĐÃ SỬA: Cấu hình logging cho ứng dụng Flask ngay trong hàm create_app để đảm bảo log debug hiển thị,
#         và ngăn chặn việc propagate log để tránh trùng lặp hoặc bị ghi đè.
# ĐÃ SỬA: Cấu hình để chỉ sử dụng một thư mục tĩnh là 'uploads' cho tất cả các file media.
# ĐÃ THÊM: Cấu hình Flask-Migrate để quản lý các thay đổi cơ sở dữ liệu.

from flask import Flask, g
from .config import Config, BASE_DIR
from .db_instance import db
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
import logging
import os

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Vui lòng đăng nhập để truy cập trang này."
login_manager.login_message_category = "info"

def create_app(config_class=Config):
    """
    Tạo và cấu hình đối tượng ứng dụng Flask.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    if not app.logger.handlers:
        app.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)
        app.logger.propagate = False

    app.logger.info("Flask app logger configured successfully.")

    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager.init_app(app)

    app.static_folder = os.path.join(BASE_DIR, 'uploads')
    app.static_url_path = '/uploads'
    app.logger.info(f"Đã cấu hình thư mục tĩnh 'uploads' tại URL: {app.static_url_path}")


    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        """
        Tải người dùng từ ID.
        """
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_user():
        """
        Cung cấp đối tượng current_user cho tất cả các template.
        """
        return dict(current_user=current_user)

    # Đăng ký các Blueprint
    from .modules.auth.routes import auth_bp
    from .modules.main.routes import main_bp
    from .modules.admin import admin_bp 
    from .modules.admin.user_management.user_routes import user_management_bp
    from .modules.user_profile import user_profile_bp 
    from .modules.content_management.routes import content_management_bp
    from .modules.learning.routes import learning_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_management_bp, url_prefix='/admin/users') 
    app.register_blueprint(user_profile_bp, url_prefix='/profile') 
    app.register_blueprint(content_management_bp, url_prefix='/content')
    app.register_blueprint(learning_bp, url_prefix='/learn')

    with app.app_context():
        # db.create_all() # BÌNH LUẬN DÒNG NÀY: Migration sẽ quản lý việc tạo bảng
        
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user is None:
            admin = User(username='admin', email='admin@example.com', user_role='admin')
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            app.logger.info("Đã tạo user admin mặc định.")
            
    return app

app = create_app()
