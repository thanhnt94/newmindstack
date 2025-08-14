# File: web/mindstack_app/__init__.py
# Version: 2.1
# ĐÃ SỬA: Thêm email mặc định khi tạo tài khoản admin để khắc phục lỗi IntegrityError.

from flask import Flask, g
from .config import Config
from .db_instance import db
from flask_login import LoginManager, current_user
from flask_migrate import Migrate

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
    
    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager.init_app(app)

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

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_management_bp, url_prefix='/admin/users') 
    app.register_blueprint(user_profile_bp, url_prefix='/profile') 
    app.register_blueprint(content_management_bp, url_prefix='/content')

    with app.app_context():
        db.create_all()
        
        # Logic tạo user admin mặc định nếu chưa tồn tại
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user is None:
            # SỬA: Thêm email mặc định
            admin = User(username='admin', email='admin@example.com', user_role='admin')
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            print("Đã tạo user admin mặc định.")
            
    return app
