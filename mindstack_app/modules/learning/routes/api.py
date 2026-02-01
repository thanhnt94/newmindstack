# File: mindstack_app/modules/learning/routes/api.py
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from .. import learning_bp as blueprint
from mindstack_app.modules.vocab_flashcard.services.session_service import LearningSessionService
from mindstack_app.models import LearningContainer, db
from flask import url_for

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
        'quiz': 'Trắc nghiệm (Quiz)'
    }
    base_name = mode_map.get(session.mode_config_id, session.mode_config_id)
    if session.learning_mode in ['typing', 'listening', 'mcq', 'quiz']:
        return f"{base_name} • {session.total_items} câu"
    return base_name

@blueprint.route('/api/active')
@login_required
def api_get_active_sessions():
    try:
        active_sessions = LearningSessionService.get_active_sessions(current_user.user_id)
        results = []
        for s in active_sessions:
            container_name = "Bộ học tập"
            try:
                if isinstance(s.set_id_data, int):
                    container = LearningContainer.query.get(s.set_id_data)
                    if container: container_name = container.title
                elif isinstance(s.set_id_data, list):
                    container_name = f"{len(s.set_id_data)} bộ học tập"
            except: pass

            if s.learning_mode == 'quiz':
                resume_url = url_for('quiz.quiz_session', session_id=s.session_id)
            elif s.learning_mode == 'typing':
                resume_url = url_for('vocab_typing.typing_session_page')
            elif s.learning_mode == 'listening':
                resume_url = url_for('vocabulary.listening_session_page')
            elif s.learning_mode == 'matching':
                resume_url = url_for('vocab_matching.matching_session_page', set_id=s.set_id_data)
            elif s.learning_mode == 'mcq':
                resume_url = url_for('vocab_mcq.mcq_session', set_id=s.set_id_data)
            else:
                resume_url = url_for('vocab_flashcard.flashcard_learning.flashcard_session', session_id=s.session_id)

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
        current_app.logger.error(f"Error getting active sessions API: {e}")
        return jsonify([]), 500

@blueprint.route('/api/check_active_vocab_session/<int:set_id>')
@login_required
def check_active_vocab_session(set_id):
    active_session = LearningSessionService.get_any_active_vocabulary_session(current_user.user_id, set_id)
    if active_session:
        resume_url = '#'
        mode = active_session.learning_mode
        if mode == 'flashcard': resume_url = url_for('vocab_flashcard.flashcard_learning.flashcard_session', session_id=active_session.session_id)
        elif mode == 'mcq': resume_url = url_for('vocab_mcq.mcq_session', set_id=set_id)
        elif mode == 'typing': resume_url = url_for('vocab_typing.typing_session_page')
        elif mode == 'listening': resume_url = url_for('vocab_listening.listening_session_page')
        elif mode == 'matching': resume_url = url_for('vocab_matching.matching_session_page', set_id=set_id)
        elif mode == 'speed': resume_url = url_for('vocab_speed.speed_session_page', set_id=set_id)
        
        mode_names = {'flashcard': 'Flashcard', 'mcq': 'Trắc nghiệm (MCQ)', 'typing': 'Gõ từ (Typing)', 'listening': 'Luyện nghe', 'matching': 'Nối từ', 'speed': 'Ôn nhanh (Speed)'}
        return jsonify({'has_active': True, 'active_mode': mode, 'active_mode_display': mode_names.get(mode, mode), 'resume_url': resume_url})
    return jsonify({'has_active': False})

@blueprint.route('/api/stats/summary')
@login_required
def api_stats_summary():
    """Delegated to Stats module via Analytics Service."""
    from mindstack_app.modules.stats.services.analytics_service import AnalyticsService
    summary = AnalyticsService.get_dashboard_overview(current_user.user_id)
    return jsonify(summary)
