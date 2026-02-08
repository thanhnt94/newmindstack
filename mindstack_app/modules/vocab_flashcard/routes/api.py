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

from ..engine.core import FlashcardEngine
from ..engine.config import FlashcardLearningConfig
from ..services import CardPresenter
# External module interfaces
from mindstack_app.modules.audio.interface import AudioInterface
from mindstack_app.modules.media.interface import MediaInterface
from mindstack_app.modules.session.interface import SessionInterface
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
# REFAC: Removed ItemMemoryState import
from mindstack_app.modules.fsrs.interface import FSRSInterface
from mindstack_app.modules.vocabulary.interface import VocabularyInterface

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
        context = request.args.get('context', 'vocab')
        if set_identifier == 'all':
            modes = get_flashcard_mode_counts(current_user.user_id, 'all', context=context)
        else:
            set_ids = [int(s) for s in set_identifier.split(',') if s]
            if len(set_ids) == 1:
                modes = get_flashcard_mode_counts(current_user.user_id, set_ids[0], context=context)
            else:
                modes = get_flashcard_mode_counts(current_user.user_id, set_ids, context=context)
        
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

    session_data = session['flashcard_session']
    db_id = session_data.get('db_session_id')
    
    # 1. Fetch DB Session for latest state
    db_sess = SessionInterface.get_session_by_id(db_id)
    if not db_sess or db_sess.status != 'active':
        return jsonify({'message': 'Phiên học đã kết thúc.'}), 404

    batch_size = request.args.get('batch_size', default=1, type=int)

    # [NEW] Handle client-side exclusions (for prefetching)
    exclude_items_str = request.args.get('exclude_items', '')
    client_excluded_ids = []
    if exclude_items_str:
        try:
            client_excluded_ids = [int(s) for s in exclude_items_str.split(',') if s]
        except ValueError:
            pass

    # Merge with DB processed IDs
    processed_ids = list(set((db_sess.processed_item_ids or []) + client_excluded_ids))
    
    try:
        # 2. Get Next Batch using Stateless Engine
        items_data = FlashcardEngine.get_next_batch(
            user_id=current_user.user_id,
            set_id=session_data.get('set_id'),
            mode=session_data.get('mode'),
            processed_ids=processed_ids,
            db_session_id=db_id,
            batch_size=batch_size,
            current_db_item_id=db_sess.current_item_id
        )

        # [AUTO-RESCUE] If no items found with exclusion, check if user is 'stuck'
        if items_data is None:
            # Check if items exist WITHOUT exclusion list
            from ..services.query_builder import FlashcardQueryBuilder
            rescue_qb = FlashcardQueryBuilder(current_user.user_id)
            
            # Re-apply filters similar to Engine
            s_id_raw = session_data.get('set_id')
            if s_id_raw == 'all':
                accessible_ids = get_accessible_flashcard_set_ids(current_user.user_id)
                rescue_qb.filter_by_containers(accessible_ids)
            else:
                s_ids = s_id_raw if isinstance(s_id_raw, list) else [int(s_id_raw)]
                rescue_qb.filter_by_containers(s_ids)

            from ..engine.vocab_flashcard_mode import get_flashcard_mode_by_id
            mode_obj = get_flashcard_mode_by_id(session_data.get('mode'))
            if mode_obj and hasattr(rescue_qb, mode_obj.filter_method):
                getattr(rescue_qb, mode_obj.filter_method)()
            else:
                rescue_qb.filter_mixed()

            # If items exist without processed_ids, then we are indeed stuck.
            if rescue_qb.count() > 0:
                current_app.logger.info(f"Auto-Rescue: Resetting session {db_id} for user {current_user.user_id} (Stuck by processed_ids)")
                SessionInterface.reset_session_progress(db_id)
                
                # Retry fetch
                items_data = FlashcardEngine.get_next_batch(
                    user_id=current_user.user_id,
                    set_id=session_data.get('set_id'),
                    mode=session_data.get('mode'),
                    processed_ids=[], # Cleared
                    db_session_id=db_id,
                    batch_size=batch_size,
                    current_db_item_id=None
                )

        if items_data is None:
            # Truly end of session
            SessionInterface.complete_session(db_id)
            return jsonify({'message': 'Bạn đã hoàn thành tất cả các thẻ trong phiên học này!'}), 404
        
        # 3. Update active item helper (Engine does this if current_db_item_id passed? No, Engine is stateless. 
        # But wait, FlashcardSessionManager did: SessionInterface.set_current_item(..., item.item_id). 
        # I need to do that here to preserve "resume" capability for the *first* item in batch.
        if items_data:
             # The first item in the batch is technically the "current" one being looked at first
             # This assumes sequential viewing.
             first_item_id = items_data[0]['item_id']
             SessionInterface.set_current_item(db_id, first_item_id)

        # 4. Construct Response
        # Recalculate stats from DB session to ensure sync
        processed_count = len(db_sess.processed_item_ids or [])
        total_items = db_sess.total_items
        
        response = {
            'items': items_data,
            'total_items_in_session': total_items,
            'session_processed_count': processed_count,
            # Stats for HUD
            'session_correct_answers': db_sess.correct_count,
            'session_incorrect_answers': db_sess.incorrect_count,
            'session_vague_answers': db_sess.vague_count,
            'session_total_answered': db_sess.correct_count + db_sess.incorrect_count + db_sess.vague_count,
            'session_points': db_sess.points_earned,
            'session_total_items': total_items,
            'container_name': session_data.get('container_name', 'Học tập') # Or fetch fresh
        }
        
        return jsonify(response)
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

    session_data = session['flashcard_session']
    db_id = session_data.get('db_session_id')
    
    # 1. Access Update (Misc)
    set_ids = session_data.get('set_id')
    if set_ids:
        s_list = set_ids if isinstance(set_ids, list) else ([set_ids] if set_ids != 'all' else [])
        for s_id in s_list:
            if isinstance(s_id, int):
                ucs = UserContainerState.query.filter_by(user_id=current_user.user_id, container_id=s_id).first()
                if not ucs:
                    ucs = UserContainerState(user_id=current_user.user_id, container_id=s_id)
                    db.session.add(ucs)
                ucs.last_accessed = func.now()
        safe_commit(db.session)

    # 2. Determine Quality
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
    
    # 3. Call Stateless Engine
    score_change, new_total, result_type, new_status, item_stats, srs_data = FlashcardEngine.process_answer(
        user_id=current_user.user_id,
        item_id=item_id,
        quality=user_answer_quality,
        current_user_total_score=current_user.total_score,
        mode=session_data.get('mode'),
        update_srs=True,
        duration_ms=duration_ms,
        user_answer_text=user_answer,
        session_id=db_id,
        container_id=None,
        learning_mode='flashcard'
    )

    # 4. Update DB Session
    SessionInterface.update_progress(db_id, item_id, result_type, score_change)
    
    # 5. Fetch updated session stats for response
    # (Since SessionInterface commits, we can query or just increment local vars if we trust logic)
    # Let's query db_sess again for accuracy or maintain local if perf critical. Query is safer for stateless.
    db_sess = SessionInterface.get_session_by_id(db_id)
    
    # 6. Update Cookie Stats (Optional but good for fallback reading)
    session_data['session_points'] = db_sess.points_earned
    session_data['correct_answers'] = db_sess.correct_count
    session_data['incorrect_answers'] = db_sess.incorrect_count
    session_data['vague_answers'] = db_sess.vague_count
    session.modified = True

    return jsonify({
        'success': True,
        'score_change': score_change,
        'updated_total_score': new_total,
        'is_correct': result_type == 'correct',
        'new_progress_status': new_status,
        'statistics': item_stats,
        'srs_data': srs_data,
        'session_correct_answers': db_sess.correct_count,
        'session_incorrect_answers': db_sess.incorrect_count,
        'session_vague_answers': db_sess.vague_count,
        'session_total_answered': db_sess.correct_count + db_sess.incorrect_count + db_sess.vague_count,
        'session_points': score_change # Providing 'delta' here, generic 'session_points' is total
    })

@blueprint.route('/end_session_flashcard', methods=['POST'])
@login_required
def api_end_session_flashcard():
    """Kết thúc phiên học Flashcard hiện tại."""
    result = {'message': 'Phiên học kết thúc', 'stats': {}}
    
    if 'flashcard_session' in session:
        session_data = session['flashcard_session']
        db_id = session_data.get('db_session_id')
        
        if db_id:
            SessionInterface.complete_session(db_id)
            # Fetch final stats
            db_sess = SessionInterface.get_session_by_id(db_id)
            if db_sess:
                result['stats'] = {
                    'correct': db_sess.correct_count,
                    'incorrect': db_sess.incorrect_count,
                    'vague': db_sess.vague_count,
                    'points': db_sess.points_earned
                }
                result['session_id'] = db_id
        
        session.pop('flashcard_session', None)
        
    return jsonify(result)

@blueprint.route('/save_flashcard_settings', methods=['POST'])
@login_required
def api_save_flashcard_settings():
    """Lưu cài đặt cho bộ thẻ hiện tại."""
    data = request.get_json()
    button_count = data.get('button_count')
    visual_settings = data.get('visual_settings')
    
    from mindstack_app.modules.learning.interface import LearningInterface
    
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
            # REFAC: Use Interface
            settings = LearningInterface.update_container_settings(current_user.user_id, sid, update_payload)
                
    return jsonify({'success': True, 'settings': settings})

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
    """
    Generate image from content text.
    
    [REFACTORED] Now delegates image search to media.interface.
    """
    data = request.get_json(silent=True) or {}
    item_id = data.get('item_id')
    side = (data.get('side') or 'front').lower()

    item = LearningItem.query.get(item_id)
    if not item or not _user_can_edit_flashcard(item.container_id):
        return jsonify({'success': False, 'message': 'Không có quyền.'}), 403

    text_source = item.content.get(side)
    if not text_source:
        return jsonify({'success': False, 'message': 'Không có nội dung để tìm ảnh.'}), 400
    
    # Use MediaInterface for image search
    result = MediaInterface.search_and_cache_image(str(text_source))
    
    if result.status == 'success' and result.file_path:
        container = item.container
        image_folder = _ensure_container_media_folder(container, 'image')
        filename = os.path.basename(result.file_path)
        destination = os.path.join(current_app.config['UPLOAD_FOLDER'], image_folder, filename)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.move(result.file_path, destination)
        
        stored_value = normalize_media_value_for_storage(filename, image_folder)
        item.content[f'{side}_img'] = stored_value
        flag_modified(item, 'content')
        safe_commit(db.session)
        return jsonify({'success': True, 'image_url': url_for('media_uploads', filename=build_relative_media_path(stored_value, image_folder))})
    
    return jsonify({'success': False, 'message': result.error or 'Không tìm thấy ảnh phù hợp.'}), 500

@blueprint.route('/regenerate-audio-from-content', methods=['POST'])
@login_required
def api_regenerate_audio_from_content():
    """
    Regenerate audio from text content.
    
    [REFACTORED] Now delegates TTS generation to audio.interface.
    Path management and DB updates remain here (presentation layer responsibility).
    """
    data = request.get_json()
    item_id, side = data.get('item_id'), data.get('side')
    item = LearningItem.query.get(item_id)
    
    if not item or not _user_can_edit_flashcard(item.container_id):
        return jsonify({'success': False, 'message': 'Không có quyền.'}), 403
    
    # 1. Get content to generate audio for
    if side == 'front':
        content_to_read = item.content.get('front_audio_content') or item.content.get('front')
    else:
        content_to_read = item.content.get('back_audio_content') or item.content.get('back')
    
    if not content_to_read or not str(content_to_read).strip():
        return jsonify({'success': False, 'message': 'Không có nội dung để tạo audio.'}), 400
    
    # 2. Determine target directory (must be 'uploads/{folder}' format for get_storage_path)
    container = item.container
    audio_folder = _ensure_container_media_folder(container, 'audio')
    # Prepend 'uploads/' to make it compatible with audio module's get_storage_path
    target_dir = f"uploads/{audio_folder}"
    filename = f"{side}_{item.item_id}.mp3"
    
    # 3. Generate audio via external AudioInterface
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            AudioInterface.generate_audio(
                text=str(content_to_read),
                engine='edge',
                target_dir=target_dir,
                custom_filename=filename,
                is_manual=True,  # Force regeneration even if file exists
                auto_voice_parsing=True
            )
        )
        
        # Status is 'exists', 'generated', or 'error'
        if result.status in ('generated', 'exists') and result.url:
            # 4. Update DB with storage value
            stored_value = normalize_media_value_for_storage(filename, audio_folder)
            item.content[f'{side}_audio_url'] = stored_value
            flag_modified(item, 'content')
            safe_commit(db.session)
            
            rel_path = build_relative_media_path(stored_value, audio_folder)
            return jsonify({
                'success': True, 
                'audio_url': url_for('media_uploads', filename=rel_path)
            })
        
        return jsonify({
            'success': False, 
            'message': result.error or 'Lỗi tạo audio.'
        }), 500
    except Exception as e:
        current_app.logger.error(f'Audio regeneration error: {e}', exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        loop.close()


@blueprint.route('/api/preview_fsrs', methods=['POST'])
@login_required
def preview_fsrs():
    """
    Calculate FSRS preview data.
    
    [REFACTORED] Now delegates to FSRSInterface.get_preview_intervals()
    which handles all state building, engine creation, and error handling.
    """
    data = request.get_json()
    if not data or 'item_id' not in data:
        return jsonify({'success': False, 'message': 'Missing item_id'}), 400
        
    try:
        item_id = int(data.get('item_id'))
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid item_id'}), 400

    # Use FSRSInterface - all logic is now encapsulated
    previews = FSRSInterface.get_preview_intervals(current_user.user_id, item_id)
            
    return jsonify({'success': True, 'previews': previews})


# --- LEGACY COLLAB API (Removed as per user request to focus on individual learning) ---
# All collaborative routes have been purged.