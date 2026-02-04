# File: mindstack_app/modules/quiz/routes/individual_api.py
import os
import copy
from typing import Optional

from flask import request, jsonify, abort, current_app, session, url_for
from flask_login import login_required, current_user
from sqlalchemy.sql import func
from sqlalchemy.orm.attributes import flag_modified

from .. import quiz_bp as blueprint
from ..logics.session_logic import QuizSessionManager
from ..logics.algorithms import get_accessible_quiz_set_ids
from ..services.audio_service import QuizAudioService
from mindstack_app.models import (
    LearningContainer,
    LearningItem,
    User,
    UserContainerState,
    Note,
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
        return url_for('media_uploads', filename=static_path)
    except Exception as exc:
        current_app.logger.error(f"Không thể tạo URL tuyệt đối cho media '{file_path}': {exc}")
        return file_path


def _serialize_quiz_learning_item(item, user_id):
    from mindstack_app.modules.content_management.interface import ContentInterface
    
    # 1. Get standardized content (handles media URLs)
    content_map = ContentInterface.get_items_content([item.item_id])
    std_content = content_map.get(item.item_id) or {}
    
    # 2. Re-construct content copy for frontend compatibility
    # Frontend expects: options (A, B, C, D keys), question_image_file, question_audio_file
    
    # ContentInterface maps: 
    # image -> question_image_file
    # audio -> question_audio_file
    # options -> options
    
    content_copy = dict(std_content)
    
    # Map back standardized keys to frontend legacy keys
    # Note: std_content has 'image', 'audio'. Frontend might expect 'question_image_file'.
    if 'image' in content_copy:
        content_copy['question_image_file'] = content_copy.pop('image')
    if 'audio' in content_copy:
        content_copy['question_audio_file'] = content_copy.pop('audio')
        
    # Ensure options are clean (already handled by interface if it just copied raw, but interface is just a filtered pass)
    # Actually Interface just returns what's in DB for options.
    options = content_copy.get('options') or {}
    valid_options = {}
    for key in ['A', 'B', 'C', 'D']:
        val = options.get(key)
        if val not in (None, ''):
            valid_options[key] = val
    content_copy['options'] = valid_options

    # Fetch Note
    note = Note.query.filter_by(user_id=user_id, reference_type='item', reference_id=item.item_id).first()

    # Permissions (Container based)
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


@blueprint.route('/api/items/<int:item_id>', methods=['GET'])
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


@blueprint.route('/get_question_batch', methods=['GET'])
@login_required
def get_question_batch():
    """Trả về dữ liệu nhóm câu hỏi tiếp theo trong phiên học hiện tại."""
    if 'quiz_session' not in session:
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 404

    session_manager = QuizSessionManager.from_dict(session['quiz_session'])
    batch_size = session_manager.batch_size
    try:
        question_batch = session_manager.get_next_batch(batch_size)
        session['quiz_session'] = session_manager.to_dict()

        if question_batch is None:
            db_session_id = None
            if 'quiz_session' in session:
                db_session_id = session['quiz_session'].get('db_session_id')

            session_manager.end_quiz_session()
            
            response = {'message': 'Bạn đã hoàn thành tất cả các câu hỏi trong phiên học này!'}
            if db_session_id:
                response['session_id'] = db_session_id
                
            return jsonify(response), 404

        question_batch['session_correct_answers'] = session_manager.correct_answers
        question_batch['session_total_answered'] = session_manager.correct_answers + session_manager.incorrect_answers

        return jsonify(question_batch)

    except Exception as e:
        current_app.logger.error(f"LỖI NGHIÊM TRỌNG khi lấy nhóm câu hỏi: {e}", exc_info=True)
        return jsonify({'message': f'Lỗi khi tải câu hỏi: {str(e)}'}), 500


@blueprint.route('/api/transcript/<int:item_id>', methods=['POST'])
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

        if not audio_rel_path:
            return jsonify({'success': False, 'message': 'Không tìm thấy thông tin audio (URL) trong dữ liệu câu hỏi.'}), 400

        audio_folder = _get_media_folders_from_container(container).get('audio')
        relative_path = build_relative_media_path(audio_rel_path, audio_folder)

        if not relative_path:
            return jsonify({'success': False, 'message': 'Không thể xác định đường dẫn file audio.'}), 400

        if relative_path.startswith(('http://', 'https://')):
            return jsonify({'success': False, 'message': 'Audio là URL ngoài, không hỗ trợ transcript tự động.'}), 400

        candidates = [
            current_app.config.get('UPLOAD_FOLDER'),
            current_app.static_folder,
            os.path.join(current_app.root_path, 'static'),
            os.path.abspath(os.path.join(current_app.root_path, '..', 'uploads'))
        ]

        full_path = None
        for base in candidates:
            if not base: continue
            p = os.path.join(base, relative_path)
            if os.path.exists(p):
                full_path = p
                break

        if not full_path:
            return jsonify({'success': False, 'message': 'Không tìm thấy file audio trên server.'}), 400

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


@blueprint.route('/api/transcript/<int:item_id>/update', methods=['POST'])
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


@blueprint.route('/api/items/batch', methods=['POST'])
@login_required
def submit_answer_batch():
    """Nhận một danh sách các câu trả lời của người dùng, xử lý và cập nhật tiến độ."""
    data = request.get_json()
    answers = data.get('answers')

    if not answers or not isinstance(answers, list):
        return jsonify({'error': 'Dữ liệu đáp án không hợp lệ.'}), 400

    if 'quiz_session' not in session:
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 404

    session_manager = QuizSessionManager.from_dict(session['quiz_session'])
    if not session_manager:
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 404

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
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Lỗi khi cập nhật last_accessed cho bộ quiz {s_id}: {e}", exc_info=True)

    try:
        results = session_manager.process_answer_batch(answers)
        if 'error' in results:
            return jsonify(results), 400

        session['quiz_session'] = session_manager.to_dict()

        response_data = {
            'results': results,
            'session_correct_answers': session_manager.correct_answers,
            'session_total_answered': session_manager.correct_answers + session_manager.incorrect_answers,
            'new_total_score': current_user.total_score
        }

        return jsonify(response_data)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"LỖI NGHIÊM TRỌNG trong submit_answer_batch: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500


@blueprint.route('/end_session', methods=['POST'])
@login_required
def end_session():
    """Kết thúc phiên học Quiz hiện tại."""
    db_session_id = None
    if 'quiz_session' in session:
        db_session_id = session['quiz_session'].get('db_session_id')
    
    result = QuizSessionManager.end_quiz_session()
    
    if db_session_id:
        result['session_id'] = db_session_id
        
    return jsonify(result)


@blueprint.route('/save_quiz_settings', methods=['POST'])
@login_required
def save_quiz_settings():
    """Lưu cài đặt số câu hỏi mặc định trong một phiên học Quiz của người dùng."""
    from mindstack_app.models import UserSession
    
    data = request.get_json()
    batch_size = data.get('batch_size')

    if batch_size is None or not isinstance(batch_size, int) or batch_size <= 0:
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
            return jsonify({'success': True, 'message': 'Cài đặt số câu hỏi mặc định đã được lưu.'})
        else:
            return jsonify({'success': False, 'message': 'Không tìm thấy người dùng.'}), 404
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi lưu cài đặt quiz của người dùng: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi lưu cài đặt.'}), 500


@blueprint.route('/toggle_archive/<int:set_id>', methods=['POST'])
@login_required
def toggle_archive(set_id):
    """Xử lý yêu cầu archive hoặc unarchive một bộ quiz."""
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
        return jsonify({'success': True, 'is_archived': is_currently_archived, 'message': f'Bộ quiz {status_text}'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi toggle archive cho bộ quiz {set_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi thay đổi trạng thái lưu trữ.'}), 500


@blueprint.route('/bulk_unarchive', methods=['POST'])
@login_required
def bulk_unarchive():
    """Xử lý yêu cầu bỏ lưu trữ hàng loạt cho các bộ quiz đã chọn."""
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
            return jsonify({'success': True, 'message': f'Đã bỏ lưu trữ thành công {updated_count} bộ quiz.'})
        else:
            return jsonify({'success': False, 'message': 'Không có bộ quiz nào được bỏ lưu trữ.'}), 400

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi bỏ lưu trữ hàng loạt: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi xử lý yêu cầu.'}), 500


@blueprint.route('/api/items', methods=['GET'])
@login_required
def api_get_quiz_sets():
    """API to get quiz sets with search and category filter."""
    search = request.args.get('q', '').strip()
    category = request.args.get('category', 'my')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    query = LearningContainer.query.filter(
        LearningContainer.container_type == 'QUIZ_SET'
    )
    
    if category == 'my':
        query = query.filter(LearningContainer.creator_user_id == current_user.user_id)
    elif category == 'learning':
        learning_ids = [
            ucs.container_id for ucs in 
            UserContainerState.query.filter_by(
                user_id=current_user.user_id,
                is_archived=False
            ).all()
        ]
        query = query.filter(LearningContainer.container_id.in_(learning_ids))
    elif category == 'explore':
        query = query.filter(
            LearningContainer.is_public == True
        )
    
    if search:
        query = query.filter(
            or_(
                LearningContainer.title.ilike(f'%{search}%'),
                LearningContainer.description.ilike(f'%{search}%')
            )
        )
    
    query = query.order_by(LearningContainer.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    sets = []
    for c in pagination.items:
        question_count = LearningItem.query.filter(
            LearningItem.container_id == c.container_id,
            LearningItem.item_type.in_(['QUESTION', 'FLASHCARD', 'QUIZ_MCQ'])
        ).count()
        
        creator = User.query.get(c.creator_user_id)
        
        sets.append({
            'id': c.container_id,
            'title': c.title,
            'description': c.description or '',
            'cover_image': c.cover_image,
            'question_count': question_count,
            'creator_name': creator.username if creator else 'Unknown',
            'is_public': c.is_public,
        })
    
    return jsonify({
        'success': True,
        'sets': sets,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
        'page': page,
        'total': pagination.total
    })


@blueprint.route('/api/sets/<int:set_id>/detail')
@login_required
def api_get_quiz_set_detail(set_id):
    """API to get detailed info about a specific quiz set."""
    from ..logics.algorithms import get_quiz_mode_counts
    
    container = LearningContainer.query.get_or_404(set_id)
    
    # Get questions
    questions = LearningItem.query.filter(
        LearningItem.container_id == set_id,
        LearningItem.item_type.in_(['QUESTION', 'FLASHCARD', 'QUIZ_MCQ'])
    ).order_by(LearningItem.order_index).all()
    
    question_count = len(questions)

    # [REFACTORED] Use ContentInterface
    from mindstack_app.modules.content_management.interface import ContentInterface
    q_ids = [q.item_id for q in questions]
    content_map = ContentInterface.get_items_content(q_ids)

    # Helper to map std content to legacy frontend expected format
    def format_content(std_c):
        c = dict(std_c or {})
        if 'image' in c: c['question_image_file'] = c.pop('image')
        if 'audio' in c: c['question_audio_file'] = c.pop('audio')
        return c

    # Get creator info
    creator = User.query.get(container.creator_user_id)
    
    # Get user access count
    user_state = UserContainerState.query.filter_by(
        user_id=current_user.user_id,
        container_id=set_id
    ).first()
    access_count = 1 if user_state and user_state.last_accessed else 0
    
    # Get available modes
    try:
        modes = get_quiz_mode_counts(current_user.user_id, set_id)
    except:
        modes = [
            {'id': 'all', 'name': 'Tất cả'},
            {'id': 'new_only', 'name': 'Câu mới'},
            {'id': 'due_only', 'name': 'Ôn tập'},
        ]
    
    return jsonify({
        'success': True,
        'set': {
            'id': container.container_id,
            'title': container.title,
            'description': container.description or '',
            'question_count': question_count,
            'creator_name': creator.username if creator else 'Unknown',
            'access_count': access_count,
        },
        'questions': [
            {'id': q.item_id, 'content': format_content(content_map.get(q.item_id))}
            for q in questions
        ],
        'modes': modes
    })

@blueprint.route('/api/item/<int:item_id>/generate-ai', methods=['POST'])
@login_required
def api_generate_quiz_ai_explanation(item_id):
    """Generate AI explanation for a quiz item."""
    from mindstack_app.modules.AI.interface import generate_content
    from mindstack_app.modules.AI.logics.prompts import get_formatted_prompt
    
    item = LearningItem.query.get_or_404(item_id)
    
    try:
        prompt = get_formatted_prompt(item, purpose="explanation")
        if not prompt:
            return jsonify({'success': False, 'message': 'Không thể tạo prompt cho học liệu này.'}), 400
            
        item_info = f"{item.item_type} ID {item.item_id}"
        response = generate_content(prompt, feature="explanation", context_ref=item_info)
        
        if not response.success:
            return jsonify({'success': False, 'message': f'Lỗi từ AI: {response.error}'}), 500
            
        item.ai_explanation = response.content
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Đã tạo nội dung AI thành công.', 'explanation': response.content})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error generating AI explanation for item {item_id}: {e}")
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi hệ thống.'}), 500

@blueprint.route('/api/sets')
@login_required
def api_get_practice_quiz_sets():
    """API lấy danh sách bộ Quiz cho practice."""
    from ..logics.algorithms import get_filtered_quiz_sets
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)

    try:
        pagination = get_filtered_quiz_sets(
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
                'question_count': getattr(item, 'question_count', 0),
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
def api_get_quiz_modes(set_identifier):
    """API lấy các chế độ học Quiz với số lượng câu hỏi."""
    from ..logics.algorithms import get_quiz_mode_counts
    
    try:
        if set_identifier == 'all':
            modes = get_quiz_mode_counts(current_user.user_id, 'all')
        else:
            set_ids = [int(s) for s in set_identifier.split(',') if s]
            if len(set_ids) == 1:
                modes = get_quiz_mode_counts(current_user.user_id, set_ids[0])
            else:
                modes = get_quiz_mode_counts(current_user.user_id, set_ids)
        
        return jsonify({'success': True, 'modes': modes})
    except ValueError:
        return jsonify({'success': False, 'message': 'ID bộ quiz không hợp lệ.'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
