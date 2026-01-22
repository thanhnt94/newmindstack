# File: mindstack_app/modules/learning/flashcard/individual/routes.py
# Phiên bản: 4.0 (Engine refactor)
# MỤC ĐÍCH: Entry point routes cho chế độ học flashcard cá nhân.
# Routes này sử dụng engine module như dependency.

from flask import render_template, request, jsonify, abort, current_app, redirect, url_for, flash, session
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
import traceback
from . import flashcard_learning_bp

# Import từ engine module
from ..engine import (
    FlashcardSessionManager,
    FlashcardLearningConfig,
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
from mindstack_app.modules.learning.services.fsrs_service import FsrsService

from ..engine import FlashcardEngine
from mindstack_app.models import (
    db,
    User,
    UserContainerState,
    LearningContainer,
    LearningItem,
    ContainerContributor,
    LearningSession,
)
from sqlalchemy.sql import func
from sqlalchemy.exc import OperationalError
import asyncio
from sqlalchemy.orm.attributes import flag_modified
import os
import shutil

from mindstack_app.utils.media_paths import (
    normalize_media_value_for_storage,
    build_relative_media_path,
)
from mindstack_app.utils.db_session import safe_commit

audio_service = AudioService()
image_service = ImageService()


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


@flashcard_learning_bp.route('/assets/<path:filename>')
def serve_session_asset(filename):
    """Serve static assets from the templates directory dynamically based on version."""
    import os
    from flask import send_from_directory
    from mindstack_app.services.template_service import TemplateService
    
    # Get active version (e.g., 'v4')
    version = TemplateService.get_active_version()
    
    # Construct path: templates/{version}/pages/learning/vocabulary/flashcard/session
    assets_dir = os.path.join(current_app.root_path, 'templates', version, 'pages', 'learning', 'vocabulary', 'flashcard', 'session')
    
    try:
        return send_from_directory(assets_dir, filename)
    except Exception as e:
        current_app.logger.error(f"Error serving asset {filename} from {assets_dir}: {e}")
        abort(404)


@flashcard_learning_bp.route('/vocabulary/flashcard/setup/<int:set_id>')
@login_required
def setup(set_id):
    """Giao diện Setup Wizard cho Flashcard (thay thế URL trực tiếp cũ)."""
    container = LearningContainer.query.get_or_404(set_id)
    
    # Check access
    if not container.is_public and container.creator_user_id != current_user.user_id:
        from mindstack_app.modules.learning.sub_modules.flashcard.individual.routes import _user_can_edit_flashcard
        if not _user_can_edit_flashcard(set_id):
             abort(403)
        
    # Get Stats via Service
    from mindstack_app.modules.learning.sub_modules.vocabulary.stats import VocabularyStatsService
    try:
        mode_counts = VocabularyStatsService.get_mode_counts(current_user.user_id, set_id)
    except Exception:
        mode_counts = {'new': 0, 'due': 0, 'hard': 0, 'total': 0, 'learned': 0, 'review': 0, 'random': 0}
        
    # Get Saved Settings
    saved_settings = {}
    try:
        ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
        if ucs and ucs.settings:
            saved_settings = ucs.settings.get('flashcard', {})
    except Exception:
        pass

    return render_dynamic_template('pages/learning/vocabulary/flashcard/setup/index.html',
        set_id=set_id,
        container_title=container.title,
        mode_counts=mode_counts,
        saved_settings=saved_settings
    )



@flashcard_learning_bp.route('/get_flashcard_options_partial/<set_identifier>', methods=['GET'])
@login_required
def get_flashcard_options_partial(set_identifier):
    """
    Trả về partial HTML chứa các chế độ học và số nút đánh giá tương ứng.
    """
    selected_mode = request.args.get('selected_mode', None, type=str)
    # [UPDATED v3] Use session_state
    user_button_count = 3
    
    # 1. Start with Global/Session Preference
    if current_user.session_state:
        user_button_count = current_user.session_state.flashcard_button_count
        
    # 2. Override with Per-Set Persistence (if available for single set)
    if set_identifier != 'all' and ',' not in set_identifier:
        try:
            set_id = int(set_identifier)
            uc_state = UserContainerState.query.filter_by(
                user_id=current_user.user_id, 
                container_id=set_id
            ).first()
            if uc_state and uc_state.settings:
                flashcard_settings = uc_state.settings.get('flashcard', {})
                if 'button_count' in flashcard_settings:
                    user_button_count = flashcard_settings['button_count']
        except (ValueError, TypeError):
            pass
    
    modes = []
    
    if set_identifier == 'all':
        modes = get_flashcard_mode_counts(current_user.user_id, 'all')
    else:
        try:
            set_ids = [int(s) for s in set_identifier.split(',') if s]
            if len(set_ids) == 1:
                # THAY ĐỔI: Lấy phần tử đầu tiên của danh sách
                modes = get_flashcard_mode_counts(current_user.user_id, set_ids[0])
            else:
                modes = get_flashcard_mode_counts(current_user.user_id, set_ids)
        except ValueError:
            return '<p class="text-red-500 text-center">Lỗi: Định dạng ID bộ thẻ không hợp lệ.</p>', 400
        except IndexError:
            return '<p class="text-red-500 text-center">Lỗi: Không tìm thấy ID bộ thẻ.</p>', 400


    return render_dynamic_template('pages/learning/collab/flashcard/_modes_list.html',
                           modes=modes,
                           selected_set_id=set_identifier,
                           selected_flashcard_mode_id=selected_mode,
                           user_button_count=user_button_count
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

    success, message = FlashcardSessionManager.start_new_flashcard_session(set_ids, mode)
    if success:
        return redirect(url_for('learning.flashcard_learning.flashcard_session'))
    else:
        flash(message, 'warning')
        return redirect(url_for('learning.vocabulary.dashboard'))


@flashcard_learning_bp.route('/start_flashcard_session/multi/<string:mode>', methods=['GET'])
@login_required
def start_flashcard_session_multi(mode):
    """
    Bắt đầu một phiên học Flashcard cho nhiều bộ thẻ.
    """
    set_ids_str = request.args.get('set_ids')

    if not set_ids_str:
        flash('Lỗi: Thiếu thông tin bộ thẻ.', 'danger')
        return redirect(url_for('learning.vocabulary.dashboard'))

    try:
        set_ids = [int(s) for s in set_ids_str.split(',') if s]
    except ValueError:
        flash('Lỗi: Định dạng ID bộ thẻ không hợp lệ.', 'danger')
        return redirect(url_for('learning.vocabulary.dashboard'))

    success, message = FlashcardSessionManager.start_new_flashcard_session(set_ids, mode)
    if success:
        return redirect(url_for('learning.flashcard_learning.flashcard_session'))
    else:
        flash(message, 'warning')
        return redirect(url_for('learning.vocabulary.dashboard'))


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

        
    success, message = FlashcardSessionManager.start_new_flashcard_session(set_id, mode)
    if success:
        return redirect(url_for('learning.flashcard_learning.flashcard_session'))
    else:
        flash(message, 'warning')
        return redirect(url_for('learning.vocabulary.dashboard'))


@flashcard_learning_bp.route('/vocabulary/flashcard/session')
@login_required
def flashcard_session():
    """
    Hiển thị giao diện học Flashcard.
    Sử dụng TemplateService để chọn template version từ admin settings.
    """
    # [NEW] Attempt to resume session from database if Flask session is empty
    if 'flashcard_session' not in session:
        active_db_session = LearningSessionService.get_active_session(current_user.user_id, learning_mode='flashcard')
        if active_db_session:
            # Reconstruct session manager from DB data
            session_manager = FlashcardSessionManager(
                user_id=active_db_session.user_id,
                set_id=active_db_session.set_id_data,
                mode=active_db_session.mode_config_id,
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
            flash('Đã khôi phục phiên học đang dở của bạn.', 'info')
        else:
            flash('Không có phiên học Flashcard nào đang hoạt động. Vui lòng chọn bộ thẻ để bắt đầu.', 'info')
            return redirect(url_for('learning.vocabulary.dashboard'))

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
        'pages/learning/vocabulary/flashcard/session/index.html',
        user_button_count=user_button_count,
        is_autoplay_session=is_autoplay_session,
        autoplay_mode=autoplay_mode,
        container_name=container_name,
        mode_display_text=mode_display_text,
        saved_visual_settings=session.get('flashcard_visual_settings', {}),
        saved_auto_save=saved_auto_save,
        display_settings=display_settings
    )


@flashcard_learning_bp.route('/get_flashcard_batch', methods=['GET'])
@login_required
def get_flashcard_batch():
    """
    Trả về dữ liệu nhóm thẻ tiếp theo trong phiên học hiện tại.
    """
    current_app.logger.debug("--- Bắt đầu get_flashcard_batch ---")
    if 'flashcard_session' not in session:
        current_app.logger.warning("Phiên học không hợp lệ hoặc đã kết thúc khi gọi get_flashcard_batch.")
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 404

    session_manager = FlashcardSessionManager.from_dict(session['flashcard_session'])
    
    try:
        flashcard_batch = session_manager.get_next_batch()
        
        session['flashcard_session'] = session_manager.to_dict()
        session.modified = True

        if flashcard_batch is None:
            session_manager.end_flashcard_session()
            current_app.logger.info(f"Phiên học Flashcard cho người dùng {current_user.user_id} đã kết thúc do hết thẻ.")
            current_app.logger.debug("--- Kết thúc get_flashcard_batch (Hết thẻ) ---")
            return jsonify({'message': 'Bạn đã hoàn thành tất cả các thẻ trong phiên học này!'}), 404
        
        # Add session stats to batch response
        flashcard_batch['session_correct_answers'] = session_manager.correct_answers
        flashcard_batch['session_incorrect_answers'] = session_manager.incorrect_answers
        flashcard_batch['session_vague_answers'] = session_manager.vague_answers
        flashcard_batch['session_total_answered'] = session_manager.correct_answers + session_manager.incorrect_answers + session_manager.vague_answers
        flashcard_batch['session_points'] = session_manager.session_points  # NEW: Include session points
        
        # Add additional fields for mobile stats view
        flashcard_batch['session_total_items'] = session_manager.total_items_in_session
        # Use answered count (not fetched count) for progress to prevent increment on refresh
        answered_count = session_manager.correct_answers + session_manager.incorrect_answers + session_manager.vague_answers
        flashcard_batch['session_processed_count'] = answered_count + 1  # +1 for current card being shown
        
        # Add container name
        container_name = ''
        set_id = session_manager.set_id
        current_app.logger.debug(f"Container name lookup - set_id: {set_id}, type: {type(set_id)}")
        
        if set_id:
            try:
                from mindstack_app.models import LearningContainer
                
                # Handle different set_id types
                if set_id == 'all':
                    container_name = 'Tất cả bộ thẻ'
                elif isinstance(set_id, (int, str)):
                    # Convert string to int if needed
                    try:
                        numeric_id = int(set_id)
                        container = LearningContainer.query.get(numeric_id)
                        if container:
                            container_name = container.title or ''
                            current_app.logger.debug(f"Found container: {container_name}")
                    except (ValueError, TypeError):
                        pass
                elif isinstance(set_id, list):
                    if len(set_id) == 1:
                        try:
                            numeric_id = int(set_id[0])
                            container = LearningContainer.query.get(numeric_id)
                            if container:
                                container_name = container.title or ''
                        except (ValueError, TypeError):
                            pass
                    elif len(set_id) > 1:
                        container_name = f'{len(set_id)} bộ thẻ'
            except Exception as e:
                current_app.logger.warning(f"Error getting container name: {e}")
                container_name = ''
        
        flashcard_batch['container_name'] = container_name or 'Bộ thẻ'

        current_app.logger.debug("--- Kết thúc get_flashcard_batch (Thành công) ---")
        return jsonify(flashcard_batch)

    except Exception as e:
        current_app.logger.error(f"LỖI NGHIÊM TRỌNG khi lấy nhóm thẻ: {e}", exc_info=True)
        current_app.logger.debug("--- Kết thúc get_flashcard_batch (LỖI) ---")
        return jsonify({'message': f'Lỗi khi tải thẻ: {str(e)}'}), 500


@flashcard_learning_bp.route('/flashcard_learning/api/items/<int:item_id>', methods=['GET'])
@login_required
def get_flashcard_item_api(item_id):
    """Trả về thông tin chi tiết của một thẻ trong phiên học hiện tại."""

    if 'flashcard_session' not in session:
        return jsonify({'success': False, 'message': 'Không có phiên học nào đang hoạt động.'}), 400

    try:
        item = LearningItem.query.filter_by(item_id=item_id, item_type='FLASHCARD').first()
        if not item:
            return jsonify({'success': False, 'message': 'Không tìm thấy thẻ yêu cầu.'}), 404

        accessible_set_ids = set(get_accessible_flashcard_set_ids(current_user.user_id))
        if accessible_set_ids and item.container_id not in accessible_set_ids:
            return jsonify({'success': False, 'message': 'Bạn không có quyền truy cập thẻ này.'}), 403

        container = item.container if item else None
        media_folders = {}
        if container:
            media_folders = dict(getattr(container, 'media_folders', {}) or {})
            if not media_folders:
                settings_payload = container.ai_settings or {}
                if isinstance(settings_payload, dict):
                    media_folders = dict(settings_payload.get('media_folders') or {})

        def resolve_media_url(file_path, media_type=None):
            if not file_path:
                return None
            try:
                relative_path = build_relative_media_path(file_path, media_folders.get(media_type) if media_type else None)
                if not relative_path:
                    return None
                if relative_path.startswith(('http://', 'https://')):
                    return relative_path
                if relative_path.startswith('/'):
                    return url_for('static', filename=relative_path.lstrip('/'), _external=True)
                return url_for('static', filename=relative_path, _external=True)
            except Exception:
                return None

        initial_stats = FlashcardEngine.get_item_statistics(current_user.user_id, item_id)

        item_payload = {
            'item_id': item.item_id,
            'container_id': item.container_id,
            'content': {
                'front': item.content.get('front', ''),
                'back': item.content.get('back', ''),
                'front_audio_content': item.content.get('front_audio_content', ''),
                'front_audio_url': resolve_media_url(item.content.get('front_audio_url'), 'audio'),
                'back_audio_content': item.content.get('back_audio_content', ''),
                'back_audio_url': resolve_media_url(item.content.get('back_audio_url'), 'audio'),
                'front_img': resolve_media_url(item.content.get('front_img'), 'image'),
                'back_img': resolve_media_url(item.content.get('back_img'), 'image'),
            },
            'ai_explanation': item.ai_explanation,
            'initial_stats': initial_stats,
        }

        return jsonify({'success': True, 'item': item_payload})
    except Exception as exc:
        current_app.logger.error('Lỗi khi tải thông tin thẻ %s: %s', item_id, exc, exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi tải lại thẻ.'}), 500


@flashcard_learning_bp.route('/submit_flashcard_answer', methods=['POST'])
@login_required
def submit_flashcard_answer():
    """
    Nhận câu trả lời của người dùng, xử lý và cập nhật tiến độ.
    """
    current_app.logger.debug("--- Bắt đầu submit_flashcard_answer ---")
    data = request.get_json()
    item_id = data.get('item_id')
    user_answer = data.get('user_answer')

    if not item_id or not user_answer:
        current_app.logger.warning("Dữ liệu đáp án không hợp lệ khi submit_flashcard_answer.")
        return jsonify({'error': 'Dữ liệu đáp án không hợp lệ.'}), 400

    if 'flashcard_session' not in session:
        current_app.logger.warning("Không tìm thấy phiên học trong session khi submit_flashcard_answer.")
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 400

    session_manager = FlashcardSessionManager.from_dict(session['flashcard_session'])
    if not session_manager:
        current_app.logger.warning("Không tìm thấy SessionManager khi submit_flashcard_answer.")
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 400

    set_ids = session_manager.set_id
    if not isinstance(set_ids, list):
        if set_ids == 'all':
            pass
        else:
            set_ids = [set_ids]

    if set_ids and set_ids != ['all']:
        pending_state_update = False
        try:
            for s_id in set_ids:
                user_container_state = UserContainerState.query.filter_by(
                    user_id=current_user.user_id,
                    container_id=s_id
                ).first()
                if not user_container_state:
                    user_container_state = UserContainerState(
                        user_id=current_user.user_id,
                        container_id=s_id,
                        is_archived=False,
                        is_favorite=False
                    )
                    db.session.add(user_container_state)
                user_container_state.last_accessed = func.now()
                pending_state_update = True

            if pending_state_update:
                safe_commit(db.session)
        except OperationalError as exc:
            current_app.logger.warning(
                "Không thể cập nhật last_accessed cho các bộ thẻ %s do cơ sở dữ liệu đang bận: %s",
                set_ids,
                exc,
                exc_info=True,
            )
            db.session.rollback()
        except Exception as exc:  # pylint: disable=broad-except
            db.session.rollback()
            current_app.logger.error(
                "Lỗi khi cập nhật last_accessed cho các bộ thẻ %s: %s",
                set_ids,
                exc,
                exc_info=True,
            )
                
    # [UPDATED v4] Priority: session override > User.last_preferences > session_state > default
    user_button_count = 4  # Default
    if 'flashcard_button_count_override' in session:
        user_button_count = session.get('flashcard_button_count_override')
    elif current_user.get_flashcard_button_count():
        user_button_count = current_user.get_flashcard_button_count()
    elif current_user.session_state:
        user_button_count = current_user.session_state.flashcard_button_count

    normalized_answer = str(user_answer).lower()

    if normalized_answer == 'continue':
        user_answer_quality = None
    else:
        quality_map = {}

        # [FSRS] Map button names to FSRS ratings 1-4
        if user_button_count == 3:
            # 3-button legacy: map to FSRS 1, 2, 3
            quality_map = {'quên': 1, 'mơ_hồ': 2, 'nhớ': 3}
        elif user_button_count == 4:
            # Standard FSRS 4-button: Again=1, Hard=2, Good=3, Easy=4
            quality_map = {'again': 1, 'hard': 2, 'good': 3, 'easy': 4}
        elif user_button_count == 6:
            # 6-button: map to FSRS range
            quality_map = {'fail': 1, 'very_hard': 1, 'hard': 2, 'medium': 3, 'good': 3, 'very_easy': 4}

        user_answer_quality = quality_map.get(normalized_answer, 3)  # Default to Good if unknown

    duration_ms = data.get('duration_ms', 0)
    result = session_manager.process_flashcard_answer(
        item_id, user_answer_quality, 
        duration_ms=duration_ms, 
        user_answer_text=user_answer
    )
    if 'error' in result:
        current_app.logger.error(f"Lỗi trong quá trình process_flashcard_answer: {result.get('error')}")
        return jsonify(result), 400

    session['flashcard_session'] = session_manager.to_dict()

    response_data = {
        'success': True,
        'score_change': result.get('score_change'),
        'updated_total_score': result.get('updated_total_score'),
        'is_correct': result.get('is_correct'),
        'new_progress_status': result.get('new_progress_status'),
        'statistics': result.get('statistics'),
        'memory_power': result.get('memory_power'),  # NEW: Pass memory power data
        'session_correct_answers': session_manager.correct_answers,
        'session_incorrect_answers': session_manager.incorrect_answers,
        'session_vague_answers': session_manager.vague_answers,
        'session_total_answered': session_manager.correct_answers + session_manager.incorrect_answers + session_manager.vague_answers,
        'session_points': result.get('session_points', session_manager.session_points)  # NEW: Include session points
    }

    current_app.logger.debug("--- Kết thúc submit_flashcard_answer (Thành công) ---")
    return jsonify(response_data)


@flashcard_learning_bp.route('/end_session_flashcard', methods=['POST'])
@login_required
def end_session_flashcard():
    """
    Kết thúc phiên học Flashcard hiện tại.
    """
    current_app.logger.debug("--- Bắt đầu end_session_flashcard ---")
    
    # Capture Session ID before ending
    db_session_id = None
    if 'flashcard_session' in session:
        db_session_id = session['flashcard_session'].get('db_session_id')
        
    result = FlashcardSessionManager.end_flashcard_session()
    
    if db_session_id:
        result['session_id'] = db_session_id
        
    current_app.logger.info(f"Phiên học Flashcard cho người dùng {current_user.user_id} đã kết thúc theo yêu cầu. Kết quả: {result.get('message')}")
    current_app.logger.debug("--- Kết thúc end_session_flashcard ---")
    return jsonify(result)


@flashcard_learning_bp.route('/api/check_active_vocab_session/<int:set_id>', methods=['GET'])
@login_required
def check_active_vocab_session(set_id):
    """
    Check if there is ANY active vocabulary session for this set.
    Returns details of the active session if found.
    """
    active_session = LearningSessionService.get_any_active_vocabulary_session(current_user.user_id, set_id)
    
    if active_session:
        # Determine URL to resume
        resume_url = '#'
        mode = active_session.learning_mode
        if mode == 'flashcard':
            resume_url = url_for('learning.flashcard_learning.flashcard_session')
        elif mode == 'mcq':
             # MCQ Session requires set_id
             resume_url = url_for('learning.vocabulary.mcq.session', set_id=set_id)
        elif mode == 'typing':
             resume_url = url_for('learning.vocabulary.typing.session_page')
        elif mode == 'listening':
             # Listening Session requires set_id
             resume_url = url_for('learning.vocabulary.listening.session', set_id=set_id)
        elif mode == 'matching':
             resume_url = url_for('learning.vocabulary.matching.session', set_id=set_id)
        elif mode == 'speed':
             resume_url = url_for('learning.vocabulary.speed.session_page', set_id=set_id)
             
        # Map nice names
        mode_names = {
            'flashcard': 'Flashcard',
            'mcq': 'Trắc nghiệm (MCQ)',
            'typing': 'Gõ từ (Typing)',
            'listening': 'Luyện nghe',
            'matching': 'Nối từ',
            'speed': 'Ôn nhanh (Speed)'
        }
        
        return jsonify({
            'has_active': True,
            'active_mode': mode,
            'active_mode_display': mode_names.get(mode, mode),
            'resume_url': resume_url
        })
    
    return jsonify({'has_active': False})


@flashcard_learning_bp.route('/api/learning/sessions/active', methods=['GET'])
@login_required
def get_active_learning_session():
    """Check if there is an active learning session for the current user."""
    mode = request.args.get('mode', 'flashcard')
    active_session = LearningSessionService.get_active_session(current_user.user_id, learning_mode=mode)
    
    if active_session:
        data = active_session.to_dict()
        
        # [NEW] Add set title for UI display
        try:
            from mindstack_app.models import LearningContainer
            set_id = active_session.set_id_data
            if isinstance(set_id, int):
                container = LearningContainer.query.get(set_id)
                if container:
                    data['set_title'] = container.title
            elif isinstance(set_id, list):
                if len(set_id) == 1:
                    container = LearningContainer.query.get(set_id[0])
                    if container:
                        data['set_title'] = container.title
                else:
                    data['set_title'] = f"{len(set_id)} bộ thẻ"
            elif set_id == 'all':
                data['set_title'] = "Tất cả bộ thẻ"
        except Exception as e:
            current_app.logger.warning(f"Error getting set title for active session: {e}")
            
        return jsonify({
            'has_active': True,
            'session': data
        })
    
    return jsonify({'has_active': False})


@flashcard_learning_bp.route('/save_flashcard_settings', methods=['POST'])
@login_required
def save_flashcard_settings():
    """
    Lưu cài đặt số nút đánh giá VÀ visual settings (autoplay, image, stats) cho bộ thẻ HIỆN TẠI.
    [UPDATED v5] Supports per-set persistence via UserContainerState.
    """
    data = request.get_json()
    
    # 1. Button Count
    button_count = data.get('button_count')
    set_id_from_payload = data.get('set_id') # New: Explicit set_id from setup page
    
    # 2. Visual Settings
    visual_settings = data.get('visual_settings') # { 'autoplay': bool, 'show_image': bool, 'show_stats': bool }
    
    # Validation
    if button_count and (not isinstance(button_count, int) or button_count not in [3, 4, 6]):
        return jsonify({'success': False, 'message': 'Số nút đánh giá không hợp lệ.'}), 400


    from mindstack_app.modules.learning.services.settings_service import LearningSettingsService
    
    # Determine target sets: Payload (Explicit) > Session (Implicit)
    target_set_ids = []
    
    # Priority 1: Explicit ID from payload
    if set_id_from_payload:
        if isinstance(set_id_from_payload, int):
            target_set_ids = [set_id_from_payload]
        elif isinstance(set_id_from_payload, list):
             target_set_ids = [int(x) for x in set_id_from_payload if str(x).isdigit()]
    
    # Priority 2: Fallback to active Session
    if not target_set_ids:
        session_data = session.get('flashcard_session', {})
        set_ids = session_data.get('set_id')
        target_set_ids = [set_ids] if isinstance(set_ids, int) else (set_ids if isinstance(set_ids, list) else [])
    
    update_payload = {'flashcard': {}}
    if button_count: update_payload['flashcard']['button_count'] = button_count
    if visual_settings:
        for k, v in visual_settings.items():
            if k in ['autoplay', 'show_image', 'show_stats']:
                update_payload['flashcard'][k] = v

    try:
        # 1. Update Session and Transient State
        if button_count:
            session['flashcard_button_count_override'] = button_count
            if current_user.session_state:
                 current_user.session_state.flashcard_button_count = button_count
        
        if visual_settings:
            session['flashcard_visual_settings'] = visual_settings

        # 2. Update Per-Set Persistence
        for sid in target_set_ids:
            if isinstance(sid, int):
                LearningSettingsService.update_container_settings(current_user.user_id, sid, update_payload)
                
        return jsonify({'success': True, 'message': 'Cài đặt đã được lưu.'})
    except Exception as e:
        current_app.logger.error(f"Lỗi khi lưu cài đặt Flashcard: {e}")
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi lưu cài đặt.'}), 500



@flashcard_learning_bp.route('/get_flashcard_sets_partial', methods=['GET'])
@login_required
def get_flashcard_sets_partial():
    """
    Trả về partial HTML chứa danh sách các bộ Flashcard, có hỗ trợ tìm kiếm và phân trang.
    """
    current_app.logger.debug(">>> Bắt đầu thực thi get_flashcard_sets_partial <<<")
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)

    try:
        pagination = get_filtered_flashcard_sets(
            user_id=current_user.user_id,
            search_query=search_query,
            search_field=search_field,
            current_filter=current_filter,
            per_page=current_app.config['ITEMS_PER_PAGE'],
            page=page
        )
        flashcard_sets = pagination.items

        # Calculate stats for each set
        stats_map = {}
        for f_set in flashcard_sets:
            try:
                # Assuming flashcard mode for now
                stats = FsrsService.get_container_stats(current_user.user_id, f_set.container_id, 'flashcard')
                # Format memory power as percentage
                stats['memory_power'] = round((stats.get('average_memory_power') or 0) * 100, 1)
                stats_map[f_set.container_id] = stats
            except Exception as e:
                current_app.logger.warning(f"Failed to calculate stats for set {f_set.container_id}: {e}")
                stats_map[f_set.container_id] = {'memory_power': 0, 'total_items': 0}

        template_vars = {
            'flashcard_sets': flashcard_sets,
            'pagination': pagination,
            'search_query': search_query,
            'search_field': search_field,
            'search_options_display': {
                'title': 'Tiêu đề', 'description': 'Mô tả', 'tags': 'Thẻ'
            },
            'current_filter': current_filter,
            'stats_map': stats_map
        }

        current_app.logger.debug("<<< Kết thúc thực thi get_flashcard_sets_partial (Thành công) >>>")
        return render_dynamic_template('pages/learning/collab/flashcard/_sets_list.html', **template_vars)

    except Exception as e:
        print(f">>> PYTHON LỖI: Đã xảy ra lỗi trong get_flashcard_sets_partial: {e}")
        print(traceback.format_exc())
        current_app.logger.error(f"LỖI NGHIÊM TRỌNG khi tải danh sách bộ thẻ qua AJAX: {e}", exc_info=True)
        current_app.logger.debug("<<< Kết thúc thực thi get_flashcard_sets_partial (LỖI) >>>")
        return '<p class="text-red-500 text-center py-4">Đã xảy ra lỗi khi tải danh sách bộ thẻ. Vui lòng thử lại.</p>', 500


@flashcard_learning_bp.route('/toggle_archive_flashcard/<int:set_id>', methods=['POST'])
@login_required
def toggle_archive_flashcard(set_id):
    """
    Xử lý yêu cầu archive hoặc unarchive một bộ thẻ.
    """
    try:
        user_container_state = UserContainerState.query.filter_by(
            user_id=current_user.user_id,
            container_id=set_id
        ).first()

        is_currently_archived = False
        if user_container_state:
            user_container_state.is_archived = not user_container_state.is_archived
            is_currently_archived = user_container_state.is_archived
        else:
            user_container_state = UserContainerState(
                user_id=current_user.user_id,
                container_id=set_id,
                is_archived=True,
                is_favorite=False
            )
            db.session.add(user_container_state)
            is_currently_archived = True

        safe_commit(db.session)
        
        status_text = "đã được lưu trữ." if is_currently_archived else "đã được bỏ lưu trữ."
        flash(f'Bộ thẻ "{set_id}" {status_text}', 'success')

        return jsonify({'success': True, 'is_archived': is_currently_archived, 'message': f'Bộ thẻ {status_text}'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi toggle archive cho bộ thẻ {set_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi thay đổi trạng thái lưu trữ.'}), 500


@flashcard_learning_bp.route('/bulk_unarchive_flashcard', methods=['POST'])
@login_required
def bulk_unarchive_flashcard():
    """
    Xử lý yêu cầu bỏ lưu trữ hàng loạt cho các bộ thẻ đã chọn.
    """
    data = request.get_json()
    set_ids = data.get('set_ids')
    
    if not set_ids or not isinstance(set_ids, list):
        return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ.'}), 400

    try:
        updated_count = 0
        for set_id in set_ids:
            user_container_state = UserContainerState.query.filter_by(
                user_id=current_user.user_id,
                container_id=set_id
            ).first()
            if user_container_state and user_container_state.is_archived:
                user_container_state.is_archived = False
                updated_count += 1
        
        safe_commit(db.session)
        
        if updated_count > 0:
            flash(f'Đã bỏ lưu trữ thành công {updated_count} bộ thẻ.', 'success')
            return jsonify({'success': True, 'message': f'Đã bỏ lưu trữ thành công {updated_count} bộ thẻ.'})
        else:
            return jsonify({'success': False, 'message': 'Không có bộ thẻ nào được bỏ lưu trữ.'}), 400
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi bỏ lưu trữ hàng loạt: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi xử lý yêu cầu.'}), 500


@flashcard_learning_bp.route('/generate-image-from-content', methods=['POST'])
@login_required
def generate_image_from_content():
    """Tự động tìm và lưu ảnh minh họa dựa trên nội dung của thẻ."""
    data = request.get_json(silent=True) or {}
    item_id = data.get('item_id')
    side = (data.get('side') or 'front').lower()

    if not item_id:
        return jsonify({'success': False, 'message': 'Thiếu thông tin mã thẻ.'}), 400

    if side not in {'front', 'back'}:
        return jsonify({'success': False, 'message': 'Mặt thẻ không hợp lệ.'}), 400

    item = LearningItem.query.get(item_id)
    if not item or item.item_type != 'FLASHCARD':
        return jsonify({'success': False, 'message': 'Không tìm thấy thẻ phù hợp.'}), 404

    if not _user_can_edit_flashcard(item.container_id):
        return jsonify({'success': False, 'message': 'Bạn không có quyền chỉnh sửa thẻ này.'}), 403

    content = item.content or {}
    text_source = content.get('front' if side == 'front' else 'back') or ''
    if not str(text_source).strip():
        return jsonify({'success': False, 'message': 'Không có nội dung để tìm ảnh minh họa.'}), 400

    try:
        absolute_path, success, message = image_service.get_cached_or_download_image(str(text_source))
        if success and absolute_path:
            container = item.container if item else None
            if not container:
                return jsonify({'success': False, 'message': 'Không xác định được bộ thẻ.'}), 400

            image_folder = getattr(container, 'media_image_folder', None)
            if not image_folder:
                image_folder = _ensure_container_media_folder(container, 'image')

            try:
                os.makedirs(os.path.join(current_app.static_folder, image_folder), exist_ok=True)
            except OSError as folder_exc:
                current_app.logger.error(
                    "Không thể tạo thư mục ảnh %s: %s", image_folder, folder_exc, exc_info=True
                )
                return jsonify({'success': False, 'message': 'Không thể chuẩn bị thư mục lưu ảnh.'}), 500

            filename = os.path.basename(absolute_path)
            destination = os.path.join(current_app.static_folder, image_folder, filename)

            try:
                if os.path.abspath(absolute_path) != os.path.abspath(destination):
                    if os.path.exists(destination):
                        os.remove(destination)
                    shutil.move(absolute_path, destination)
            except Exception as move_exc:  # pylint: disable=broad-except
                current_app.logger.error(
                    "Lỗi khi di chuyển ảnh vào thư mục %s: %s", image_folder, move_exc, exc_info=True
                )
                return jsonify({'success': False, 'message': 'Không thể lưu file ảnh.'}), 500

            stored_value = normalize_media_value_for_storage(filename, image_folder)
            relative_path = build_relative_media_path(stored_value, image_folder)

            if side == 'front':
                content['front_img'] = stored_value
            else:
                content['back_img'] = stored_value

            item.content = content
            flag_modified(item, 'content')
            safe_commit(db.session)

            return jsonify({
                'success': True,
                'message': 'Đã cập nhật ảnh minh họa thành công.',
                'image_url': url_for('static', filename=relative_path)
            })

        return jsonify({'success': False, 'message': message or 'Không tìm thấy ảnh phù hợp.'}), 500
    except Exception as exc:  # pylint: disable=broad-except
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi tạo ảnh minh họa cho thẻ {item_id}: {exc}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi xử lý yêu cầu.'}), 500

@flashcard_learning_bp.route('/regenerate-audio-from-content', methods=['POST'])
@login_required
def regenerate_audio_from_content():
    """
    Kích hoạt việc tạo file audio từ nội dung văn bản và lưu đường dẫn vào database.
    """
    data = request.get_json()
    item_id = data.get('item_id')
    side = data.get('side')
    content_to_read = data.get('content_to_read')

    if not item_id or not side or not content_to_read:
        return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ.'}), 400

    item = LearningItem.query.get(item_id)
    if not item or item.item_type != 'FLASHCARD':
        return jsonify({'success': False, 'message': 'Không tìm thấy thẻ hoặc loại thẻ không đúng.'}), 404

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Use the NEW optimized method that handles folders and ID-based naming
        # Now returns both the DB-ready value and the full relative path for URL generation
        stored_value, full_relative_path, success, msg = loop.run_until_complete(
            audio_service.get_or_generate_audio_for_item(item, side, force_refresh=True)
        )
        
        if success and stored_value:
            # ✅ Save audio URL/filename to database
            try:
                current_app.logger.info(f"[AUDIO REGEN] Item {item_id} - Saving {side} audio value: {stored_value}")
                
                if side == 'front':
                    item.content['front_audio_url'] = stored_value
                elif side == 'back':
                    item.content['back_audio_url'] = stored_value
                
                flag_modified(item, 'content')
                safe_commit(db.session)
            except Exception as db_exc:
                current_app.logger.warning(f"Failed to save audio to database: {db_exc}")
            
            # Generate final URL for frontend playback using the full relative path
            final_audio_url = url_for('static', filename=full_relative_path)
            
            return jsonify({
                'success': True,
                'message': 'Đã tạo audio thành công.',
                'audio_url': final_audio_url,
            })
        else:
            return jsonify({'success': False, 'message': msg or 'Không thể tạo audio.'}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi tạo audio từ nội dung: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi xử lý yêu cầu.'}), 500
    finally:
        loop.close()

