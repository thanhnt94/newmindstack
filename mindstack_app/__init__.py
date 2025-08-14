# File: web/mindstack_app/__init__.py
# Version: 2.0 (của chỉnh sửa hợp nhất content_management)
# Mục đích: Khởi tạo ứng dụng Flask, cấu hình, kết nối cơ sở dữ liệu và đăng ký các Blueprint.
#           Cập nhật để đăng ký Blueprint content_management_bp mới và loại bỏ các blueprint cũ
#           từ my_content và admin/content_management, đảm bảo ứng dụng hoạt động chính xác.

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
    # Đảm bảo import đúng đường dẫn tương đối

    # Các Blueprint không liên quan đến quản lý nội dung, giữ nguyên
    from .modules.auth.routes import auth_bp
    from .modules.main.routes import main_bp
    from .modules.admin import admin_bp 
    from .modules.admin.user_management.user_routes import user_management_bp # Đã sửa đường dẫn import
    from .modules.user_profile import user_profile_bp 
    
    # DÒNG MỚI: Import Blueprint quản lý nội dung hợp nhất
    from .modules.content_management.routes import content_management_bp

    # app.register_blueprint(auth_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth') # Đăng ký với url_prefix chuẩn

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_management_bp, url_prefix='/admin/users') 
    app.register_blueprint(user_profile_bp, url_prefix='/profile') 
    
    # DÒNG MỚI: Đăng ký Blueprint quản lý nội dung hợp nhất
    app.register_blueprint(content_management_bp, url_prefix='/content')

    # DÒNG CŨ ĐÃ BỊ LOẠI BỎ DO HỢP NHẤT LOGIC. Đảm bảo các import tương ứng cũng không còn.
    # Các dòng này sẽ bị loại bỏ hoàn toàn khỏi file gốc để tránh nhầm lẫn và code rác.
    # from .modules.my_content import my_content_bp
    # from .modules.my_content.flashcards import flashcards_bp
    # from .modules.my_content.quizzes import quizzes_bp
    # from .modules.my_content.courses import courses_bp
    # from .modules.admin.content_management import admin_content_bp
    # from .modules.admin.content_management.flashcards import admin_flashcards_bp
    # from .modules.admin.content_management.quizzes import admin_quizzes_bp
    # from .modules.admin.content_management.courses import admin_courses_bp
    
    # Các dòng đăng ký blueprint cũ đã loại bỏ
    # app.register_blueprint(my_content_bp, url_prefix='/my-content') 
    # app.register_blueprint(flashcards_bp, url_prefix='/my-content/flashcards') 
    # app.register_blueprint(quizzes_bp, url_prefix='/my-content/quizzes') 
    # app.register_blueprint(courses_bp, url_prefix='/my-content/courses') 
    # app.register_blueprint(admin_content_bp, url_prefix='/admin/content') 
    # app.register_blueprint(admin_flashcards_bp, url_prefix='/admin/content/flashcards')
    # app.register_blueprint(admin_quizzes_bp, url_prefix='/admin/content/quizzes') 
    # app.register_blueprint(admin_courses_bp, url_prefix='/admin/content/courses') 

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
