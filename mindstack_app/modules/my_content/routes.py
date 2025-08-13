# File: Mindstack/web/mindstack_app/modules/my_content/routes.py
# Version: 1.3 - Đã import Blueprint con courses
# Mục đích: Chứa các route và logic cho trang dashboard quản lý nội dung của người dùng.

from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user

# Import Blueprint từ __init__.py của module này
from . import my_content_bp 
# Import Blueprint con flashcards_bp
from .flashcards import flashcards_bp
# Import Blueprint con quizzes_bp
from .quizzes import quizzes_bp
# DÒNG MỚI: Import Blueprint con courses_bp
from .courses import courses_bp

# Middleware để đảm bảo người dùng đã đăng nhập cho toàn bộ Blueprint my_content
@my_content_bp.before_request
@login_required 
def content_management_required():
    # Không cần kiểm tra quyền admin ở đây, chỉ cần đã đăng nhập
    pass

# Route cho trang dashboard quản lý nội dung của người dùng
@my_content_bp.route('/')
@my_content_bp.route('/dashboard')
def my_content_dashboard():
    # Trang dashboard này sẽ hiển thị các liên kết đến quản lý Flashcard, Quiz, Course
    return render_template('my_content_dashboard.html')
