from flask import Blueprint, render_template, request
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import current_user, login_required
from ..engine.config import FlashcardLearningConfig

dashboard_bp = Blueprint(
    'flashcard_dashboard_internal',
    __name__,
)


def _build_dashboard_context(user):
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)

    # [UPDATED v3] Use session_state
    user_button_count = 3
    if user.session_state:
        user_button_count = user.session_state.flashcard_button_count

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

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    """Trang dashboard dùng chung cho Flashcard cá nhân và cộng tác."""

    template_vars = _build_dashboard_context(current_user)
    # Using 'dashboard/index.html' relative to the dashboard module's template folder
    # which maps to .../dashboard/templates/dashboard/index.html
    return render_dynamic_template('modules/learning/collab/flashcard/index.html', **template_vars)
