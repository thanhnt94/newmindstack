# File: newmindstack/mindstack_app/modules/learning/routes.py
# Phiên bản: 1.2
# Mục đích: Đăng ký blueprint cho module học Course.
# ĐÃ THÊM: Import và đăng ký course_learning_bp.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, current_app
from flask_login import login_required, current_user
from mindstack_app.models import LearningContainer
from .sub_modules.flashcard.services.session_service import LearningSessionService

# Import các blueprint con
from .sub_modules.quiz import quiz_battle_bp, quiz_learning_bp
from .sub_modules.flashcard import flashcard_bp
from .sub_modules.flashcard.individual.routes import flashcard_learning_bp
from .sub_modules.course.routes import course_bp
from .sub_modules.flashcard.collab.routes import flashcard_collab_bp
from .sub_modules.vocabulary import vocabulary_bp
from .sub_modules.practice import practice_bp
from .sub_modules.collab import collab_bp
from .api.markers import markers_bp  # NEW: Markers API
# from .sub_modules.stats import stats_bp
# Note: stats_api_bp is registered globally in module_registry.py


# Định nghĩa Blueprint chính cho learning
learning_bp = Blueprint('learning', __name__) # Các template chung cho learning (nếu có)

# Đăng ký các blueprint con
learning_bp.register_blueprint(quiz_learning_bp)
learning_bp.register_blueprint(flashcard_bp)
learning_bp.register_blueprint(flashcard_learning_bp)
learning_bp.register_blueprint(course_bp)
learning_bp.register_blueprint(quiz_battle_bp, url_prefix='/collab/quiz-battle')
learning_bp.register_blueprint(flashcard_collab_bp, url_prefix='/collab/flashcard-collab')
learning_bp.register_blueprint(vocabulary_bp)
learning_bp.register_blueprint(practice_bp)  # NEW: Practice module
learning_bp.register_blueprint(collab_bp)  # NEW: Collab module
# learning_bp.register_blueprint(markers_bp)  # MOVED: Registered globally in module_registry
# learning_bp.register_blueprint(stats_bp)  # Stats dashboard (HTML only, API is global)



@learning_bp.route('/')
@login_required
def learning_dashboard():
    """
    Mô tả: Hiển thị dashboard tổng quan cho các hoạt động học tập.
    Chuyển hướng đến trang stats dashboard.
    """
    return redirect(url_for('stats.dashboard'))


@learning_bp.route('/stats/dashboard')
@login_required
def legacy_stats_dashboard_redirect():
    """
    Redirect legacy /learn/stats/dashboard to new analytics dashboard.
    """
    return redirect(url_for('stats.dashboard'))


@learning_bp.route('/assets/v3/<path:filename>')
def serve_v3_asset(filename):
    """
    Serve static assets (CSS, JS, Images) directly from the V3 templates directory.
    This supports the co-location of assets with templates for easier management.
    """
    import os
    from flask import current_app, send_from_directory
    
    # Path to v3/pages/learning templates
    directory = os.path.join(current_app.root_path, 'templates', 'v3', 'pages', 'learning')
    return send_from_directory(directory, filename)


def get_mode_description(session):
    """Generate a detailed description for a learning session."""
    mode_map = {
        # Flashcard
        'new_only': 'Học từ mới',
        'due_only': 'Ôn tập tới hạn',
        'hard_only': 'Các từ khó',
        'mixed_srs': 'Học ngẫu nhiên (SRS)',
        'all_review': 'Ôn tập tất cả',
        'pronunciation_practice': 'Luyện phát âm',
        'writing_practice': 'Luyện chính tả',
        'quiz_practice': 'Làm Flashcard trắc nghiệm',
        'essay_practice': 'Luyện viết luận',
        'listening_practice': 'Luyện nghe',
        'speaking_practice': 'Luyện nói',
        'autoplay_all': 'Tự động phát (Tất cả)',
        'autoplay_learned': 'Tự động phát (Đã học)',
        
        # Quiz
        'quiz': 'Trắc nghiệm (Quiz)',
        'multiple_choice': 'Trắc nghiệm (MCQ)',
        
        # Vocabulary Games
        'typing': 'Gõ từ',
        'listening': 'Nghe chép chính tả',
        'matching': 'Ghép thẻ',
        'mcq': 'Trắc nghiệm (MCQ Game)',
        'matching_game': 'Ghép thẻ' 
    }
    
    base_name = mode_map.get(session.mode_config_id, session.mode_config_id)
    
    # Customize based on mode
    if session.learning_mode == 'typing':
        return f"Gõ từ • {session.total_items} câu"
    elif session.learning_mode == 'listening':
        return f"Nghe chép chính tả • {session.total_items} câu"
    elif session.learning_mode == 'matching':
        return f"Ghép thẻ • 6 cặp" # Matching usually fixed
    elif session.learning_mode == 'mcq':
        return f"Trắc nghiệm • {session.total_items} câu"
    elif session.learning_mode == 'quiz':
        # Quiz might have config id like 'random_10' or just 'random'
        return f"Quiz • {session.total_items} câu"
    
    # Fallback for Flashcard
    if session.learning_mode == 'flashcard':
        return base_name

    return base_name

@learning_bp.route('/session')
@login_required
def manage_sessions():
    """ Trang quản lý các phiên học đang hoạt động. """
    current_app.logger.debug(f"Accessing manage_sessions for user {current_user.user_id}")
    try:
        sessions = LearningSessionService.get_active_sessions(current_user.user_id)
        current_app.logger.debug(f"Found {len(sessions)} active sessions")
    except Exception as e:
        current_app.logger.error(f"Error fetching active sessions: {e}")
        sessions = []

    session_list = []
    for s in sessions:
        container_name = "Bộ học tập"
        try:
            if isinstance(s.set_id_data, int):
                container = LearningContainer.query.get(s.set_id_data)
                if container: container_name = container.title
            elif isinstance(s.set_id_data, list):
                container_name = f"{len(s.set_id_data)} bộ học tập"
        except Exception as e:
             current_app.logger.warning(f"Error resolving container: {e}")
             pass
        
        # Determine Resume URL
        if s.learning_mode == 'quiz':
            resume_url = url_for('learning.quiz_learning.quiz_session')
        elif s.learning_mode == 'typing':
            resume_url = url_for('learning.vocabulary.typing.session_page')
        elif s.learning_mode == 'listening':
            resume_url = url_for('learning.vocabulary.listening.session_page')
        elif s.learning_mode == 'matching':
            # Matching sessions are usually short-lived games, but if we support resume:
            resume_url = url_for('learning.vocabulary.matching.session_page', set_id=s.set_id_data)
        elif s.learning_mode == 'mcq':
            resume_url = url_for('learning.vocabulary.mcq.session', set_id=s.set_id_data)
        else:
            resume_url = url_for('learning.flashcard_learning.flashcard_session')

        session_list.append({
            'session_id': s.session_id,
            'learning_mode': s.learning_mode,
            'mode_name': get_mode_description(s),
            'container_name': container_name,
            'done': len(s.processed_item_ids or []),
            'total': s.total_items,
            'start_time': s.start_time,
            'resume_url': resume_url
        })
    
    # Fetch History
    try:
        history_raw = LearningSessionService.get_session_history(current_user.user_id)
        current_app.logger.debug(f"Found {len(history_raw)} history sessions")
    except Exception as e:
        current_app.logger.error(f"Error fetching history: {e}")
        history_raw = []

    history_list = []
    for h in history_raw:
        container_name = "Bộ học tập"
        try:
            if isinstance(h.set_id_data, int):
                container = LearningContainer.query.get(h.set_id_data)
                if container: container_name = container.title
            elif isinstance(h.set_id_data, list):
                container_name = f"{len(h.set_id_data)} bộ học tập"
        except Exception as e:
             current_app.logger.warning(f"Error resolving container for history: {e}")
             pass
        
        try:
            desc = get_mode_description(h)
        except Exception as e:
             current_app.logger.warning(f"Error getting mode description: {e}")
             desc = "Phiên học"

        history_list.append({
            'session_id': h.session_id,
            'learning_mode': h.learning_mode,
            'mode_name': desc,
            'container_name': container_name,
            'start_time': h.start_time,
            'end_time': h.end_time,
            'status': h.status,
            'correct': h.correct_count,
            'incorrect': h.incorrect_count,
            'processed': len(h.processed_item_ids or []),
            'total': h.total_items,
            'points': h.points_earned
        })
    
    current_app.logger.debug("Rendering v3/pages/learning/sessions.html")
    return render_template('v3/pages/learning/sessions.html', sessions=session_list, history=history_list)


@learning_bp.route('/session/<session_id>/summary')
@login_required
def session_summary(session_id):
    """
    Displays the summary page for a specific (completed) session.
    """
    session = LearningSessionService.get_session_by_id(session_id)
    if not session or session.user_id != current_user.user_id:
        abort(404)
        
    container_name = "Bộ học tập"
    try:
        if isinstance(session.set_id_data, int):
            container = LearningContainer.query.get(session.set_id_data)
            if container: container_name = container.title
        elif isinstance(session.set_id_data, list) and len(session.set_id_data) > 0:
            container_name = f"{len(session.set_id_data)} bộ học tập"
    except: pass
    
    # Calculate duration
    duration_str = "0m"
    if session.start_time and session.end_time:
        delta = session.end_time - session.start_time
        minutes = int(delta.total_seconds() // 60)
        seconds = int(delta.total_seconds() % 60)
        duration_str = f"{minutes}m {seconds}s"
        
    summary_data = {
        'session_id': session.session_id,
        'mode_name': get_mode_description(session),
        'container_name': container_name,
        'start_time': session.start_time,
        'end_time': session.end_time,
        'duration': duration_str,
        'correct': session.correct_count,
        'wrong': session.incorrect_count,
        'points': session.points_earned,
        'total': session.total_items or (session.correct_count + session.incorrect_count + session.vague_count)
    }
    
    # Calculate accuracy
    total_answered = summary_data['correct'] + summary_data['wrong']
    if total_answered > 0:
        summary_data['accuracy'] = round((summary_data['correct'] / total_answered) * 100)
    else:
        summary_data['accuracy'] = 0

    return render_template(
        'v3/pages/learning/session_summary.html',
        summary=summary_data,
        set_id=session.set_id_data if isinstance(session.set_id_data, int) else None
    )


@learning_bp.route('/api/active')
@login_required
def api_active_sessions():
    """ API endpoint cho danh sách phiên học active. """
    sessions = LearningSessionService.get_active_sessions(current_user.user_id)
    
    result = []
    for s in sessions:
        container_name = "Bộ học tập"
        try:
            if isinstance(s.set_id_data, int):
                container = LearningContainer.query.get(s.set_id_data)
                if container: container_name = container.title
            elif isinstance(s.set_id_data, list) and len(s.set_id_data) > 0:
                container_name = f"{len(s.set_id_data)} bộ học tập"
        except: pass

        # Determine Resume URL
        if s.learning_mode == 'quiz':
            resume_url = url_for('learning.quiz_learning.quiz_session')
        elif s.learning_mode == 'typing':
            resume_url = url_for('learning.vocabulary.typing.session_page')
        elif s.learning_mode == 'listening':
            resume_url = url_for('learning.vocabulary.listening.session_page')
        elif s.learning_mode == 'matching':
            resume_url = url_for('learning.vocabulary.matching.session_page', set_id=s.set_id_data)
        elif s.learning_mode == 'mcq':
            resume_url = url_for('learning.vocabulary.mcq.session', set_id=s.set_id_data)
        else:
            resume_url = url_for('learning.flashcard_learning.flashcard_session')

        result.append({
            'session_id': s.session_id,
            'learning_mode': s.learning_mode,
            'mode_name': get_mode_description(s),
            'container_name': container_name,
            'progress': {'done': len(s.processed_item_ids or []), 'total': s.total_items},
            'resume_url': resume_url
        })
    return jsonify(result)
