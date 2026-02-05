from flask import render_template, request, redirect, url_for, flash, abort, current_app
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from mindstack_app.models import LearningContainer, UserContainerState, LearningSession, LearningItem, db
# REFAC: Remove ItemMemoryState import
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsInterface
from .. import blueprint
from ..logics.typing_logic import get_typing_items
from datetime import datetime, timezone

@blueprint.route('/')
@login_required
def typing_dashboard():
    """Dashboard cho chế độ gõ từ."""
    # Lấy các bộ thẻ
    containers = LearningContainer.query.filter_by(
        container_type='FLASHCARD_SET',
        creator_user_id=current_user.user_id
    ).all()
    
    return render_dynamic_template('modules/learning/vocab_typing/dashboard.html', containers=containers)

@blueprint.route('/session')
@login_required
def typing_session_page():
    """Trang phiên học gõ từ."""
    # REFAC: Use FSRSInterface to get stats
    stats = FsrsInterface.get_memory_stats_by_type(current_user.user_id, 'FLASHCARD')
    
    count_review = stats.get('due', 0)
    count_learned = stats.get('total', 0) - stats.get('new', 0)
    
    return render_dynamic_template('modules/learning/vocab_typing/session/index.html',
        stats={
            'review_count': count_review,
            'learned_count': count_learned
        }
    )