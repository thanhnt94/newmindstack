# File: newmindstack/mindstack_app/modules/learning/routes.py
# Phiên bản: 1.2
# Mục đích: Đăng ký blueprint cho module học Course.
# ĐÃ THÊM: Import và đăng ký course_learning_bp.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

# Import các blueprint con
from .sub_modules.quiz import quiz_battle_bp, quiz_learning_bp
from .sub_modules.flashcard import flashcard_bp
from .sub_modules.flashcard.individual.routes import flashcard_learning_bp
from .sub_modules.course.routes import course_bp
from .sub_modules.flashcard.collab.routes import flashcard_collab_bp
from .sub_modules.vocabulary import vocabulary_bp
from .sub_modules.practice import practice_bp
from .sub_modules.collab import collab_bp
from .sub_modules.stats import stats_bp
# Note: stats_api_bp is registered globally in module_registry.py


# Định nghĩa Blueprint chính cho learning
learning_bp = Blueprint('learning', __name__,
                        template_folder='templates') # Các template chung cho learning (nếu có)

# Đăng ký các blueprint con
learning_bp.register_blueprint(quiz_learning_bp)
learning_bp.register_blueprint(flashcard_bp)
learning_bp.register_blueprint(flashcard_learning_bp)
learning_bp.register_blueprint(course_bp)
learning_bp.register_blueprint(quiz_battle_bp, url_prefix='/quiz-battle')
learning_bp.register_blueprint(flashcard_collab_bp)
learning_bp.register_blueprint(vocabulary_bp)
learning_bp.register_blueprint(practice_bp)  # NEW: Practice module
learning_bp.register_blueprint(collab_bp)  # NEW: Collab module
learning_bp.register_blueprint(stats_bp)  # Stats dashboard (HTML only, API is global)



@learning_bp.route('/')
@login_required
def learning_dashboard():
    """
    Mô tả: Hiển thị dashboard tổng quan cho các hoạt động học tập.
    Chuyển hướng đến trang stats dashboard.
    """
    return redirect(url_for('learning.stats.dashboard'))
