# mindstack_app/modules/session_hub/services/hub_service.py
"""
Session Hub Service
===================
Aggregates session summary data from SessionInterface and LearningHistoryInterface.
"""
from flask import current_app
from mindstack_app.modules.session.interface import SessionInterface
from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
from mindstack_app.models import LearningContainer, LearningItem


class SessionHubService:
    """Service to aggregate data for Session Hub views."""

    # Mode display labels
    MODE_LABELS = {
        'flashcard': 'Thẻ ghi nhớ',
        'mcq': 'Trắc nghiệm (MCQ)',
        'typing': 'Luyện gõ từ',
        'listening': 'Luyện nghe',
        'matching': 'Ghép thẻ',
        'speed': 'Ôn nhanh',
        'quiz': 'Quiz'
    }

    SUB_MODE_LABELS = {
        'srs': 'SRS',
        'review': 'Ôn tập',
        'random': 'Ngẫu nhiên',
        'mixed': 'Trộn lẫn',
        'new_cards': 'Thẻ mới',
        'due_cards': 'Thẻ đến hạn',
        'sequential': 'Theo thứ tự'
    }

    @staticmethod
    def get_summary_data(user_id, session_id, page=1, per_page=20):
        """
        Aggregate all data needed to render a session summary page.
        
        Returns:
            dict with keys: summary, logs, pagination, set_id
            or None if session not found / unauthorized
        """
        # 1. Get session object via Interface
        session_obj = SessionInterface.get_session_by_id(session_id)
        if not session_obj or session_obj.user_id != user_id:
            return None

        # 2. Resolve container name
        container_name = "Bộ học tập"
        try:
            if isinstance(session_obj.set_id_data, int):
                container = LearningContainer.query.get(session_obj.set_id_data)
                if container:
                    container_name = container.title
            elif isinstance(session_obj.set_id_data, list) and len(session_obj.set_id_data) > 0:
                container_name = f"{len(session_obj.set_id_data)} bộ học tập"
        except Exception:
            pass

        # 3. Calculate accuracy and duration
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

        # 4. Resolve mode labels
        l_mode = session_obj.learning_mode
        s_data = session_obj.session_data or {}
        s_mode = s_data.get('mode') or s_data.get('study_mode')
        if not s_mode:
            s_mode = 'srs' if l_mode == 'flashcard' else 'review'

        summary = {
            'id': session_obj.session_id,
            'session_id': session_obj.session_id,
            'correct': session_obj.correct_count,
            'wrong': session_obj.incorrect_count,
            'vague': session_obj.vague_count,
            'points': session_obj.points_earned,
            'total': session_obj.total_items or answered_count,
            'answered': answered_count,
            'accuracy': accuracy,
            'duration': duration_str,
            'learning_mode': l_mode,
            'learning_mode_label': SessionHubService.MODE_LABELS.get(l_mode, l_mode.capitalize()),
            'sub_mode_label': SessionHubService.SUB_MODE_LABELS.get(s_mode, s_mode.capitalize()) if s_mode else "Tự do",
            'container_name': s_data.get('container_name', container_name),
            'mode_name': s_data.get('mode_name', 'Tự do')
        }

        # 5. Query logs via LearningHistoryInterface
        try:
            current_sess_id = int(session_obj.session_id)
        except (ValueError, TypeError):
            current_sess_id = session_obj.session_id

        logs_data = LearningHistoryInterface.get_session_logs(
            session_id=current_sess_id, page=page, per_page=per_page
        )

        # [RESCUE LOGIC] If no logs found, try orphaned logs
        if logs_data.get('total', 0) == 0 and answered_count > 0:
            current_app.logger.warning(
                f"[SESSION_HUB] No logs found for session {current_sess_id}, attempting rescue..."
            )
            logs_data = SessionHubService._rescue_orphaned_logs(session_obj, page, per_page)

        # 6. Process logs with item content
        processed_logs = SessionHubService._process_logs(logs_data, summary['learning_mode'])

        # 7. Build pagination info
        pagination = {
            'items': processed_logs,
            'total': logs_data.get('total', 0),
            'pages': logs_data.get('pages', 0),
            'page': logs_data.get('current_page', page),
            'per_page': per_page,
            'has_prev': page > 1,
            'has_next': page < logs_data.get('pages', 0),
            'prev_num': page - 1,
            'next_num': page + 1
        }

        set_id = session_obj.set_id_data if isinstance(session_obj.set_id_data, int) else None

        return {
            'summary': summary,
            'logs': processed_logs,
            'pagination': pagination,
            'set_id': set_id
        }

    @staticmethod
    def _rescue_orphaned_logs(session_obj, page, per_page):
        """Find orphaned logs that belong to this session but lack session_id."""
        from mindstack_app.models import StudyLog
        
        rescue_query = StudyLog.query.filter(
            StudyLog.user_id == session_obj.user_id,
            StudyLog.session_id.is_(None),
            StudyLog.learning_mode == session_obj.learning_mode,
            StudyLog.timestamp >= session_obj.start_time
        ).order_by(StudyLog.timestamp.desc())

        pagination = rescue_query.paginate(page=page, per_page=per_page, error_out=False)
        items = [
            {
                'log_id': log.log_id,
                'item_id': log.item_id,
                'timestamp': log.timestamp,
                'rating': log.rating,
                'is_correct': log.is_correct,
                'review_duration': log.review_duration,
                'learning_mode': log.learning_mode,
                'user_answer': log.user_answer,
                'gamification_snapshot': log.gamification_snapshot,
                'fsrs_snapshot': log.fsrs_snapshot,
                'context_snapshot': log.context_snapshot
            }
            for log in pagination.items
        ]
        return {
            'items': items,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }

    @staticmethod
    def _process_logs(logs_data, learning_mode):
        """Enrich log entries with item content and score info."""
        from mindstack_app.utils.content_renderer import render_text_field
        
        raw_logs = logs_data.get('items', [])
        
        # Prefetch items
        item_ids = [log['item_id'] for log in raw_logs]
        items = LearningItem.query.filter(LearningItem.item_id.in_(item_ids)).all()
        item_map = {i.item_id: i for i in items}

        processed = []
        for log in raw_logs:
            item = item_map.get(log['item_id'])
            game = log.get('gamification_snapshot') or {}

            score_change = game.get('score_change', 0)
            if score_change == 0:
                rating = log.get('rating')
                if rating == 3: score_change = 10
                elif rating == 4: score_change = 15
                elif rating == 2: score_change = 5

            log_entry = {
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
                    log_entry['front'] = render_text_field(item.content.get('front', ''), 'front')
                    log_entry['back'] = render_text_field(item.content.get('back', ''), 'back')
                elif item.item_type in ['QUIZ', 'MCQ']:
                    log_entry['front'] = render_text_field(item.content.get('question', ''), 'question')
                    correct_opt = item.content.get('correct_option')
                    options = item.content.get('options', {})
                    if correct_opt and options:
                        log_entry['back'] = options.get(correct_opt)
                elif item.item_type == 'TYPING':
                    log_entry['front'] = render_text_field(item.content.get('question', ''), 'question')
                    log_entry['back'] = item.content.get('correct_answer')

            processed.append(log_entry)

        return processed
