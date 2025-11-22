"""Shared Flashcard module definitions."""

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from .individual.config import FlashcardLearningConfig

flashcard_bp = Blueprint(
    'flashcard', __name__, url_prefix='/flashcard', template_folder='templates'
)


def _build_dashboard_context(user):
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)

    user_button_count = user.flashcard_button_count if user.flashcard_button_count else 3

    flashcard_set_search_options = {
        'title': 'Tiêu đề',
        'description': 'Mô tả',
        'tags': 'Thẻ',
    }

    return {
        'search_query': search_query,
        'search_field': search_field,
        'flashcard_set_search_options': flashcard_set_search_options,
        'current_filter': current_filter,
        'user_button_count': user_button_count,
        'flashcard_modes': FlashcardLearningConfig.FLASHCARD_MODES,
    }


@flashcard_bp.route('/')
@flashcard_bp.route('/dashboard')
@login_required
def dashboard():
    """Trang dashboard dùng chung cho Flashcard cá nhân và cộng tác."""

    template_vars = _build_dashboard_context(current_user)
    return render_template('dashboard.html', **template_vars)
