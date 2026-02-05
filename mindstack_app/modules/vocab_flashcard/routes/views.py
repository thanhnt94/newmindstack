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
from .. import blueprint as flashcard_learning_bp


# Import từ engine module
from ..services.query_builder import FlashcardQueryBuilder
from ..engine.config import FlashcardLearningConfig
from ..engine.algorithms import (
    get_new_only_items,
    get_due_items,
    get_hard_items,
    get_mixed_items,
    get_filtered_flashcard_sets,
    get_flashcard_mode_counts,
    get_accessible_flashcard_set_ids,
)
from ..engine.vocab_flashcard_mode import get_flashcard_mode_by_id

# Import external module interfaces
from mindstack_app.modules.session.interface import SessionInterface
from mindstack_app.modules.fsrs.interface import FSRSInterface
from mindstack_app.modules.vocabulary.services.stats_container import VocabularyStatsService
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
    
    mode_obj = get_flashcard_mode_by_id(mode)
    if mode_obj and hasattr(qb, mode_obj.filter_method):
        getattr(qb, mode_obj.filter_method)()
    else:
        qb.filter_mixed()
        
    total_items = qb.count()
    if total_items == 0:
        flash('Không có thẻ nào cho chế độ này.', 'warning')
        return redirect(url_for('vocabulary.dashboard'))

    # Create DB Session
    db_sess = SessionInterface.create_session(
        user_id=current_user.user_id,
        learning_mode='flashcard',
        mode_config_id=mode,
        set_id_data='all',
        total_items=total_items
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
    
    mode_obj = get_flashcard_mode_by_id(mode)
    if mode_obj and hasattr(qb, mode_obj.filter_method):
        getattr(qb, mode_obj.filter_method)()
    else:
        qb.filter_mixed()
        
    total_items = qb.count()
    if total_items == 0:
        flash('Không có thẻ nào cho chế độ này.', 'warning')
        return redirect(url_for('vocabulary.dashboard'))

    db_sess = SessionInterface.create_session(
        user_id=current_user.user_id,
        learning_mode='flashcard',
        mode_config_id=mode,
        set_id_data=set_ids, # List of ints
        total_items=total_items
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
    from mindstack_app.modules.learning.services.settings_service import LearningSettingsService
    config = LearningSettingsService.resolve_flashcard_session_config(current_user, set_id, request.args)
    
    session['flashcard_button_count_override'] = config['button_count']
    session['flashcard_visual_settings'] = config['visual_settings']

        
    # [REFACTORED] Stateless Session Start (Single ID)
    from ..services.query_builder import FlashcardQueryBuilder
    qb = FlashcardQueryBuilder(current_user.user_id)
    qb.filter_by_containers([set_id])
    
    mode_obj = get_flashcard_mode_by_id(mode)
    if mode_obj and hasattr(qb, mode_obj.filter_method):
        getattr(qb, mode_obj.filter_method)()
    else:
        qb.filter_mixed()
        
    total_items = qb.count()
    if total_items == 0:
        flash('Không có thẻ nào cho chế độ này.', 'warning')
        return redirect(url_for('vocabulary.dashboard'))

    db_sess = SessionInterface.create_session(
        user_id=current_user.user_id,
        learning_mode='flashcard',
        mode_config_id=mode,
        set_id_data=set_id, # Int
        total_items=total_items
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
    
    # [REFACTORED] Re-load session from DB (Stateless approach)
    should_reload = False
    if 'flashcard_session' not in session:
        should_reload = True
    else:
        # Verify if cookie matches URL
        cookie_data = session['flashcard_session']
        if cookie_data.get('db_session_id') != session_id:
            should_reload = True
            
    if should_reload:
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




    # [UPDATED v4] Priority: session override > User.last_preferences > session_state > default
    user_button_count = 4  # Default
    if 'flashcard_button_count_override' in session:
        user_button_count = session.get('flashcard_button_count_override')
    elif current_user.get_flashcard_button_count():
        user_button_count = current_user.get_flashcard_button_count()
    elif current_user.session_state:
        user_button_count = current_user.session_state.flashcard_button_count

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
    
    return render_dynamic_template(
        'modules/vocab_flashcard/session.html',
        user_button_count=user_button_count,
        is_autoplay_session=is_autoplay_session,
        autoplay_mode=autoplay_mode,
        container_name=container_name,
        mode_display_text=mode_display_text,
        saved_visual_settings=session.get('flashcard_visual_settings', {}),
        saved_auto_save=saved_auto_save,
        display_settings=display_settings
    )









@flashcard_learning_bp.route('/setup')
@login_required
def flashcard_setup():
    """Trang thiết lập trước khi bắt đầu phiên luyện tập."""
    from mindstack_app.modules.vocabulary.interface import VocabularyInterface
    from mindstack_app.modules.learning.services.settings_service import LearningSettingsService
    
    set_ids_str = request.args.get('sets', '')
    mode = request.args.get('mode', 'mixed_srs')
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
        saved_settings = LearningSettingsService.get_container_settings(current_user.user_id, set_id)
    else:
        # Default settings if multiple sets or 'all'
        saved_settings = {
            'last_mode': mode,
            'flashcard_button_count': 3
        }
            
    # Load Mode Counts
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
    mode = data.get('mode', 'mixed_srs')
    
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
        
    mode_obj = get_flashcard_mode_by_id(mode)
    if mode_obj and hasattr(qb, mode_obj.filter_method):
        getattr(qb, mode_obj.filter_method)()
    else:
        qb.filter_mixed()
        
    total_items = qb.count()
    if total_items == 0:
        flash('Không có thẻ nào.', 'warning')
        return redirect(url_for('vocabulary.dashboard'))

    db_sess = SessionInterface.create_session(
        user_id=current_user.user_id,
        learning_mode='flashcard',
        mode_config_id=mode,
        set_id_data=set_ids,
        total_items=total_items
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


