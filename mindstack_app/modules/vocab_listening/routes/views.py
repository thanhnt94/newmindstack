# File: mindstack_app/modules/vocab_listening/routes/views.py
from flask import render_template, request, redirect, url_for, flash, abort, current_app
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from mindstack_app.models import LearningContainer, UserContainerState, LearningItem, db
from mindstack_app.modules.fsrs.models import ItemMemoryState
from .. import blueprint
from ..logics.listening_logic import get_listening_items
import random
from datetime import datetime, timezone

@blueprint.route('/')
@login_required
def listening_dashboard():
    """Dashboard cho chế độ luyện nghe."""
    # Lấy các bộ thẻ có thể học
    containers = LearningContainer.query.filter_by(
        container_type='FLASHCARD_SET',
        creator_user_id=current_user.user_id # Tạm thời chỉ lấy của chính mình
    ).all()
    
    return render_dynamic_template('modules/learning/vocab_listening/dashboard.html', containers=containers)

@blueprint.route('/session')
@login_required
def listening_session_page():
    """Trang phiên học luyện nghe."""
    # Logic thống kê sơ bộ để hiển thị (số lượng thẻ cần ôn)
    # Lấy tất cả item có thể nghe
    now = datetime.now(timezone.utc)
    base_query = LearningItem.query.filter(
        LearningItem.item_type == 'FLASHCARD'
    )
    
    # join với ItemMemoryState
    # Count due: due_date <= now
    count_review = base_query.join(ItemMemoryState).filter(
        ItemMemoryState.user_id == current_user.user_id,
        ItemMemoryState.due_date <= now
    ).count()
    
    # Count learned: state != NEW (0)
    count_learned = base_query.join(ItemMemoryState).filter(
        ItemMemoryState.user_id == current_user.user_id,
        ItemMemoryState.state != 0
    ).count()
    
    return render_dynamic_template('modules/learning/vocab_listening/session/index.html',
        stats={
            'review_count': count_review,
            'learned_count': count_learned
        }
    )