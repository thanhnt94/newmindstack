# File: web/mindstack_app/__init__.py
# Version: 3.11 - Đã đăng ký Blueprint courses
from flask import Flask, g
from .config import Config
from .db_instance import db
from flask_login import LoginManager, current_user

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
    # Đảm bảo import đúng đường dẫn tương đối
    from .modules.auth.routes import auth_bp
    from .modules.main.routes import main_bp
    from .modules.admin import admin_bp 
    from .modules.admin.user_management import user_management_bp 
    from .modules.user_profile import user_profile_bp 
    from .modules.my_content import my_content_bp 
    from .modules.my_content.flashcards import flashcards_bp 
    from .modules.my_content.quizzes import quizzes_bp 
    # DÒNG MỚI: Import Blueprint courses_bp từ module con my_content.courses
    from .modules.my_content.courses import courses_bp 
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_management_bp, url_prefix='/admin/users') 
    app.register_blueprint(user_profile_bp, url_prefix='/profile') 
    app.register_blueprint(my_content_bp, url_prefix='/my-content') 
    app.register_blueprint(flashcards_bp, url_prefix='/my-content/flashcards') 
    app.register_blueprint(quizzes_bp, url_prefix='/my-content/quizzes') 
    # DÒNG MỚI: Đăng ký Blueprint courses_bp
    # Nó sẽ có tiền tố URL là /my-content/courses
    app.register_blueprint(courses_bp, url_prefix='/my-content/courses') 

    with app.app_context():
        db.create_all()
        
        # Logic mới: Tạo user admin mặc định nếu chưa tồn tại
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user is None:
            admin = User(username='admin', user_role='admin')
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            print("Đã tạo user admin mặc định.")
            
    return app
