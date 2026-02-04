# File: mindstack_app/modules/session/routes/views.py
from flask import render_template, request, redirect, url_for, flash, abort, current_app
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from mindstack_app.models import LearningContainer, LearningItem, db
from ..services.session_service import LearningSessionService
from mindstack_app.modules.learning_history.models import StudyLog
from .. import blueprint
from .api import safe_url_for

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
    if session.learning_mode in ['typing', 'listening', 'mcq', 'quiz']:
        return f"{base_name} • {session.total_items} câu"
    return base_name

@blueprint.route('/')
@login_required
def manage_sessions():
    """Trang quản lý các phiên học đang hoạt động (Thay thế /learn/session cũ)."""
    try:
        sessions = LearningSessionService.get_active_sessions(current_user.user_id)
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
                'total': s.total_items,
                'resume_url': resume_url,
                'start_time': s.start_time,
                'learning_mode': s.learning_mode
            })
        
        history_raw = LearningSessionService.get_session_history(current_user.user_id)
        history_list = []
        for h in history_raw:
            container_name = "Bộ học tập"
            try:
                if isinstance(h.set_id_data, int):
                    container = LearningContainer.query.get(h.set_id_data)
                    if container: container_name = container.title
                elif isinstance(h.set_id_data, list):
                    container_name = f"{len(h.set_id_data)} bộ học tập"
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
                'points': h.points_earned
            })
        
        return render_template('aura_mobile/modules/learning/sessions.html', sessions=session_list, history=history_list)
    except Exception as e:
        current_app.logger.error(f"Error loading sessions page: {e}", exc_info=True)
        return f"Error loading sessions: {e}", 500

@blueprint.route('/<session_id>/summary')
@login_required
def session_summary(session_id):
    """Trang tóm tắt kết quả phiên học (Thay thế /learn/session/<id>/summary cũ)."""
    try:
        session_obj = LearningSessionService.get_session_by_id(session_id)
        if not session_obj or session_obj.user_id != current_user.user_id:
            abort(404)
            
        container_name = "Bộ học tập"
        try:
            if isinstance(session_obj.set_id_data, int):
                container = LearningContainer.query.get(session_obj.set_id_data)
                if container: container_name = container.title
            elif isinstance(session_obj.set_id_data, list) and len(session_obj.set_id_data) > 0:
                container_name = f"{len(session_obj.set_id_data)} bộ học tập"
        except: pass
        
        summary_data = {
            'session_id': session_obj.session_id,
            'mode_name': get_mode_description(session_obj),
            'container_name': container_name,
            'start_time': session_obj.start_time,
            'end_time': session_obj.end_time,
            'correct': session_obj.correct_count,
            'wrong': session_obj.incorrect_count,
            'points': session_obj.points_earned,
            'total': session_obj.total_items or (session_obj.correct_count + session_obj.incorrect_count + session_obj.vague_count)
        }
        
        from mindstack_app.utils.content_renderer import render_text_field
        page = request.args.get('page', 1, type=int)
        
        # Query StudyLog instead of ReviewLog
        pagination = StudyLog.query.filter_by(session_id=session_obj.session_id).order_by(StudyLog.timestamp.desc()).paginate(page=page, per_page=20, error_out=False)
        
        # Prefetch items to avoid N+1 and because StudyLog has no relationship
        item_ids = [log.item_id for log in pagination.items]
        items = LearningItem.query.filter(LearningItem.item_id.in_(item_ids)).all()
        item_map = {i.item_id: i for i in items}

        processed_logs = []
        for log in pagination.items:
            item = item_map.get(log.item_id)
            game = log.gamification_snapshot or {}
            
            score_change = game.get('score_change', 0)
            if score_change == 0:
                 # Fallback if gamification_snapshot is missing or 0
                 if log.rating == 3: score_change = 10
                 elif log.rating == 4: score_change = 15
                 elif log.rating == 2: score_change = 5

            log_data = {
                'timestamp': log.timestamp, 
                'rating': log.rating, 
                'score_change': score_change, 
                'duration_ms': log.review_duration, 
                'item_id': log.item_id, 
                'item_content': f"Item #{log.item_id}"
            }
            if item:
                if item.item_type == 'FLASHCARD': 
                    log_data['item_content'] = render_text_field(item.content.get('front', ''), 'front')
                elif item.item_type == 'QUIZ': 
                    log_data['item_content'] = render_text_field(item.content.get('question', ''), 'question')
            processed_logs.append(log_data)
        
        return render_dynamic_template('modules/learning/session_summary.html',
            summary=summary_data,
            set_id=session_obj.set_id_data if isinstance(session_obj.set_id_data, int) else None,
            pagination=pagination,
            logs=processed_logs
        )
    except Exception as e:
        current_app.logger.error(f"Error loading session summary: {e}", exc_info=True)
         # Fallback error page
        return f"Error: {str(e)}", 500