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
from ..engine.session_manager import FlashcardSessionManager
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

# Import từ services module
from ..services import AudioService, ImageService, LearningSessionService
from mindstack_app.modules.fsrs.interface import FSRSInterface
from mindstack_app.modules.vocabulary.services.stats_container import VocabularyStatsService
from mindstack_app.modules.fsrs.services.optimizer_service import FSRSOptimizerService
from ..engine.core import FlashcardEngine


from mindstack_app.models import LearningContainer, UserContainerState, ItemMemoryState, db
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
from mindstack_app.modules.fsrs.logics.fsrs_engine import FSRSEngine
from mindstack_app.modules.fsrs.schemas import CardStateDTO as CardState

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

    success, message, session_id = FlashcardSessionManager.start_new_flashcard_session(set_ids, mode)
    if success:
        return redirect(url_for('vocab_flashcard.flashcard_learning.flashcard_session', session_id=session_id))
    else:
        flash(message, 'warning')
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

    success, message, session_id = FlashcardSessionManager.start_new_flashcard_session(set_ids, mode)
    if success:
        return redirect(url_for('vocab_flashcard.flashcard_session', session_id=session_id))
    else:
        flash(message, 'warning')
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

        
    success, message, session_id = FlashcardSessionManager.start_new_flashcard_session(set_id, mode)
    if success:
        return redirect(url_for('vocab_flashcard.flashcard_session', session_id=session_id))
    else:
        flash(message, 'warning')
        return redirect(url_for('vocabulary.dashboard'))


@flashcard_learning_bp.route('/vocabulary/flashcard/session')
@login_required
def flashcard_session_legacy():
    # Attempt to find active session and redirect
    active_db_session = LearningSessionService.get_active_session(current_user.user_id, learning_mode='flashcard')
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
    
    # [NEW] Check if session matches URL ID
    should_reload = False
    if 'flashcard_session' not in session:
        should_reload = True
    else:
        current_session_data = session['flashcard_session']
        if current_session_data.get('db_session_id') != session_id:
            should_reload = True
            
    if should_reload:
        active_db_session = LearningSessionService.get_session_by_id(session_id)
        
        # Security check: User must own this session
        if not active_db_session or active_db_session.user_id != current_user.user_id:
             flash('Phiên học không tồn tại hoặc bạn không có quyền truy cập.', 'error')
             return redirect(url_for('vocabulary.dashboard'))
             
        # Reconstruct session manager from DB data
        session_manager = FlashcardSessionManager(
            user_id=active_db_session.user_id,
            set_id=active_db_session.set_id_data,
            mode=active_db_session.mode_config_id,
            batch_size=1,
            total_items_in_session=active_db_session.total_items,
            processed_item_ids=active_db_session.processed_item_ids or [],
            correct_answers=active_db_session.correct_count,
            incorrect_answers=active_db_session.incorrect_count,
            vague_answers=active_db_session.vague_count,
            start_time=active_db_session.start_time.isoformat() if active_db_session.start_time else None,
            session_points=active_db_session.points_earned,
            db_session_id=active_db_session.session_id
        )
        session['flashcard_session'] = session_manager.to_dict()
        session.modified = True
        current_app.logger.info(f"Reloaded session {session_id} from DB into Flask session.")




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
    
    # Calculate Mode Display Text
    # [UPDATED] Expanded map to match all modes and shorter labels
    mode_map = {
        'new_only': 'Học từ mới',
        'due_only': 'Ôn tập tới hạn',
        'hard_only': 'Từ khó',
        'mixed_srs': 'Học ngẫu nhiên',
        'preview': 'Xem trước',
        'all_review': 'Ôn tập tất cả',
        'autoplay_all': 'Tự động phát tất cả',
        'autoplay_learned': 'Tự động phát đã học',
        'pronunciation_practice': 'Luyện phát âm',
        'writing_practice': 'Luyện viết',
        'quiz_practice': 'Trắc nghiệm',
        'essay_practice': 'Tự luận',
        'listening_practice': 'Luyện nghe',
        'speaking_practice': 'Luyện nói'
    }
    mode_display_text = mode_map.get(session_mode, 'Phiên học')
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
def setup():
    """Trang thiết lập trước khi bắt đầu phiên luyện tập."""
    from mindstack_app.modules.vocabulary.interface import VocabularyInterface
    from mindstack_app.modules.learning.services.settings_service import LearningSettingsService
    
    set_ids_str = request.args.get('sets', '')
    mode = request.args.get('mode', 'mixed_srs')
    
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
        set_details = VocabularyInterface.get_set_details(set_id)
        if set_details:
            container_title = set_details.title
        saved_settings = LearningSettingsService.get_container_settings(current_user.user_id, set_id)
    else:
        # Default settings if multiple sets or 'all'
        saved_settings = {
            'last_mode': mode,
            'flashcard_button_count': 3
        }
            
    # Load Mode Counts
    set_identifier = set_id if set_id else (selected_sets if selected_sets else 'all')
    mode_counts = get_flashcard_mode_counts(current_user.user_id, set_identifier)

    # Render standardized template namespace
    return render_dynamic_template('modules/vocab_flashcard/setup.html',
        set_id=set_id or 'all',
        container_title=container_title,
        mode_counts=mode_counts,
        saved_settings=saved_settings
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
    
    # Bắt đầu session sử dụng flashcard engine
    success, message, session_id = FlashcardSessionManager.start_new_flashcard_session(set_ids, mode)
    if success:
        return redirect(url_for('.flashcard_session', session_id=session_id))
    else:
        flash(message, 'warning')
        return redirect(url_for('vocabulary.dashboard'))



@flashcard_learning_bp.route('/')
@flashcard_learning_bp.route('/dashboard')
@login_required
def dashboard_home():
    """Redirect to vocabulary dashboard as this module now serves vocabulary directly."""
    return redirect(url_for('vocabulary.dashboard'))


