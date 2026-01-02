# File: quiz/individual/routes/api.py
# MỤC ĐÍCH: API endpoints - JSON responses
# Refactored from routes.py

import os
import copy
from typing import Optional

from flask import request, jsonify, abort, current_app, session, url_for
from flask_login import login_required, current_user
from sqlalchemy.sql import func
from sqlalchemy.orm.attributes import flag_modified

from . import quiz_learning_bp
from ..logics.session_logic import QuizSessionManager
from ..logics.algorithms import get_accessible_quiz_set_ids
from ..services.audio_service import QuizAudioService
from mindstack_app.models import (
    LearningContainer,
    LearningItem,
    User,
    UserContainerState,
    UserNote,
    ContainerContributor,
    db,
)
from mindstack_app.utils.media_paths import build_relative_media_path


def _get_media_folders_from_container(container) -> dict[str, str]:
    if not container:
        return {}
    folders = getattr(container, 'media_folders', {}) or {}
    if folders:
        return dict(folders)
    return {}


def _build_absolute_media_url(file_path, media_folder: Optional[str] = None):
    if not file_path:
        return None
    try:
        relative_path = build_relative_media_path(file_path, media_folder)
        if not relative_path:
            return None
        if relative_path.startswith(('http://', 'https://')):
            return relative_path
        static_path = relative_path.lstrip('/')
        return url_for('static', filename=static_path)
    except Exception as exc:
        current_app.logger.error(f"Không thể tạo URL tuyệt đối cho media '{file_path}': {exc}")
        return file_path


def _serialize_quiz_learning_item(item, user_id):
    content_copy = copy.deepcopy(item.content or {})
    options = content_copy.get('options') or {}

    # Filter out empty options to support dynamic number of answers (e.g. 2, 3, 4)
    valid_options = {}
    for key in ['A', 'B', 'C', 'D']:
        val = options.get(key)
        if val not in (None, ''):
            valid_options[key] = val
    content_copy['options'] = valid_options

    media_folders = _get_media_folders_from_container(item.container if item else None)
    image_folder = media_folders.get('image')
    audio_folder = media_folders.get('audio')

    image_path = content_copy.get('question_image_file')
    if image_path:
        content_copy['question_image_file'] = _build_absolute_media_url(image_path, image_folder)

    audio_path = content_copy.get('question_audio_file')
    if audio_path:
        content_copy['question_audio_file'] = _build_absolute_media_url(audio_path, audio_folder)

    note = UserNote.query.filter_by(user_id=user_id, item_id=item.item_id).first()

    can_edit = False
    if current_user.is_authenticated and current_user.user_role == User.ROLE_ADMIN:
        can_edit = True
    elif item and item.container:
        if item.container.creator_user_id == user_id:
            can_edit = True
        elif user_id:
            contributor = ContainerContributor.query.filter_by(
                container_id=item.container_id,
                user_id=user_id,
                permission_level='editor'
            ).first()
            if contributor:
                can_edit = True

    return {
        'item_id': item.item_id,
        'container_id': item.container_id,
        'content': content_copy,
        'ai_explanation': item.ai_explanation,
        'note_content': note.content if note else '',
        'group_id': item.group_id,
        'group_details': None,
        'can_edit': can_edit,
    }


@quiz_learning_bp.route('/quiz_learning/api/items/<int:item_id>', methods=['GET'])
@login_required
def get_quiz_item_api(item_id):
    item = LearningItem.query.get_or_404(item_id)
    if item.item_type != 'QUIZ_MCQ':
        abort(404)

    accessible_ids = set(get_accessible_quiz_set_ids(current_user.user_id))
    if accessible_ids and item.container_id not in accessible_ids:
        abort(403)

    item_payload = _serialize_quiz_learning_item(item, current_user.user_id)
    return jsonify({'success': True, 'item': item_payload})


@quiz_learning_bp.route('/get_question_batch', methods=['GET'])
@login_required
def get_question_batch():
    """Trả về dữ liệu nhóm câu hỏi tiếp theo trong phiên học hiện tại."""
    current_app.logger.debug("--- Bắt đầu get_question_batch ---")
    if 'quiz_session' not in session:
        current_app.logger.warning("Phiên học không hợp lệ hoặc đã kết thúc khi gọi get_question_batch.")
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 404

    session_manager = QuizSessionManager.from_dict(session['quiz_session'])
    batch_size = session_manager.batch_size
    try:
        question_batch = session_manager.get_next_batch(batch_size)
        session['quiz_session'] = session_manager.to_dict()

        if question_batch is None:
            session_manager.end_quiz_session()
            current_app.logger.info(f"Phiên học Quiz cho người dùng {current_user.user_id} đã kết thúc do hết câu hỏi.")
            current_app.logger.debug("--- Kết thúc get_question_batch (Hết câu hỏi) ---")
            return jsonify({'message': 'Bạn đã hoàn thành tất cả các câu hỏi trong phiên học này!'}), 404

        question_batch['session_correct_answers'] = session_manager.correct_answers
        question_batch['session_total_answered'] = session_manager.correct_answers + session_manager.incorrect_answers

        current_app.logger.debug("--- Kết thúc get_question_batch (Thành công) ---")
        return jsonify(question_batch)

    except Exception as e:
        current_app.logger.error(f"LỖI NGHIÊM TRỌNG khi lấy nhóm câu hỏi: {e}", exc_info=True)
        current_app.logger.debug("--- Kết thúc get_question_batch (LỖI) ---")
        return jsonify({'message': f'Lỗi khi tải câu hỏi: {str(e)}'}), 500


@quiz_learning_bp.route('/api/transcript/<int:item_id>', methods=['POST'])
@login_required
def get_quiz_transcript(item_id):
    """API: Returns transcript for a quiz item."""
    try:
        item = LearningItem.query.get(item_id)
        if not item:
            return jsonify({'success': False, 'message': 'Không tìm thấy câu hỏi.'}), 404

        container = LearningContainer.query.get(item.container_id)
        if not container:
            return jsonify({'success': False, 'message': 'Container not found'}), 404

        can_edit = (container.creator_user_id == current_user.user_id) or (current_user.user_role == User.ROLE_ADMIN)

        content = item.content or {}
        current_app.logger.info(f"TRANSCRIPT DEBUG: Item {item_id} content keys: {list(content.keys())}")

        transcript = content.get('audio_transcript')
        if transcript:
            return jsonify({
                'success': True,
                'transcript': transcript,
                'cached': True,
                'can_edit': can_edit
            })

        if not can_edit:
            return jsonify({
                'success': False,
                'message': 'Chưa có transcript cho câu hỏi này. Vui lòng liên hệ admin/người tạo để tạo transcript.',
                'can_edit': False
            }), 404

        audio_rel_path = content.get('question_audio') or content.get('question_audio_file') or content.get('audio_url')
        current_app.logger.info(f"TRANSCRIPT DEBUG: Found audio path: {audio_rel_path}")

        if not audio_rel_path:
            return jsonify({'success': False, 'message': 'Không tìm thấy thông tin audio (URL) trong dữ liệu câu hỏi.'}), 400

        media_folders = _get_media_folders_from_container(container)
        audio_folder = media_folders.get('audio')
        relative_path = build_relative_media_path(audio_rel_path, audio_folder)

        if not relative_path:
            return jsonify({'success': False, 'message': 'Không thể xác định đường dẫn file audio.'}), 400

        if relative_path.startswith(('http://', 'https://')):
            return jsonify({'success': False, 'message': 'Audio là URL ngoài, không hỗ trợ transcript tự động.'}), 400

        candidates = []
        if current_app.static_folder:
            candidates.append(current_app.static_folder)
        standard_static = os.path.join(current_app.root_path, 'static')
        if standard_static not in candidates:
            candidates.append(standard_static)
        project_uploads = os.path.abspath(os.path.join(current_app.root_path, '..', 'uploads'))
        if project_uploads not in candidates:
            candidates.append(project_uploads)

        current_app.logger.info(f"TRANSCRIPT DEBUG: Candidates for audio root: {candidates}")

        full_path = None
        checked_paths = []

        for base in candidates:
            p = os.path.join(base, relative_path)
            checked_paths.append(p)
            if os.path.exists(p):
                full_path = p
                current_app.logger.info(f"TRANSCRIPT DEBUG: Found audio at '{full_path}'")
                break

        if not full_path:
            msg = f"Không tìm thấy file audio trên server. Đã kiểm tra: {'; '.join(checked_paths)}"
            current_app.logger.error(f"TRANSCRIPT ERROR: {msg}")
            return jsonify({'success': False, 'message': msg}), 400

        lang_code = 'vi-VN'
        container_text = (container.title or '') + ' ' + (container.description or '') + ' ' + (container.tags or '')
        container_text_lower = container_text.lower()

        if any(kw in container_text_lower for kw in ['jlpt', 'japanese', 'tiếng nhật', 'n5', 'n4', 'n3', 'n2', 'n1', 'nihongo']):
            lang_code = 'ja-JP'
        elif any(kw in container_text_lower for kw in ['english', 'tiếng anh', 'toeic', 'ielts']):
            lang_code = 'en-US'

        service = QuizAudioService()
        transcript = service.voice_service.speech_to_text(full_path, lang=lang_code)

        if transcript:
            if lang_code == 'ja-JP':
                import re
                transcript = re.sub(r'(?<!^)(\s*)(\d+番)', r'\n\n\2', transcript)
                transcript = re.sub(r'(\s+)([1-4])(\s+)', r'\n\2 ', transcript)
                transcript = re.sub(r'\n{3,}', '\n\n', transcript)

            new_content = dict(content)
            new_content['audio_transcript'] = transcript
            item.content = new_content
            flag_modified(item, "content")
            db.session.commit()

            return jsonify({
                'success': True,
                'transcript': transcript,
                'cached': False,
                'can_edit': can_edit
            })
        else:
            return jsonify({'success': False, 'message': 'Không thể nhận diện văn bản (kết quả rỗng).'}), 500

    except Exception as e:
        current_app.logger.error(f"Error generating transcript for item {item_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500


@quiz_learning_bp.route('/api/transcript/<int:item_id>/update', methods=['POST'])
@login_required
def update_quiz_transcript(item_id):
    """API: Manually update the transcript text."""
    try:
        data = request.get_json()
        new_text = data.get('transcript')

        item = LearningItem.query.get(item_id)
        if not item:
            return jsonify({'success': False, 'message': 'Không tìm thấy câu hỏi.'}), 404

        container = LearningContainer.query.get(item.container_id)
        if not container:
            return jsonify({'success': False, 'message': 'Container not found'}), 404

        can_edit = (container.creator_user_id == current_user.user_id) or (current_user.user_role == User.ROLE_ADMIN)
        if not can_edit:
            return jsonify({'success': False, 'message': 'Bạn không có quyền sửa transcript.'}), 403

        content = item.content or {}
        new_content = dict(content)
        new_content['audio_transcript'] = new_text

        item.content = new_content
        flag_modified(item, "content")
        db.session.commit()

        return jsonify({'success': True, 'message': 'Cập nhật thành công.'})

    except Exception as e:
        current_app.logger.error(f"Error updating transcript for item {item_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500


@quiz_learning_bp.route('/api/items/batch', methods=['POST'])
@login_required
def submit_answer_batch():
    """Nhận một danh sách các câu trả lời của người dùng, xử lý và cập nhật tiến độ."""
    current_app.logger.debug("--- Bắt đầu submit_answer_batch ---")
    data = request.get_json()
    answers = data.get('answers')

    if not answers or not isinstance(answers, list):
        current_app.logger.warning("Dữ liệu đáp án không hợp lệ khi submit_answer_batch.")
        return jsonify({'error': 'Dữ liệu đáp án không hợp lệ.'}), 400

    if 'quiz_session' not in session:
        current_app.logger.warning("Không tìm thấy phiên học trong session khi submit_answer_batch.")
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 400

    session_manager = QuizSessionManager.from_dict(session['quiz_session'])
    if not session_manager:
        current_app.logger.warning("Không tìm thấy SessionManager khi submit_answer_batch.")
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 400

    quiz_set_ids = session_manager.set_id
    if not isinstance(quiz_set_ids, list):
        if quiz_set_ids == 'all':
            pass
        else:
            quiz_set_ids = [quiz_set_ids]

    if quiz_set_ids and quiz_set_ids != ['all']:
        for s_id in quiz_set_ids:
            try:
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
                db.session.commit()
                print(f">>> ROUTES: Đã cập nhật last_accessed cho bộ quiz {s_id} <<<")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Lỗi khi cập nhật last_accessed cho bộ quiz {s_id}: {e}", exc_info=True)

    results = session_manager.process_answer_batch(answers)
    if 'error' in results:
        current_app.logger.error(f"Lỗi trong quá trình process_answer_batch: {results.get('error')}")
        return jsonify(results), 400

    session['quiz_session'] = session_manager.to_dict()

    response_data = {
        'results': results,
        'session_correct_answers': session_manager.correct_answers,
        'session_total_answered': session_manager.correct_answers + session_manager.incorrect_answers
    }

    current_app.logger.debug("--- Kết thúc submit_answer_batch (Thành công) ---")
    return jsonify(response_data)


@quiz_learning_bp.route('/end_session', methods=['POST'])
@login_required
def end_session():
    """Kết thúc phiên học Quiz hiện tại."""
    current_app.logger.debug("--- Bắt đầu end_session ---")
    result = QuizSessionManager.end_quiz_session()
    current_app.logger.info(f"Phiên học Quiz cho người dùng {current_user.user_id} đã kết thúc theo yêu cầu. Kết quả: {result.get('message')}")
    current_app.logger.debug("--- Kết thúc end_session ---")
    return jsonify(result)


@quiz_learning_bp.route('/save_quiz_settings', methods=['POST'])
@login_required
def save_quiz_settings():
    """Lưu cài đặt số câu hỏi mặc định trong một phiên học Quiz của người dùng."""
    from flask import flash
    from mindstack_app.models import UserSession
    
    data = request.get_json()
    batch_size = data.get('batch_size')

    if batch_size is None or not isinstance(batch_size, int) or batch_size <= 0:
        flash('Kích thước nhóm câu hỏi không hợp lệ.', 'danger')
        return jsonify({'success': False, 'message': 'Kích thước nhóm câu hỏi không hợp lệ.'}), 400

    try:
        user = User.query.get(current_user.user_id)
        if user:
            if user.session_state:
                user.session_state.current_quiz_batch_size = batch_size
            else:
                new_sess = UserSession(user_id=user.user_id, current_quiz_batch_size=batch_size)
                db.session.add(new_sess)

            db.session.commit()
            flash('Cài đặt số câu hỏi mặc định đã được lưu.', 'success')
            return jsonify({'success': True, 'message': 'Cài đặt số câu hỏi mặc định đã được lưu.'})
        else:
            flash('Không tìm thấy người dùng.', 'danger')
            return jsonify({'success': False, 'message': 'Không tìm thấy người dùng.'}), 404
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi lưu cài đặt quiz của người dùng: {e}", exc_info=True)
        flash('Đã xảy ra lỗi khi lưu cài đặt.', 'danger')
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi lưu cài đặt.'}), 500


@quiz_learning_bp.route('/toggle_archive/<int:set_id>', methods=['POST'])
@login_required
def toggle_archive(set_id):
    """Xử lý yêu cầu archive hoặc unarchive một bộ quiz."""
    from flask import flash
    
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

        db.session.commit()

        status_text = "đã được lưu trữ." if is_currently_archived else "đã được bỏ lưu trữ."
        flash(f'Bộ quiz "{set_id}" {status_text}', 'success')

        return jsonify({'success': True, 'is_archived': is_currently_archived, 'message': f'Bộ quiz {status_text}'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi toggle archive cho bộ quiz {set_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi thay đổi trạng thái lưu trữ.'}), 500


@quiz_learning_bp.route('/bulk_unarchive', methods=['POST'])
@login_required
def bulk_unarchive():
    """Xử lý yêu cầu bỏ lưu trữ hàng loạt cho các bộ quiz đã chọn."""
    from flask import flash
    
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

        db.session.commit()

        if updated_count > 0:
            flash(f'Đã bỏ lưu trữ thành công {updated_count} bộ quiz.', 'success')
            return jsonify({'success': True, 'message': f'Đã bỏ lưu trữ thành công {updated_count} bộ quiz.'})
        else:
            return jsonify({'success': False, 'message': 'Không có bộ quiz nào được bỏ lưu trữ.'}), 400

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi bỏ lưu trữ hàng loạt: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi xử lý yêu cầu.'}), 500
