# File: newmindstack/mindstack_app/modules/learning/routes.py
# Phiên bản: 1.2
# Mục đích: Đăng ký blueprint cho module học Course.
# ĐÃ THÊM: Import và đăng ký course_learning_bp.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

# Import các blueprint con
from .quiz_learning.routes import quiz_learning_bp
from .flashcard_learning.routes import flashcard_learning_bp
from .course_learning.routes import course_learning_bp

# Định nghĩa Blueprint chính cho learning
learning_bp = Blueprint('learning', __name__,
                        template_folder='templates') # Các template chung cho learning (nếu có)

# Đăng ký các blueprint con
learning_bp.register_blueprint(quiz_learning_bp)
learning_bp.register_blueprint(flashcard_learning_bp)
learning_bp.register_blueprint(course_learning_bp)


@learning_bp.route('/')
@login_required
def learning_dashboard():
    """
    Mô tả: Hiển thị dashboard tổng quan cho các hoạt động học tập.
    Hiện tại sẽ chuyển hướng đến trang học Flashcard.
    """
    # Tạm thời chuyển hướng đến trang học Flashcard
    return redirect(url_for('learning.flashcard_learning.flashcard_learning_dashboard'))
