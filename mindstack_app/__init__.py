# File: web/mindstack_app/__init__.py
# Version: 3.3
# MỤC ĐÍCH: Đăng ký hàm bbcode_to_html như một context processor toàn cục.
# ĐÃ THÊM: app.context_processor để inject hàm bbcode_to_html.

from flask import Flask, g
from .config import Config, BASE_DIR
from .db_instance import db
from flask_login import LoginManager, current_user
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
    login_manager.init_app(app)

    app.static_folder = os.path.join(BASE_DIR, 'uploads')
    app.static_url_path = '/uploads'
    app.logger.info(f"Đã cấu hình thư mục tĩnh 'uploads' tại URL: {app.static_url_path}")


    # Đăng ký các hàm tiện ích toàn cục cho template
    from .modules.shared.utils.bbcode_parser import bbcode_to_html
    @app.context_processor
    def inject_utility_functions():
        return dict(bbcode_to_html=bbcode_to_html)

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
    from .modules.admin.api_key_management.routes import api_key_management_bp
    from .modules.user_profile import user_profile_bp 
    from .modules.content_management.routes import content_management_bp
    from .modules.learning.routes import learning_bp
    from .modules.ai_services.routes import ai_services_bp
    from .modules.notes.routes import notes_bp
    from .modules.shared import shared_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_management_bp, url_prefix='/admin/users') 
    app.register_blueprint(api_key_management_bp, url_prefix='/admin/api-keys')
    app.register_blueprint(user_profile_bp, url_prefix='/profile') 
    app.register_blueprint(content_management_bp, url_prefix='/content')
    app.register_blueprint(learning_bp, url_prefix='/learn')
    app.register_blueprint(ai_services_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(shared_bp)


    with app.app_context():
        db.create_all()
        
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user is None:
            admin = User(username='admin', email='admin@example.com', user_role='admin')
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            app.logger.info("Đã tạo user admin mặc định.")
            
    return app

app = create_app()
