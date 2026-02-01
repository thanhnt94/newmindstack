# File: mindstack_app/modules/learning/routes/views.py
from flask import render_template, request, redirect, url_for, flash, abort, current_app
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from mindstack_app.models import LearningContainer, ReviewLog, LearningItem, db
from mindstack_app.modules.vocab_flashcard.services.session_service import LearningSessionService
from .. import learning_bp as blueprint

def get_mode_description(session):
    """Generate a detailed description for a learning session."""
    mode_map = {
        'new_only': 'Học từ mới',
        'due_only': 'Ôn tập tới hạn',
        'hard_only': 'Các từ khó',
        'mixed_srs': 'Học ngẫu nhiên (SRS)',
        'all_review': 'Ôn tập tất cả',
        'typing': 'Gõ từ',
        'listening': 'Nghe chép chính tả',
        'matching': 'Ghép thẻ',
        'mcq': 'Trắc nghiệm (MCQ Game)',
        'quiz': 'Trắc nghiệm (Quiz)'
    }
    base_name = mode_map.get(session.mode_config_id, session.mode_config_id)
    if session.learning_mode in ['typing', 'listening', 'mcq', 'quiz']:
        return f"{base_name} • {session.total_items} câu"
    return base_name

@blueprint.route('/')
@login_required
def learning_dashboard():
    """Redirect to stats dashboard."""
    return redirect(url_for('stats.dashboard'))

@blueprint.route('/practice')
@login_required
def practice_hub():
    """Hub trang chính cho Practice - chọn Flashcard hoặc Quiz."""
    return render_dynamic_template('modules/learning/practice/default/hub.html')

@blueprint.route('/practice/flashcard')
@login_required
def flashcard_dashboard():
    """Dashboard cho chế độ luyện tập flashcard."""
    from mindstack_app.modules.vocab_flashcard.engine.config import FlashcardLearningConfig
    user_button_count = 3
    if current_user.session_state:
        user_button_count = current_user.session_state.flashcard_button_count

    return render_dynamic_template('modules/learning/practice/default/dashboard.html',
        user_button_count=user_button_count,
        flashcard_modes=FlashcardLearningConfig.FLASHCARD_MODES,
    )
