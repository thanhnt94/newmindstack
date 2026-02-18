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
    """Generate a detailed description for a learning session."""
    mode_map = {
        'new_only': 'Học từ mới',
        'due_only': 'Ôn tập tới hạn',
        'hard_only': 'Các từ khó',
        'mixed_srs': 'Học theo lộ trình (SRS)',
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
        
        # Calculate Accuracy and Duration
        answered_count = session_obj.correct_count + session_obj.incorrect_count + session_obj.vague_count
        total_for_acc = session_obj.correct_count + session_obj.incorrect_count
        accuracy = round((session_obj.correct_count / total_for_acc * 100)) if total_for_acc > 0 else 0
        
        duration_str = "0s"
        if session_obj.start_time and session_obj.end_time:
            diff = session_obj.end_time - session_obj.start_time
            seconds = int(diff.total_seconds())
            if seconds < 60:
                duration_str = f"{seconds}s"
            else:
                duration_str = f"{seconds // 60}m {seconds % 60}s"

        # Map mode labels
        mode_labels = {
            'flashcard': 'Thẻ ghi nhớ',
            'mcq': 'Trắc nghiệm (MCQ)',
            'typing': 'Luyện gõ từ'
        }
        sub_mode_labels = {
            'srs': 'SRS',
            'review': 'Ôn tập',
            'random': 'Ngẫu nhiên',
            'mixed': 'Trộn lẫn',
            'new_cards': 'Thẻ mới',
            'due_cards': 'Thẻ đến hạn',
            'sequential': 'Theo thứ tự'
        }
        
        l_mode = session_obj.learning_mode
        # Ensure session_data is a dict
        s_data = session_obj.session_data or {}
        
        # Try 'mode' (standard) or 'study_mode' (new metadata)
        s_mode = s_data.get('mode') or s_data.get('study_mode')
        
        # Default fallback
        if not s_mode:
            s_mode = 'srs' if l_mode == 'flashcard' else 'review'
        
        summary_data = {
            'id': session_obj.session_id,
            'correct': session_obj.correct_count,
            'wrong': session_obj.incorrect_count,
            'vague': session_obj.vague_count,
            'points': session_obj.points_earned,
            'total': session_obj.total_items or answered_count,
            'answered': answered_count,
            'accuracy': accuracy,
            'duration': duration_str,
            'learning_mode': l_mode,
            'learning_mode_label': mode_labels.get(l_mode, l_mode.capitalize()),
            'sub_mode_label': sub_mode_labels.get(s_mode, s_mode.capitalize()) if s_mode else "Tự do",
            'container_name': s_data.get('container_name', container_name),
            'mode_name': s_data.get('mode_name', 'Tự do')
        }
        
        from mindstack_app.utils.content_renderer import render_text_field
        page = request.args.get('page', 1, type=int)
        
        # Query via Interface - Ensure session_id is int
        try:
            current_sess_id = int(session_obj.session_id)
        except:
            current_sess_id = session_obj.session_id

        from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
        logs_data = LearningHistoryInterface.get_session_logs(session_id=current_sess_id, page=page, per_page=20)
        
        # [RESCUE LOGIC] If no logs found via session_id, try to find orphaned logs for this user/mode/time
        if logs_data.get('total', 0) == 0 and answered_count > 0:
            current_app.logger.warning(f"[SESSION_SUMMARY] No logs found for session {current_sess_id}, attempting rescue...")
            from mindstack_app.models import StudyLog
            # Search for logs by same user, same mode, within 5 minutes of session start
            rescue_query = StudyLog.query.filter(
                StudyLog.user_id == session_obj.user_id,
                StudyLog.session_id.is_(None),
                StudyLog.learning_mode == session_obj.learning_mode,
                StudyLog.timestamp >= session_obj.start_time
            ).order_by(StudyLog.timestamp.desc())
            
            pagination = rescue_query.paginate(page=page, per_page=20, error_out=False)
            logs_items = [
                {
                    'log_id': log.log_id,
                    'item_id': log.item_id,
                    'timestamp': log.timestamp,
                    'rating': log.rating,
                    'is_correct': log.is_correct,
                    'review_duration': log.review_duration,
                    'learning_mode': log.learning_mode,
                    'user_answer': log.user_answer
                }
                for log in pagination.items
            ]
            logs_data = {
                'items': logs_items,
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page
            }

        class PaginationWrapper:
            def __init__(self, data):
                self.items = data['items']
                self.total = data['total']
                self.pages = data['pages']
                self.page = data['current_page']
                self.per_page = 20
                self.has_prev = self.page > 1
                self.has_next = self.page < self.pages
                self.prev_num = self.page - 1
                self.next_num = self.page + 1

            def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
                last = 0
                for num in range(1, self.pages + 1):
                    if num <= left_edge or \
                       (num > self.page - left_current - 1 and num < self.page + right_current) or \
                       num > self.pages - right_edge:
                        if last + 1 != num:
                            yield None
                        yield num
                        last = num
        
        pagination = PaginationWrapper(logs_data)
        
        # Prefetch items
        item_ids = [log['item_id'] for log in pagination.items]
        items = LearningItem.query.filter(LearningItem.item_id.in_(item_ids)).all()
        item_map = {i.item_id: i for i in items}

        processed_logs = []
        for log in pagination.items:
            item = item_map.get(log['item_id'])
            game = log.get('gamification_snapshot') or {}
            
            score_change = game.get('score_change', 0)
            if score_change == 0:
                 # Fallback if gamification_snapshot is missing or 0
                 rating = log.get('rating')
                 if rating == 3: score_change = 10
                 elif rating == 4: score_change = 15
                 elif rating == 2: score_change = 5

            log_data = {
                'log_id': log['log_id'],
                'timestamp': log['timestamp'], 
                'rating': log['rating'], 
                'is_correct': log.get('is_correct', True),
                'score_change': score_change, 
                'duration_ms': log['review_duration'], 
                'item_id': log['item_id'], 
                'front': f"Item #{log['item_id']}",
                'back': None
            }
            if item:
                if item.item_type == 'FLASHCARD': 
                    log_data['front'] = render_text_field(item.content.get('front', ''), 'front')
                    log_data['back'] = render_text_field(item.content.get('back', ''), 'back')
                elif item.item_type in ['QUIZ', 'MCQ']: 
                    log_data['front'] = render_text_field(item.content.get('question', ''), 'question')
                    # Find correct option for back
                    correct_opt = item.content.get('correct_option')
                    options = item.content.get('options', {})
                    if correct_opt and options:
                        log_data['back'] = options.get(correct_opt)
                elif item.item_type == 'TYPING':
                    log_data['front'] = render_text_field(item.content.get('question', ''), 'question')
                    log_data['back'] = item.content.get('correct_answer')
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