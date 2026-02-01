
# File: mindstack_app/modules/session/routes/api.py
from flask import request, jsonify, current_app, url_for
from flask_login import login_required, current_user
from .. import blueprint
from mindstack_app.modules.vocab_flashcard.services.session_service import LearningSessionService
from mindstack_app.models import LearningContainer, db

def safe_url_for(endpoint, **values):
    try:
        return url_for(endpoint, **values)
    except Exception as e:
        current_app.logger.warning(f"[SESSION MODULE] Failed to build url for endpoint '{endpoint}': {e}")
        return '#'

def get_mode_description(session):
    """Generate a detailed description for a learning session."""
    mode_map = {
        'new_only': 'Học từ mới',
        'due_only': 'Ôn tập tới hạn',
        'hard_only': 'Các từ khó',
        'mixed_srs': 'Học ngẫu nhiên (SRS)',
        'all_review': 'Ôn tập tất cả',
        'typing': 'Gõ từ',
        'listening': 'Nghe chép chính tả',
        'matching': 'Ghép thẻ',
        'mcq': 'Trắc nghiệm (MCQ Game)',
        'quiz': 'Trắc nghiệm (Quiz)',
        'flashcard': 'Flashcard',
        'speed': 'Ôn nhanh'
    }
    base_name = mode_map.get(session.mode_config_id, session.mode_config_id)
    # Customize description based on specific modes if needed
    if session.learning_mode in ['typing', 'listening', 'mcq', 'quiz']:
        return f"{base_name} • {session.total_items} câu"
    return base_name

@blueprint.route('/api/active')
@login_required
def api_get_active_sessions():
    """Nhận danh sách các phiên học đang hoạt động của người dùng."""
    try:
        active_sessions = LearningSessionService.get_active_sessions(current_user.user_id)
        results = []
        for s in active_sessions:
            container_name = "Bộ học tập"
            try:
                if isinstance(s.set_id_data, int):
                    container = LearningContainer.query.get(s.set_id_data)
                    if container: 
                        container_name = container.title
                elif isinstance(s.set_id_data, list):
                    container_name = f"{len(s.set_id_data)} bộ học tập"
            except Exception as e:
                current_app.logger.warning(f"Error resolving container name: {e}")

            # Determine Resume URL based on learning mode
            resume_url = '#'
            mode = s.learning_mode
            
            if mode == 'quiz':
                resume_url = safe_url_for('quiz.quiz_session', session_id=s.session_id)
            elif mode == 'typing':
                resume_url = safe_url_for('vocab_typing.typing_session_page')
            elif mode == 'listening':
                # Ưu tiên module vocab_listening mới, fallback về vocabulary cũ nếu cần
                resume_url = safe_url_for('vocab_listening.listening_session_page')
                if resume_url == '#':
                     resume_url = safe_url_for('vocabulary.listening_session_page')
            elif mode == 'matching':
                resume_url = safe_url_for('vocab_matching.matching_session_page', set_id=s.set_id_data)
            elif mode == 'mcq':
                resume_url = safe_url_for('vocab_mcq.mcq_session', set_id=s.set_id_data)
            elif mode == 'speed':
                resume_url = safe_url_for('vocab_speed.speed_session_page', set_id=s.set_id_data)
            else:
                # Default to Flashcard
                resume_url = safe_url_for('vocab_flashcard.flashcard_learning.flashcard_session', session_id=s.session_id)

            results.append({
                'session_id': s.session_id,
                'learning_mode': s.learning_mode,
                'mode_name': get_mode_description(s),
                'container_name': container_name,
                'progress': {'done': len(s.processed_item_ids or []), 'total': s.total_items},
                'resume_url': resume_url
            })
        return jsonify(results)
    except Exception as e:
        current_app.logger.error(f"Error getting active sessions API: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@blueprint.route('/api/check_active/<int:set_id>')
@login_required
def check_active_vocab_session(set_id):
    """Kiểm tra xem có phiên nào đang active cho bộ thẻ này không."""
    try:
        active_session = LearningSessionService.get_any_active_vocabulary_session(current_user.user_id, set_id)
        if active_session:
            resume_url = '#'
            mode = active_session.learning_mode
            
            if mode == 'flashcard': 
                resume_url = safe_url_for('vocab_flashcard.flashcard_learning.flashcard_session', session_id=active_session.session_id)
            elif mode == 'mcq': 
                resume_url = safe_url_for('vocab_mcq.mcq_session', set_id=set_id)
            elif mode == 'typing': 
                resume_url = safe_url_for('vocab_typing.typing_session_page')
            elif mode == 'listening': 
                resume_url = safe_url_for('vocab_listening.listening_session_page')
            elif mode == 'matching': 
                resume_url = safe_url_for('vocab_matching.matching_session_page', set_id=set_id)
            elif mode == 'speed': 
                resume_url = safe_url_for('vocab_speed.speed_session_page', set_id=set_id)
            
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
    except Exception as e:
        current_app.logger.error(f"Error checking active session: {e}", exc_info=True)
        return jsonify({'has_active': False, 'error': str(e)}), 500

