# File: mindstack_app/modules/vocab_flashcard/individual/routes.py
# Phiên bản: 4.0 (Engine refactor)
# MỤC ĐÍCH: Entry point routes cho chế độ học flashcard cá nhân.
# Routes này sử dụng engine module như dependency.

from flask import Blueprint, render_template, request, jsonify, abort, current_app, redirect, url_for, flash, session
from mindstack_app.utils.template_helpers import render_dynamic_template
from mindstack_app.utils.db_session import safe_commit
from flask_login import login_required, current_user
import traceback
import os

# Define Blueprint here
from .. import flashcard_bp as flashcard_learning_bp


# Import từ engine module
from ..services.query_builder import FlashcardQueryBuilder
from ..engine.config import FlashcardLearningConfig
from ..engine.algorithms import (
    get_filtered_flashcard_sets,
    get_flashcard_mode_counts,
    get_accessible_flashcard_set_ids,
)
from ..engine.vocab_flashcard_mode import get_flashcard_mode_by_id

# Import external module interfaces
from mindstack_app.modules.session.interface import SessionInterface
from mindstack_app.modules.fsrs.interface import FSRSInterface
from mindstack_app.modules.vocabulary.interface import VocabularyInterface
from ..engine.core import FlashcardEngine


from mindstack_app.models import LearningContainer, UserContainerState, db
from sqlalchemy.sql import func
from sqlalchemy.exc import OperationalError
import asyncio
from sqlalchemy.orm.attributes import flag_modified
import os
import shutil
import datetime

from mindstack_app.utils.media_paths import (
    normalize_media_value_for_storage,
    build_relative_media_path,
)


def _ensure_container_media_folder(container: LearningContainer, media_type: str) -> str:
    """Return the folder for the requested media type, creating a default if missing."""

    attr_name = f"media_{media_type}_folder"
    existing = getattr(container, attr_name, None)
    if existing:
        return existing

    type_slug = (container.container_type or "").lower()
    if type_slug.endswith("_set"):
        type_slug = type_slug[:-4]
    type_slug = type_slug.replace("_", "-") or "container"

    default_folder = f"{type_slug}/{container.container_id}/{media_type}"
    setattr(container, attr_name, default_folder)
    db.session.add(container)
    try:
        safe_commit(db.session)
    except Exception:  # pragma: no cover - commit failures bubble up
        db.session.rollback()
        raise

    return default_folder


def _user_can_edit_flashcard(container_id: int) -> bool:
    """Return True if the current user can edit items within the container."""

    if current_user.user_role == User.ROLE_ADMIN:
        return True

    container = LearningContainer.query.get(container_id)
    if not container:
        return False

    if container.creator_user_id == current_user.user_id:
        return True

    return (
        ContainerContributor.query.filter_by(
            container_id=container_id,
            user_id=current_user.user_id,
            permission_level="editor",
        ).first()
        is not None
    )



@flashcard_learning_bp.route('/start_flashcard_session/all/<string:mode>', methods=['GET'])
@login_required
def start_flashcard_session_all(mode):
    """
    Bắt đầu một phiên học Flashcard cho TẤT CẢ các bộ thẻ.
    """
    set_ids = 'all'

    # [UPDATED] Capture UI Preference
    ui_pref = request.args.get('flashcard_ui_pref')
    if ui_pref:
        session['flashcard_ui_pref'] = ui_pref

    # [REFACTORED] Stateless Session Start
    from ..services.query_builder import FlashcardQueryBuilder
    
    qb = FlashcardQueryBuilder(current_user.user_id)
    accessible_ids = get_accessible_flashcard_set_ids(current_user.user_id)
    qb.filter_by_containers(accessible_ids)
    
    mode_param = mode # Preserve original param
    if mode == 'mixed_srs':
        qb.filter_mixed()
        mode = 'srs' # Underlying FSRS mode
    elif mode == 'new':
        qb.filter_new_only()
        mode = 'srs'
    elif mode == 'review':
        qb.filter_due_only()
        mode = 'srs'
    elif mode == 'cram':
        # [NEW] Cram Mode: Random review of learned items
        qb.filter_cram()
        mode = 'cram' # We might need to handle this in session manager or just treat as custom
        # For now, let's treat it as 'flashcard' mode but with a special filter.
        # However, the session manager might expect 'srs'.
        # Let's check session interface and session manager logic.
        # Actually, query builder does the filtering. The mode passed to start_driven_session
        # determines the *behavior* (e.g. FSRS updates).
        # We want SRS updates DISABLED for cram mode (practice).
        # Our previous fix in SchedulerService disables FSRS if mode != 'flashcard'.
        # So we should pass 'cram' (or 'practice') as the learning_mode to start_driven_session?
        # No, start_driven_session takes `learning_mode`.
        # The `mode` in settings is just config.
        pass
    else:
        # Default SRS
        qb.filter_srs()
        mode = 'srs'
        
    total_items = qb.count()
    if total_items == 0:
        flash('Không có thẻ nào cho chế độ này.', 'warning')
        return redirect(url_for('vocab_flashcard.dashboard'))

    # [UPDATED] Use centralized Settings Service to resolve limits
    from mindstack_app.modules.learning.interface import LearningInterface
    session_config = LearningInterface.resolve_flashcard_session_config(
        user=current_user,
        container_id='all',
        url_params=request.args.to_dict()
    )
    new_limit = session_config.get('new_limit', 50)

    # Determine learning_mode for Session
    # If cram mode, we want to ensure FSRS updates are skipped.
    # Our SchedulerService fix checks if mode in ('flashcard', 'typing').
    # So if we pass 'cram', it will trigger only_count=True. Perfect.
    session_learning_mode = 'cram' if mode_param == 'cram' else 'flashcard'

    # Create DB Session using Driver API
    from mindstack_app.modules.session.interface import SessionInterface
    db_sess, driver_state = SessionInterface.start_driven_session(
        user_id=current_user.user_id,
        container_id='all',
        learning_mode=session_learning_mode,
        settings={'filter': mode_param, 'mode_config_id': mode, 'new_limit': new_limit}
    )
    
    if db_sess:
        # Set Cookie
        session['flashcard_session'] = {
            'user_id': current_user.user_id,
            'set_id': 'all',
            'mode': mode,
            'batch_size': 1, 
            'total_items_in_session': total_items, # Use DB count
            'processed_item_ids': [],
            'correct_answers': 0, 'incorrect_answers': 0, 'vague_answers': 0,
            'session_points': 0,
            'start_time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'db_session_id': db_sess.session_id,
            'current_item_id': None
        }
        session.modified = True
        return redirect(url_for('vocab_flashcard.flashcard_session', session_id=db_sess.session_id))
    else:
        flash('Lỗi khởi tạo phiên học.', 'danger')
        return redirect(url_for('vocabulary.dashboard'))


@flashcard_learning_bp.route('/start_flashcard_session/multi/<string:mode>', methods=['GET'])
@login_required
def start_flashcard_session_multi(mode):
    """
    Bắt đầu một phiên học Flashcard cho nhiều bộ thẻ.
    """
    set_ids_str = request.args.get('set_ids')

    if not set_ids_str:
        flash('Lỗi: Thiếu thông tin bộ thẻ.', 'danger')
        return redirect(url_for('vocabulary.dashboard'))

    try:
        set_ids = [int(s) for s in set_ids_str.split(',') if s]
    except ValueError:
        flash('Lỗi: Định dạng ID bộ thẻ không hợp lệ.', 'danger')
        return redirect(url_for('vocabulary.dashboard'))

    # [REFACTORED] Stateless Session Start (Multi)
    # ... (Simplified logic similar to 'all' but with specific set list)
    from ..services.query_builder import FlashcardQueryBuilder
    qb = FlashcardQueryBuilder(current_user.user_id)
    qb.filter_by_containers(set_ids)
    
    mode = 'srs'
    qb.filter_srs()
        
    total_items = qb.count()
    if total_items == 0:
        flash('Không có thẻ nào cho chế độ này.', 'warning')
        return redirect(url_for('vocabulary.dashboard'))

    # [UPDATED] Use centralized Settings Service
    from mindstack_app.modules.learning.interface import LearningInterface
    session_config = LearningInterface.resolve_flashcard_session_config(
        user=current_user,
        container_id=set_ids[0] if set_ids else 0,
        url_params=request.args.to_dict()
    )
    new_limit = session_config.get('new_limit', 50)

    # Create DB Session using Driver API
    from mindstack_app.modules.session.interface import SessionInterface
    # For multi-set, use first set as container_id (Driver will handle multi-set)
    container_id = set_ids[0] if isinstance(set_ids, list) and len(set_ids) > 0 else set_ids
    db_sess, driver_state = SessionInterface.start_driven_session(
        user_id=current_user.user_id,
        container_id=container_id,
        learning_mode='flashcard',
        settings={'filter': 'srs', 'mode_config_id': mode, 'set_ids': set_ids, 'new_limit': new_limit}
    )
    
    if db_sess:
        # Resolve container name for UI display
        if len(set_ids) == 1:
            container = LearningContainer.query.get(set_ids[0])
            container_name = container.title if container else 'Học tập'
        else:
            container_name = f"{len(set_ids)} bộ thẻ"
        
        session['flashcard_session'] = {
            'user_id': current_user.user_id,
            'set_id': set_ids,
            'mode': mode,
            'batch_size': 1,
            'total_items_in_session': total_items,
            'processed_item_ids': [], 'correct_answers': 0, 'incorrect_answers': 0, 'vague_answers': 0, 'session_points': 0,
            'start_time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'db_session_id': db_sess.session_id, 'current_item_id': None,
            'container_name': container_name
        }
        session.modified = True
        return redirect(url_for('vocab_flashcard.flashcard_session', session_id=db_sess.session_id))
    else:
        flash('Lỗi khởi tạo phiên học.', 'danger')
        return redirect(url_for('vocabulary.dashboard'))


@flashcard_learning_bp.route('/start_flashcard_session/<int:set_id>/<string:mode>', methods=['GET'])
@login_required
def start_flashcard_session_by_id(set_id, mode):
    """
    Bắt đầu một phiên học Flashcard cho một bộ thẻ cụ thể.
    """
    
    # [UPDATED v6] Use centralized Settings Service
    from mindstack_app.modules.learning.interface import LearningInterface
    # REFAC: Use Interface
    session_config = LearningInterface.resolve_flashcard_session_config(
        user=current_user,
        container_id=set_id,
        url_params=request.args.to_dict()
    )
    session['flashcard_button_count_override'] = session_config['button_count']
    session['flashcard_visual_settings'] = session_config['visual_settings']

        
    # [REFACTORED] Stateless Session Start (Single ID)
    from ..services.query_builder import FlashcardQueryBuilder
    qb = FlashcardQueryBuilder(current_user.user_id)
    qb.filter_by_containers([set_id])
    
    # Handle modes
    mode_param = mode # Preserve original param
    if mode == 'mixed_srs':
        qb.filter_mixed()
        mode = 'srs'
    elif mode == 'new':
        qb.filter_new_only()
        mode = 'srs'
    elif mode == 'review':
        qb.filter_due_only() # This is 'Due' review only?
        # Re-check views.py logic. 'review' usually maps to Due.
        # But for consistency with Cram Mode being "learned", we might want strict mapping.
        # The 'review' mode in UI usually means 'Due Review'.
        mode = 'srs'
    elif mode == 'cram':
        # Cram Mode: Random review of learned items
        qb.filter_cram()
        # Mode remains 'cram'
    else:
        # Default SRS
        qb.filter_srs()
        mode = 'srs'
        
    total_items = qb.count()
    if total_items == 0:
        flash('Không có thẻ nào cho chế độ này.', 'warning')
        return redirect(url_for('vocab_flashcard.dashboard'))

    # Determine learning_mode for Session
    # Cram is a sub-mode of Flashcard, handled by VocabularyDriver via settings['filter']
    session_learning_mode = 'flashcard'

    # Create DB Session using Driver API
    from mindstack_app.modules.session.interface import SessionInterface
    
    db_sess, driver_state = SessionInterface.start_driven_session(
        user_id=current_user.user_id,
        container_id=set_id,
        learning_mode=session_learning_mode,
        settings={'filter': mode_param, 'mode_config_id': mode, 'new_limit': session_config.get('new_limit', 50)}
    )
    
    if db_sess:
        # Resolve container name for UI display
        container = LearningContainer.query.get(set_id)
        container_name = container.title if container else 'Học tập'
        
        session['flashcard_session'] = {
            'user_id': current_user.user_id,
            'set_id': set_id,
            'mode': mode,
            'batch_size': 1,
            'total_items_in_session': total_items,
            'processed_item_ids': [], 'correct_answers': 0, 'incorrect_answers': 0, 'vague_answers': 0, 'session_points': 0,
            'start_time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'db_session_id': db_sess.session_id, 'current_item_id': None,
            'container_name': container_name
        }
        session.modified = True
        return redirect(url_for('vocab_flashcard.flashcard_session', session_id=db_sess.session_id))
    else:
        flash('Lỗi khởi tạo phiên học.', 'danger')
        return redirect(url_for('vocabulary.dashboard'))


@flashcard_learning_bp.route('/vocabulary/flashcard/session')
@login_required
def flashcard_session_legacy():
    # Attempt to find active session and redirect
    active_db_session = SessionInterface.get_active_session(current_user.user_id, learning_mode='flashcard')
    if active_db_session:
        return redirect(url_for('vocab_flashcard.flashcard_session', session_id=active_db_session.session_id))
        
    flash('Không có phiên học Flashcard nào đang hoạt động. Vui lòng chọn bộ thẻ để bắt đầu.', 'info')
    return redirect(url_for('vocabulary.dashboard'))


@flashcard_learning_bp.route('/vocabulary/flashcard/session/<int:session_id>')
@login_required
def flashcard_session(session_id):
    """
    Hiển thị giao diện học Flashcard.
    Sử dụng TemplateService để chọn template version từ admin settings.
    """
    
    # [REFACTORED] Always reload session from DB to ensure fresh stats (Stateless approach)
    # This prevents stale data in the Flask session cookie after API submissions.
    active_db_session = SessionInterface.get_session_by_id(session_id)
    
    # Security check
    if not active_db_session or active_db_session.user_id != current_user.user_id:
         flash('Phiên học không tồn tại hoặc bạn không có quyền truy cập.', 'error')
         return redirect(url_for('vocabulary.dashboard'))
        
    # Resolve container name from DB
    resolved_container_name = 'Học tập'
    set_id_data = active_db_session.set_id_data
    try:
        if isinstance(set_id_data, int):
            container = LearningContainer.query.get(set_id_data)
            if container:
                resolved_container_name = container.title
        elif isinstance(set_id_data, list) and len(set_id_data) > 0:
            if len(set_id_data) == 1:
                container = LearningContainer.query.get(set_id_data[0])
                if container:
                    resolved_container_name = container.title
            else:
                resolved_container_name = f"{len(set_id_data)} bộ thẻ"
    except Exception as e:
        current_app.logger.warning(f"Error resolving container name: {e}")
         
    # Reconstruct session dict directly from DB model
    session['flashcard_session'] = {
        'user_id': active_db_session.user_id,
        'set_id': active_db_session.set_id_data,
        'mode': active_db_session.mode_config_id,
        'batch_size': 1,
        'total_items_in_session': active_db_session.total_items,
        'processed_item_ids': active_db_session.processed_item_ids or [],
        'correct_answers': active_db_session.correct_count,
        'incorrect_answers': active_db_session.incorrect_count,
        'vague_answers': active_db_session.vague_count,
        'session_points': active_db_session.points_earned,
        'start_time': active_db_session.start_time.isoformat() if active_db_session.start_time else None,
        'db_session_id': active_db_session.session_id,
        'current_item_id': active_db_session.current_item_id,
        # UI display fields
        'container_name': resolved_container_name
    }
    session.modified = True
    current_app.logger.info(f"Reloaded session {session_id} from DB (Stateless).")




    # [UPDATED] Mandatory 4-button UI for SRS
    user_button_count = 4

    session_data = session.get('flashcard_session', {})
    session_mode = session_data.get('mode')
    is_autoplay_session = session_mode in ('autoplay_all', 'autoplay_learned')
    autoplay_mode = session_mode if is_autoplay_session else ''
    
    # Calculate Mode Display Text from Registry
    mode_obj = get_flashcard_mode_by_id(session_mode)
    mode_display_text = mode_obj.label if mode_obj else 'Phiên học'
    current_app.logger.debug(f"[FLASHCARD] session_mode: {session_mode}, mode_display_text: {mode_display_text}")
    autoplay_mode = session_mode if is_autoplay_session else ''

    # Get container name from session
    container_name = session_data.get('container_name', 'Bộ thẻ')
    
    # [NEW] Load auto_save flag for this container
    saved_auto_save = True
    try:
        container_id = session_data.get('set_id')
        if isinstance(container_id, int):
             uc_state = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=container_id).first()
             if uc_state and uc_state.settings:
                 saved_auto_save = uc_state.settings.get('auto_save', True)
    except Exception:
        pass
    
    # [NEW] Load display settings from container for Quick Formatting
    display_settings = {}
    try:
        container_id = session_data.get('set_id')
        if isinstance(container_id, int):
            container = LearningContainer.query.get(container_id)
            if container and container.settings:
                display_settings = container.settings.get('display', {})
    except Exception as e:
        current_app.logger.warning(f"Error loading display settings: {e}")
    
    # [NEW] Server-Side Initial Batch Load (SSR)
    initial_batch = []
    try:
        from ..engine.core import FlashcardEngine
        # Force batch_size=1 for standard flashcards, unless autoplay (which might want more, but let's stick to 1 for consistency)
        batch_limit = 1
        initial_batch_data = FlashcardEngine.get_next_batch(
            user_id=current_user.user_id,
            set_id=session_data.get('set_id'),
            mode=session_mode,
            processed_ids=session_data.get('processed_item_ids', []),
            db_session_id=session_id,
            batch_size=batch_limit,
            current_db_item_id=session_data.get('current_item_id')
        )
        if initial_batch_data and 'items' in initial_batch_data:
            initial_batch = initial_batch_data['items']
            # Update session total items if returned
            if 'total_items_in_session' in initial_batch_data:
                 session_data['total_items_in_session'] = initial_batch_data['total_items_in_session']
    except Exception as e:
        current_app.logger.error(f"Error fetching initial batch: {e}")

    return render_dynamic_template(
        'modules/vocab_flashcard/session.html',
        user_button_count=user_button_count,
        is_autoplay_session=is_autoplay_session,
        autoplay_mode=autoplay_mode,
        container_name=container_name,
        mode_display_text=mode_display_text,
        saved_visual_settings=session.get('flashcard_visual_settings', {}),
        saved_auto_save=saved_auto_save,
        display_settings=display_settings,
        initial_batch=initial_batch, # Pass to template
        db_session_id=session_id,    # Pass DB session ID for Driver API
        initial_processed_count=len(session_data.get('processed_item_ids', [])),
        initial_correct_count=session_data.get('correct_answers', 0),
        initial_incorrect_count=session_data.get('incorrect_answers', 0),
        initial_vague_count=session_data.get('vague_answers', 0),
        initial_session_points=session_data.get('session_points', 0),
    )









@flashcard_learning_bp.route('/setup')
@login_required
def flashcard_setup():
    """Trang thiết lập trước khi bắt đầu phiên luyện tập."""
    from mindstack_app.modules.vocabulary.interface import VocabularyInterface
    from mindstack_app.modules.learning.interface import LearningInterface
    
    set_ids_str = request.args.get('sets', '')
    mode = 'srs'
    context = request.args.get('context', 'vocab')
    
    selected_sets = []
    if set_ids_str:
        if set_ids_str != 'all':
            try:
                selected_sets = [int(s) for s in set_ids_str.split(',') if s]
            except ValueError:
                flash('Định dạng ID bộ thẻ không hợp lệ.', 'danger')
                return redirect(url_for('vocabulary.dashboard'))

    # For Wizard UI, prioritize single set details
    set_id = selected_sets[0] if len(selected_sets) == 1 else None
    
    container_title = "Tất cả các bộ thẻ"
    saved_settings = {}
    
    if set_id:
        # Use VocabularyInterface instead of direct DB query
        set_details = VocabularyInterface.get_set_detail(current_user.user_id, set_id)
        if set_details:
            container_title = set_details.set_info.title
        saved_settings = LearningInterface.get_container_settings(current_user.user_id, set_id)
    else:
        # Default settings if multiple sets or 'all'
        saved_settings = {
            'last_mode': mode,
            'flashcard_button_count': 3
        }
            
    # Load Mode Counts (Always SRS for Flashcard)
    set_identifier = set_id if set_id else (selected_sets if selected_sets else 'all')
    mode_counts = get_flashcard_mode_counts(current_user.user_id, set_identifier, context=context)
    
    # Get mode definitions for UI rendering
    from ..engine.vocab_flashcard_mode import get_flashcard_modes
    modes = get_flashcard_modes(context)

    # Render standardized template namespace
    return render_dynamic_template('modules/vocab_flashcard/setup.html',
        set_id=set_id or 'all',
        container_title=container_title,
        mode_counts=mode_counts,
        modes=modes,
        saved_settings=saved_settings,
        context=context
    )


@flashcard_learning_bp.route('/start', methods=['GET', 'POST'])
@login_required
def start():
    """Bắt đầu phiên luyện tập flashcard."""
    data = request.values or {}
    
    set_ids_str = data.get('set_ids', '')
    mode = 'srs'
    
    # Parse set IDs
    if set_ids_str == 'all':
        set_ids = 'all'
    elif set_ids_str:
        try:
            set_ids = [int(s) for s in set_ids_str.split(',') if s]
        except ValueError:
            flash('Định dạng ID bộ thẻ không hợp lệ.', 'danger')
            return redirect(url_for('vocabulary.dashboard'))
    else:
        flash('Vui lòng chọn ít nhất một bộ thẻ.', 'warning')
        return redirect(url_for('vocabulary.dashboard'))
    
    # [REFACTORED] Stateless Session Start (Generic)
    # Using 'set_ids' from request (parsed above)
    from ..services.query_builder import FlashcardQueryBuilder
    qb = FlashcardQueryBuilder(current_user.user_id)
    
    if set_ids == 'all':
        accessible = get_accessible_flashcard_set_ids(current_user.user_id)
        qb.filter_by_containers(accessible)
    else:
        # set_ids is list of ints
        qb.filter_by_containers(set_ids)
        
    # Always use SRS mode logic
    qb.filter_srs()
        
    total_items = qb.count()
    if total_items == 0:
        flash('Không có thẻ nào.', 'warning')
        return redirect(url_for('vocabulary.dashboard'))

    # Create DB Session using Driver API
    from mindstack_app.modules.session.interface import SessionInterface
    # Handle 'all' or list of set IDs
    if set_ids == 'all':
        container_id = 'all'
    elif isinstance(set_ids, list) and len(set_ids) > 0:
        container_id = set_ids[0]
    else:
        container_id = 'all'
    
    db_sess, driver_state = SessionInterface.start_driven_session(
        user_id=current_user.user_id,
        container_id=container_id,
        learning_mode='flashcard',
        settings={'filter': 'srs', 'set_ids': set_ids}
    )
    
    if db_sess:
        session['flashcard_session'] = {
            'user_id': current_user.user_id, 
            'set_id': set_ids,
            'mode': mode, 'batch_size': 1, 'total_items_in_session': total_items,
            'processed_item_ids': [], 'correct_answers': 0, 'incorrect_answers': 0, 'vague_answers': 0, 'session_points': 0,
            'start_time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'db_session_id': db_sess.session_id, 'current_item_id': None
        }
        session.modified = True
        return redirect(url_for('.flashcard_session', session_id=db_sess.session_id))
    else:
        flash('Lỗi khởi tạo.', 'danger')
        return redirect(url_for('vocabulary.dashboard'))



@flashcard_learning_bp.route('/')
@flashcard_learning_bp.route('/dashboard')
@login_required
def dashboard_home():
    """Redirect to vocabulary dashboard as this module now serves vocabulary directly."""
    return redirect(url_for('vocabulary.dashboard'))


@flashcard_learning_bp.route('/summary/<int:session_id>')
@login_required
def session_summary(session_id):
    """View summary of a completed session (Redirects to generic session summary)."""
    return redirect(url_for('session.session_summary', session_id=session_id))


