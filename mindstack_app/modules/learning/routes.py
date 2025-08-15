# File: newmindstack/mindstack_app/modules/learning/routes.py
# Phiên bản: 1.0
# Mục đích: Định nghĩa Blueprint chính cho module học tập và đăng ký các Blueprint con.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

# Import các blueprint con (sẽ được tạo sau)
from .quiz_learning.routes import quiz_learning_bp
# from .flashcard_learning.routes import flashcard_learning_bp # Sẽ import khi tạo module Flashcard Learning

# Định nghĩa Blueprint chính cho learning
learning_bp = Blueprint('learning', __name__,
                        template_folder='templates') # Các template chung cho learning (nếu có)

# Đăng ký các blueprint con
learning_bp.register_blueprint(quiz_learning_bp)
# learning_bp.register_blueprint(flashcard_learning_bp) # Sẽ đăng ký khi tạo module Flashcard Learning

@learning_bp.route('/')
@login_required
def learning_dashboard():
    """
    Hiển thị dashboard tổng quan cho các hoạt động học tập.
    Hiện tại sẽ chuyển hướng đến trang học Quiz.
    """
    # Tạm thời chuyển hướng đến trang học Quiz
    return redirect(url_for('learning.quiz_learning.quiz_learning_dashboard'))

