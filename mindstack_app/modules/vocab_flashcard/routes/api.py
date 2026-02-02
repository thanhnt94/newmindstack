# File: mindstack_app/modules/vocab_flashcard/routes/api.py
from flask import request, jsonify, current_app, session, abort, url_for
from flask_login import login_required, current_user
import asyncio
import os
import shutil
import traceback
import datetime
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.sql import func
from sqlalchemy.exc import OperationalError

from .. import blueprint
from ..engine.algorithms import (
    get_filtered_flashcard_sets, 
    get_flashcard_mode_counts,
    get_accessible_flashcard_set_ids
)
from ..engine.session_manager import FlashcardSessionManager
from ..engine.core import FlashcardEngine
from ..engine.config import FlashcardLearningConfig
from ..services import AudioService, ImageService, LearningSessionService
from mindstack_app.utils.db_session import safe_commit
from mindstack_app.utils.media_paths import (
    normalize_media_value_for_storage,
    build_relative_media_path,
)
from mindstack_app.models import (
    db, 
    LearningItem, 
    LearningContainer, 
    UserContainerState,
)
from mindstack_app.modules.fsrs.models import ItemMemoryState
from mindstack_app.modules.fsrs.schemas import CardStateDTO as CardState
from mindstack_app.modules.fsrs.logics.fsrs_engine import FSRSEngine
from mindstack_app.modules.fsrs.services.optimizer_service import FSRSOptimizerService
from mindstack_app.modules.vocabulary.services.stats_container import VocabularyStatsService

# Helper from views (could be moved to a shared logic file later)
def _user_can_edit_flashcard(container_id: int) -> bool:
    """Return True if the current user can edit items within the container."""
    from mindstack_app.models import User, ContainerContributor
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
    except Exception:
        db.session.rollback()
        raise
    return default_folder

@blueprint.route('/api/sets')
@login_required
def api_get_sets():
    """API lấy danh sách bộ thẻ cho practice."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)

    try:
        pagination = get_filtered_flashcard_sets(
            user_id=current_user.user_id,
            search_query=search,
            search_field=search_field,
            current_filter=current_filter,
            page=page,
            per_page=12
        )

        sets = []
        for item in pagination.items:
            sets.append({
                'id': item.container_id,
                'title': item.title,
                'description': item.description or '',
                'cover_image': item.cover_image,
                'total_items': getattr(item, 'total_items', 0),
                'completion_percentage': getattr(item, 'completion_percentage', 0),
                'item_count_display': getattr(item, 'item_count_display', '0 / 0'),
            })

        return jsonify({
            'success': True,
            'sets': sets,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
            'page': page,
            'total': pagination.total,
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/api/modes/<set_identifier>')
@login_required
def api_get_modes(set_identifier):
    """API lấy các chế độ học với số lượng thẻ."""
    try:
        if set_identifier == 'all':
            modes = get_flashcard_mode_counts(current_user.user_id, 'all')
        else:
            set_ids = [int(s) for s in set_identifier.split(',') if s]
            if len(set_ids) == 1:
                modes = get_flashcard_mode_counts(current_user.user_id, set_ids[0])
            else:
                modes = get_flashcard_mode_counts(current_user.user_id, set_ids)
        
        return jsonify({'success': True, 'modes': modes['list']})
    except ValueError:
        return jsonify({'success': False, 'message': 'ID bộ thẻ không hợp lệ.'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/api/items/<int:item_id>', methods=['GET'])
@login_required
def api_get_flashcard_item_details(item_id):
    """Trả về thông tin chi tiết của một thẻ trong phiên học hiện tại."""
    if 'flashcard_session' not in session:
        return jsonify({'success': False, 'message': 'Không có phiên học nào đang hoạt động.'}), 400

    try:
        item = LearningItem.query.filter(
            LearningItem.item_id == item_id,
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        ).first()
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
                return url_for('media_uploads', filename=relative_path.lstrip('/'), _external=True)
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

@blueprint.route('/get_flashcard_batch', methods=['GET'])
@login_required
def api_get_flashcard_batch():
    """Trả về dữ liệu nhóm thẻ tiếp theo trong phiên học hiện tại."""
    if 'flashcard_session' not in session:
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 404

    session_manager = FlashcardSessionManager.from_dict(session['flashcard_session'])
    batch_size = request.args.get('batch_size', default=10, type=int)
    
    try:
        flashcard_batch = session_manager.get_next_batch(batch_size=batch_size)
        session['flashcard_session'] = session_manager.to_dict()
        session.modified = True

        if flashcard_batch is None:
            session_manager.end_flashcard_session()
            return jsonify({'message': 'Bạn đã hoàn thành tất cả các thẻ trong phiên học này!'}), 404
        
        flashcard_batch['session_correct_answers'] = session_manager.correct_answers
        flashcard_batch['session_incorrect_answers'] = session_manager.incorrect_answers
        flashcard_batch['session_vague_answers'] = session_manager.vague_answers
        flashcard_batch['session_total_answered'] = session_manager.correct_answers + session_manager.incorrect_answers + session_manager.vague_answers
        flashcard_batch['session_points'] = session_manager.session_points
        flashcard_batch['session_total_items'] = session_manager.total_items_in_session
        answered_count = session_manager.correct_answers + session_manager.incorrect_answers + session_manager.vague_answers
        flashcard_batch['session_processed_count'] = answered_count + 1
        
        container_name = 'Bộ thẻ'
        set_id = session_manager.set_id
        if set_id == 'all':
            container_name = 'Tất cả bộ thẻ'
        elif isinstance(set_id, (int, str)):
            try:
                numeric_id = int(set_id)
                container = LearningContainer.query.get(numeric_id)
                if container:
                    container_name = container.title or ''
            except (ValueError, TypeError):
                pass
        
        flashcard_batch['container_name'] = container_name
        return jsonify(flashcard_batch)
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        current_app.logger.error(f"LỖI khi lấy nhóm thẻ: {error_msg}")
        return jsonify({'message': f'Lỗi khi tải thẻ: {str(e)}', 'traceback': error_msg}), 500

@blueprint.route('/submit_flashcard_answer', methods=['POST'])
@login_required
def api_submit_flashcard_answer():
    """Nhận câu trả lời của người dùng, xử lý và cập nhật tiến độ."""
    data = request.get_json()
    item_id = data.get('item_id')
    user_answer = data.get('user_answer')

    if not item_id or not user_answer:
        return jsonify({'error': 'Dữ liệu đáp án không hợp lệ.'}), 400

    if 'flashcard_session' not in session:
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 400

    session_manager = FlashcardSessionManager.from_dict(session['flashcard_session'])
    
    # Update last accessed
    set_ids = session_manager.set_id
    if not isinstance(set_ids, list):
        set_ids = [set_ids] if set_ids != 'all' else []
    
    for s_id in set_ids:
        if isinstance(s_id, int):
            ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=s_id).first()
            if not ucs:
                ucs = UserContainerState(user_id=current_user.user_id, container_id=s_id)
                db.session.add(ucs)
            ucs.last_accessed = func.now()
    safe_commit(db.session)

    user_button_count = 4
    if 'flashcard_button_count_override' in session:
        user_button_count = session.get('flashcard_button_count_override')
    elif current_user.get_flashcard_button_count():
        user_button_count = current_user.get_flashcard_button_count()

    normalized_answer = str(user_answer).lower()
    quality_map = {}
    if user_button_count == 3:
        quality_map = {'quên': 1, 'mơ_hồ': 2, 'nhớ': 3}
    elif user_button_count == 4:
        quality_map = {'again': 1, 'hard': 2, 'good': 3, 'easy': 4}
    
    user_answer_quality = quality_map.get(normalized_answer, 3)
    duration_ms = data.get('duration_ms', 0)
    
    result = session_manager.process_flashcard_answer(item_id, user_answer_quality, duration_ms=duration_ms, user_answer_text=user_answer)
    session['flashcard_session'] = session_manager.to_dict()

    return jsonify({
        'success': True,
        'score_change': result.get('score_change'),
        'updated_total_score': result.get('updated_total_score'),
        'is_correct': result.get('is_correct'),
        'new_progress_status': result.get('new_progress_status'),
        'statistics': result.get('statistics'),
        'srs_data': result.get('srs_data'),
        'session_correct_answers': session_manager.correct_answers,
        'session_incorrect_answers': session_manager.incorrect_answers,
        'session_vague_answers': session_manager.vague_answers,
        'session_total_answered': session_manager.correct_answers + session_manager.incorrect_answers + session_manager.vague_answers,
        'session_points': result.get('session_points', session_manager.session_points)
    })

@blueprint.route('/end_session_flashcard', methods=['POST'])
@login_required
def api_end_session_flashcard():
    """Kết thúc phiên học Flashcard hiện tại."""
    db_session_id = None
    if 'flashcard_session' in session:
        db_session_id = session['flashcard_session'].get('db_session_id')
    result = FlashcardSessionManager.end_flashcard_session()
    if db_session_id:
        result['session_id'] = db_session_id
    return jsonify(result)

@blueprint.route('/save_flashcard_settings', methods=['POST'])
@login_required
def api_save_flashcard_settings():
    """Lưu cài đặt cho bộ thẻ hiện tại."""
    data = request.get_json()
    button_count = data.get('button_count')
    visual_settings = data.get('visual_settings')
    
    from mindstack_app.modules.learning.services.settings_service import LearningSettingsService
    
    session_data = session.get('flashcard_session', {})
    set_ids = session_data.get('set_id')
    target_set_ids = [set_ids] if isinstance(set_ids, int) else (set_ids if isinstance(set_ids, list) else [])
    
    update_payload = {'flashcard': {}}
    if button_count: 
        update_payload['flashcard']['button_count'] = button_count
        session['flashcard_button_count_override'] = button_count
    if visual_settings:
        update_payload['flashcard'].update(visual_settings)
        session['flashcard_visual_settings'] = visual_settings

    for sid in target_set_ids:
        if isinstance(sid, int):
            LearningSettingsService.update_container_settings(current_user.user_id, sid, update_payload)
                
    return jsonify({'success': True, 'message': 'Cài đặt đã được lưu.'})

@blueprint.route('/toggle_archive_flashcard/<int:set_id>', methods=['POST'])
@login_required
def toggle_archive_flashcard(set_id):
    """Xử lý yêu cầu archive hoặc unarchive một bộ thẻ."""
    ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=set_id).first()
    if ucs:
        ucs.is_archived = not ucs.is_archived
    else:
        ucs = UserContainerState(user_id=current_user.user_id, container_id=set_id, is_archived=True)
        db.session.add(ucs)
    safe_commit(db.session)
    return jsonify({'success': True, 'is_archived': ucs.is_archived})

@blueprint.route('/generate-image-from-content', methods=['POST'])
@login_required
def generate_image_from_content():
    """Tự động tìm và lưu ảnh minh họa."""
    data = request.get_json(silent=True) or {}
    item_id = data.get('item_id')
    side = (data.get('side') or 'front').lower()

    item = LearningItem.query.get(item_id)
    if not item or not _user_can_edit_flashcard(item.container_id):
        return jsonify({'success': False, 'message': 'Không có quyền.'}), 403

    text_source = item.content.get(side)
    image_service = ImageService()
    absolute_path, success, message = image_service.get_cached_or_download_image(str(text_source))
    
    if success:
        container = item.container
        image_folder = _ensure_container_media_folder(container, 'image')
        filename = os.path.basename(absolute_path)
        destination = os.path.join(current_app.config['UPLOAD_FOLDER'], image_folder, filename)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.move(absolute_path, destination)
        
        stored_value = normalize_media_value_for_storage(filename, image_folder)
        item.content[f'{side}_img'] = stored_value
        flag_modified(item, 'content')
        safe_commit(db.session)
        return jsonify({'success': True, 'image_url': url_for('media_uploads', filename=build_relative_media_path(stored_value, image_folder))})
    
    return jsonify({'success': False, 'message': message}), 500

@blueprint.route('/regenerate-audio-from-content', methods=['POST'])
@login_required
def api_regenerate_audio_from_content():
    """Tạo file audio từ văn bản."""
    data = request.get_json()
    item_id, side = data.get('item_id'), data.get('side')
    item = LearningItem.query.get(item_id)
    
    audio_service = AudioService()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        stored_value, rel_path, success, msg = loop.run_until_complete(audio_service.get_or_generate_audio_for_item(item, side, force_refresh=True))
        if success:
            item.content[f'{side}_audio_url'] = stored_value
            flag_modified(item, 'content')
            safe_commit(db.session)
            return jsonify({'success': True, 'audio_url': url_for('media_uploads', filename=rel_path)})
        return jsonify({'success': False, 'message': msg}), 500
    finally:
        loop.close()

@blueprint.route('/api/preview_fsrs', methods=['POST'])
@login_required
def preview_fsrs():
    """Calculate FSRS preview data."""
    data = request.get_json()
    if not data or 'item_id' not in data:
        return jsonify({'success': False, 'message': 'Missing item_id'}), 400
        
    try:
        item_id = int(data.get('item_id'))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid item_id'}), 400

    # MIGRATED: Use ItemMemoryState
    progress = ItemMemoryState.query.filter_by(user_id=current_user.user_id, item_id=item_id).first()
    
    # Calculate interval from due date if available, or 0.0
    current_ivl = 0.0
    if progress and progress.due_date and progress.last_review:
         delta = (progress.due_date.replace(tzinfo=timezone.utc) - progress.last_review.replace(tzinfo=timezone.utc))
         current_ivl = max(0.0, delta.total_seconds() / 86400.0)

    card_state = CardState(
        stability=progress.stability if progress else 0.0,
        difficulty=progress.difficulty if progress else 0.0,
        reps=progress.repetitions if progress else 0,
        lapses=progress.lapses if progress else 0,
        state=progress.state if progress else 0,
        last_review=progress.last_review if progress else None,
        scheduled_days=current_ivl
    )

    weights = FSRSOptimizerService.get_user_parameters(current_user.user_id)
    engine = FSRSEngine(desired_retention=0.9, custom_weights=weights)
    now = datetime.datetime.now(datetime.timezone.utc)
    
    previews = {}
    for rating in [1, 2, 3, 4]:
        try:
            new_card, _, _ = engine.review_card(card_state, rating, now, enable_fuzz=False)
            previews[str(rating)] = {
                'interval': f"{round(new_card.scheduled_days, 1)}d",
                'stability': round(new_card.stability, 2),
                'difficulty': round(new_card.difficulty, 2),
                'retrievability': 100 
            }
        except Exception as e:
            current_app.logger.error(f"FSRS Preview Error for rating {rating}: {str(e)}")
            previews[str(rating)] = {
                'interval': 'N/A',
                'stability': 0,
                'difficulty': 0,
                'retrievability': 0
            }
            
    return jsonify({'success': True, 'previews': previews})


# --- LEGACY COLLAB API (Removed as per user request to focus on individual learning) ---
# All collaborative routes have been purged.