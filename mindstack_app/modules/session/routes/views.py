# File: mindstack_app/modules/session/routes/views.py
from flask import render_template, request, redirect, url_for, flash, abort, current_app
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from mindstack_app.models import LearningContainer, LearningItem, db
from ..services.session_service import LearningSessionService
# REFAC: StudyLog removed (Isolation)
from .. import blueprint
from .api import safe_url_for

def get_mode_description(session):
    """Generate a detailed human-readable description for a learning session."""
    # 1. Map Core Strategy/Config
    strategy_map = {
        'mixed_srs': 'Lộ trình SRS',
        'new_only': 'Học từ mới',
        'due_only': 'Ôn tập tới hạn',
        'hard_only': 'Các từ khó',
        'all_review': 'Ôn tập tất cả',
        'sequential': 'Học theo thứ tự',
        'srs': 'Lộ trình SRS',
        # MCQ Specific Configs
        'front_back': 'Từ -> Nghĩa',
        'back_front': 'Nghĩa -> Từ',
        'audio_back': 'Nghe âm thanh',
        'image_back': 'Nhìn ảnh',
        'audio_front': 'Nghe chọn từ',
    }
    
    # 2. Map Learning Game/Mode
    game_map = {
        'flashcard': 'Flashcard',
        'mcq': 'Trắc nghiệm',
        'typing': 'Gõ từ',
        'listening': 'Nghe chép',
        'matching': 'Ghép thẻ',
        'quiz': 'Quiz',
        'speed': 'Ôn nhanh'
    }
    
    strategy = strategy_map.get(session.mode_config_id, session.mode_config_id)
    game = game_map.get(session.learning_mode, session.learning_mode.upper())
    
    # Structure the description
    if session.learning_mode == 'flashcard':
        desc = f"{game} • {strategy}"
    elif session.learning_mode == 'quiz':
        desc = f"{game} ({session.total_items} câu)"
    else:
        # For MCQ, Typing, etc. Strategy often represents the question direction/type
        desc = f"{game} • {strategy}"
        if session.total_items:
            desc += f" • {session.total_items} câu"
            
    return desc

@blueprint.route('/')
@login_required
def manage_sessions():
    """Trang quản lý các phiên học đang hoạt động (Thay thế /learn/session cũ)."""
    try:
        # Standard Pagination Params
        page_active = request.args.get('page_active', 1, type=int)
        page_history = request.args.get('page_history', 1, type=int)
        per_page = 10 

        # 1. Active Sessions
        all_sessions = LearningSessionService.get_active_sessions(current_user.user_id)
        
        # Manual Pagination for Active List
        total_active = len(all_sessions)
        start_active = (page_active - 1) * per_page
        end_active = start_active + per_page
        current_sessions = all_sessions[start_active:end_active]
        
        session_list = []
        for s in current_sessions:
            container_name = "Bộ học tập"
            try:
                if isinstance(s.set_id_data, int):
                    container = LearningContainer.query.get(s.set_id_data)
                    if container: container_name = container.title
                elif isinstance(s.set_id_data, list):
                    container_name = f"{len(s.set_id_data)} bộ học tập"
            except Exception as e:
                current_app.logger.warning(f"Error fetching container info: {e}")
            
            # Determine Resume URL based on learning mode
            resume_url = '#'
            if s.learning_mode == 'quiz':
                resume_url = safe_url_for('quiz.quiz_session', session_id=s.session_id)
            elif s.learning_mode == 'typing':
                resume_url = safe_url_for('vocab_typing.typing_session_page')
            elif s.learning_mode == 'listening':
                # Prefer updated module, fallback to legacy
                resume_url = safe_url_for('vocab_listening.listening_session_page')
                if resume_url == '#': resume_url = safe_url_for('vocabulary.listening_session_page')
            elif s.learning_mode == 'matching':
                resume_url = safe_url_for('vocab_matching.matching_session_page', set_id=s.set_id_data)
            elif s.learning_mode == 'mcq':
                resume_url = safe_url_for('vocab_mcq.mcq_session', set_id=s.set_id_data)
            elif s.learning_mode == 'speed':
                resume_url = safe_url_for('vocab_speed.speed_session_page', set_id=s.set_id_data)
            else:
                 # Default to Flashcard
                 resume_url = safe_url_for('vocab_flashcard.flashcard_session', session_id=s.session_id)
    
            session_list.append({
                'session_id': s.session_id,
                'mode_name': get_mode_description(s),
                'container_name': container_name,
                'done': len(s.processed_item_ids or []),
                'total': s.total_items,
                'resume_url': resume_url,
                'start_time': s.start_time,
                'learning_mode': s.learning_mode
            })
            
        pagination_active = {
            'page': page_active,
            'per_page': per_page,
            'total': total_active,
            'pages': (total_active + per_page - 1) // per_page,
            'has_prev': page_active > 1,
            'has_next': end_active < total_active,
            'prev_num': page_active - 1,
            'next_num': page_active + 1
        }
        
        # 2. History
        all_history = LearningSessionService.get_session_history(current_user.user_id)
        
        # Manual Pagination for History List
        total_history = len(all_history)
        start_history = (page_history - 1) * per_page
        end_history = start_history + per_page
        current_history = all_history[start_history:end_history]

        history_list = []
        for h in current_history:
            container_name = "Bộ học tập"
            try:
                if isinstance(h.set_id_data, int):
                    container = LearningContainer.query.get(h.set_id_data)
                    if container: container_name = container.title
                elif isinstance(h.set_id_data, list):
                    container_name = f"{len(h.set_id_data)} bộ học tập"
            except: pass
            
            history_list.append({
                'session_id': h.session_id,
                'mode_name': get_mode_description(h),
                'container_name': container_name,
                'start_time': h.start_time,
                'end_time': h.end_time,
                'status': h.status,
                'correct': h.correct_count,
                'incorrect': h.incorrect_count,
                'total': h.total_items,
                'points': h.points_earned,
                'learning_mode': h.learning_mode
            })
            
        pagination_history = {
            'page': page_history,
            'per_page': per_page,
            'total': total_history,
            'pages': (total_history + per_page - 1) // per_page,
            'has_prev': page_history > 1,
            'has_next': end_history < total_history,
            'prev_num': page_history - 1,
            'next_num': page_history + 1
        }
        
        return render_template('aura_mobile/modules/learning/sessions.html', 
                             sessions=session_list, 
                             history=history_list,
                             pagination_active=pagination_active,
                             pagination_history=pagination_history)
    except Exception as e:
        current_app.logger.error(f"Error loading sessions page: {e}", exc_info=True)
        return f"Error loading sessions: {e}", 500

@blueprint.route('/<session_id>/summary')
@login_required
def session_summary(session_id):
    """Redirect to the new Session Hub summary page."""
    page = request.args.get('page', 1, type=int)
    return redirect(url_for('session_hub.session_summary_hub', session_id=session_id, page=page))