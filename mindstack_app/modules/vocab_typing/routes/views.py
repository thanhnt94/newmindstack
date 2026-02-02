# File: mindstack_app/modules/vocab_typing/routes/views.py
from flask import render_template, request, redirect, url_for, flash, abort, current_app
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from mindstack_app.models import LearningContainer, UserContainerState, LearningSession, LearningItem, db
from mindstack_app.modules.fsrs.models import ItemMemoryState
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
    now = datetime.now(timezone.utc)
    base_query = LearningItem.query.filter(
        LearningItem.item_type == 'FLASHCARD'
    )
    
    count_review = base_query.join(ItemMemoryState).filter(
        ItemMemoryState.user_id == current_user.user_id,
        ItemMemoryState.due_date <= now
    ).count()
    
    count_learned = base_query.join(ItemMemoryState).filter(
        ItemMemoryState.user_id == current_user.user_id,
        ItemMemoryState.state != 0
    ).count()
    
    return render_dynamic_template('modules/learning/vocab_typing/session/index.html',
        stats={
            'review_count': count_review,
            'learned_count': count_learned
        }
    )