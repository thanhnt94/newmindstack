# File: mindstack_app/modules/stats/services/vocabulary_stats_service.py
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, or_, desc
from flask import current_app, url_for
from collections import defaultdict
from mindstack_app.models import (
    db, LearningItem, User, ContainerContributor, LearningContainer, 
    UserItemMarker, ScoreLog
)
# REFAC: ItemMemoryState removed
from mindstack_app.modules.learning_history.models import StudyLog
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsService
# REFAC: HardItemService removed (Delegated to FsrsInterface)
from mindstack_app.utils.content_renderer import render_text_field

class VocabularyStatsService:
    """Service for calculating vocabulary-related statistics."""

    @staticmethod
    def get_container_leaderboard(container_id: int, limit: int = 20, timeframe: str = 'all') -> list:
        item_ids_query = db.session.query(LearningItem.item_id).filter(
            LearningItem.container_id == container_id
        ).subquery()
        start_date = VocabularyStatsService._get_start_date(timeframe)
        query = db.session.query(
            User.user_id, User.username, User.avatar_url,
            func.sum(ScoreLog.score_change).label('total_score'),
            func.count(ScoreLog.log_id).label('review_count')
        ).join(ScoreLog, User.user_id == ScoreLog.user_id).filter(ScoreLog.item_id.in_(item_ids_query))
        if start_date: query = query.filter(ScoreLog.timestamp >= start_date)
        score_results = query.group_by(User.user_id, User.username, User.avatar_url).order_by(desc('total_score')).limit(limit).all()
        user_ids = [r.user_id for r in score_results]
        mastered_map = {}
        if user_ids:
            # REFAC: Use FsrsInterface for mastery stats
            mastered_map = FsrsService.get_leaderboard_mastery(user_ids, item_ids_query)

        leaderboard = []
        for idx, row in enumerate(score_results, start=1):
            avatar_url = None
            if row.avatar_url:
                if row.avatar_url.startswith(('http://', 'https://')): avatar_url = row.avatar_url
                else:
                    try: avatar_url = url_for('media_uploads', filename=row.avatar_url)
                    except: pass
            leaderboard.append({
                'rank': idx, 'user_id': row.user_id, 'username': row.username, 'avatar_url': avatar_url,
                'total_score': int(row.total_score or 0), 'review_count': int(row.review_count or 0), 'mastered_count': mastered_map.get(row.user_id, 0)
            })
        return leaderboard

    @staticmethod
    def get_global_stats(user_id: int) -> dict:
        total_sets = LearningContainer.query.filter(LearningContainer.creator_user_id == user_id, LearningContainer.container_type == 'FLASHCARD_SET').count()
        # REFAC: Use FsrsInterface for global FSRS stats
        fsrs_stats = FsrsService.get_global_stats(user_id)
        
        return {
            'total_sets': total_sets, 
            'total_cards': fsrs_stats.get('total_cards', 0), 
            'mastered': fsrs_stats.get('mastered_count', 0), 
            'due': fsrs_stats.get('due_count', 0)
        }

    @staticmethod
    def get_full_stats(user_id: int, container_id: int) -> dict:
        items = LearningItem.query.filter(LearningItem.container_id == container_id, LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])).all()
        item_ids = [item.item_id for item in items]
        total = len(item_ids)
        if not item_ids: return VocabularyStatsService._empty_stats()
        
        # REFAC: Use FsrsInterface
        progress_map = FsrsService.get_memory_states(user_id, item_ids)
        
        now = datetime.now(timezone.utc)
        new_count = learning_count = mastered_count = due_count = 0
        total_retrievability = total_correct = total_incorrect = total_reviews = 0
        last_reviewed = None
        for item_id in item_ids:
            p = progress_map.get(item_id)
            if not p: new_count += 1
            else:
                stability = p.stability or 0.0
                retrievability = FsrsService.get_retrievability(p)
                total_retrievability += retrievability
                if stability >= 21.0: mastered_count += 1
                else: learning_count += 1
                
                due_date = p.due_date
                if due_date and (due_date.replace(tzinfo=timezone.utc) if due_date.tzinfo is None else due_date) <= now:
                    due_count += 1
                    
                total_correct += p.times_correct or 0
                total_incorrect += p.times_incorrect or 0
                total_reviews += (p.times_correct or 0) + (p.times_incorrect or 0)
                if p.last_review:
                    if not last_reviewed or p.last_review > last_reviewed: last_reviewed = p.last_review
        learned_count = len(progress_map)
        
        # REFAC: Use FsrsService.get_hard_count
        hard_count = FsrsService.get_hard_count(user_id, container_id)
        
        return {
            'total': total, 'new': new_count, 'learning': learning_count, 'mastered': mastered_count, 'due': due_count,
            'hard': hard_count, 'learned': learned_count,
            'completion_pct': round((learned_count / total * 100), 1) if total > 0 else 0,
            'retrievability_avg': round((total_retrievability / learned_count), 2) if learned_count > 0 else 0,
            'mastery_avg': round((total_retrievability / learned_count), 2) if learned_count > 0 else 0,
            'accuracy_pct': round((total_correct / (total_correct + total_incorrect) * 100), 1) if (total_correct + total_incorrect) > 0 else 0,
            'total_reviews': total_reviews, 'total_correct': total_correct, 'total_incorrect': total_incorrect,
            'last_reviewed': last_reviewed.isoformat() if last_reviewed else None
        }

    @staticmethod
    def _empty_stats() -> dict:
        return {'total': 0, 'new': 0, 'learning': 0, 'mastered': 0, 'due': 0, 'hard': 0, 'learned': 0, 'completion_pct': 0, 'retrievability_avg': 0, 'mastery_avg': 0, 'accuracy_pct': 0, 'total_reviews': 0, 'total_correct': 0, 'total_incorrect': 0, 'last_reviewed': None}

    @staticmethod
    def get_chart_data(user_id: int, container_id: int) -> dict:
        items = LearningItem.query.filter(LearningItem.container_id == container_id, LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])).all()
        item_ids = [item.item_id for item in items]
        if not item_ids: return {'distribution': {'weak': 0, 'medium': 0, 'strong': 0}, 'timeline': {'dates': [], 'values': []}}
        
        # REFAC: Use FsrsInterface
        progress_map = FsrsService.get_memory_states(user_id, item_ids)
        
        weak = medium = strong = 0
        for p in progress_map.values():
            r = FsrsService.get_retrievability(p)
            if r < 0.7: weak += 1
            elif r < 0.9: medium += 1
            else: strong += 1
        
        # Timeline
        now = datetime.now(timezone.utc)
        timeline_data = defaultdict(list)
        start_date = now - timedelta(days=30)
        
        logs = StudyLog.query.filter(
            StudyLog.user_id == user_id, 
            StudyLog.item_id.in_(item_ids), 
            StudyLog.timestamp >= start_date
        ).order_by(StudyLog.timestamp).all()
        
        for log in logs:
            fsrs = log.fsrs_snapshot or {}
            stability = fsrs.get('stability')
            if stability is not None:
                date_key = log.timestamp.strftime('%d/%m')
                timeline_data[date_key].append(min((stability)/21.0, 1.0) * 100)
        
        dates, values = [], []
        for i in range(29, -1, -1):
            date = now - timedelta(days=i)
            date_key = date.strftime('%d/%m')
            dates.append(date_key)
            if date_key in timeline_data: values.append(round(sum(timeline_data[date_key]) / len(timeline_data[date_key]), 1))
            else: values.append(None)
        return {'distribution': {'weak': weak, 'medium': medium, 'strong': strong}, 'timeline': {'dates': dates, 'values': values}}

    @staticmethod
    def get_item_stats(user_id: int, item_id: int) -> dict:
        item = LearningItem.query.get(item_id)
        if not item: return None
        content = item.content or {}
        
        # REFAC: Use FsrsInterface
        progress = FsrsService.get_item_state(user_id, item_id)
        
        logs = StudyLog.query.filter_by(user_id=user_id, item_id=item_id).order_by(StudyLog.timestamp.desc()).all()
        
        total_attempts = len(logs)
        total_correct = sum(1 for log in logs if VocabularyStatsService._is_log_correct(log))
        total_duration_ms = sum(log.review_duration for log in logs if log.review_duration)
        
        total_score = 0
        for log in logs:
            game = log.gamification_snapshot or {}
            total_score += game.get('score_change', 0)
        
        mode_counts = {}
        for log in logs:
            mode = log.learning_mode or 'unknown'
            if mode not in mode_counts: mode_counts[mode] = {'count': 0, 'correct': 0, 'duration': 0, 'score': 0}
            mode_counts[mode]['count'] += 1
            if log.review_duration: mode_counts[mode]['duration'] += log.review_duration
            if VocabularyStatsService._is_log_correct(log): mode_counts[mode]['correct'] += 1
            
            game = log.gamification_snapshot or {}
            score = game.get('score_change', 0)
            if score: mode_counts[mode]['score'] += score

        for mode_data in mode_counts.values():
            mode_data['accuracy'] = round((mode_data['correct'] / mode_data['count'] * 100), 1) if mode_data['count'] > 0 else 0
            mode_data['avg_duration'] = round(mode_data['duration'] / mode_data['count'], 0) if mode_data['count'] > 0 else 0

        stability = progress.stability if progress else 0.0
        difficulty = progress.difficulty if progress else 0.0
        retrievability = FsrsService.get_retrievability(progress) if progress else 0.0
        streak = progress.streak if progress else 0
        next_due = progress.due_date if progress else None
        
        accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
        avg_duration = (total_duration_ms / total_attempts) if total_attempts > 0 else 0
        avg_score = (total_score / total_attempts) if total_attempts > 0 else 0
        
        first_reviewed = logs[-1].timestamp if logs else None
        last_reviewed_log = logs[0].timestamp if logs else None
        
        status = 'new'
        if progress:
            now = datetime.now(timezone.utc)
            if stability >= 21.0: status = 'mastered'
            elif progress.due_date and (progress.due_date.replace(tzinfo=timezone.utc) if progress.due_date.tzinfo is None else progress.due_date) <= now: status = 'due'
            else:
                 # Check logic for 'hard' without HardItemService
                 is_hard = (progress.difficulty or 0) >= 7.0
                 if is_hard: status = 'hard'
                 else: status = 'learning'
                
        can_edit = False
        user_obj = User.query.get(user_id)
        if user_obj:
            if user_obj.user_role == User.ROLE_ADMIN: can_edit = True
            elif item.container and item.container.creator_user_id == user_id: can_edit = True
            else:
                contributor = ContainerContributor.query.filter_by(container_id=item.container_id, user_id=user_id, permission_level='editor').first()
                if contributor: can_edit = True
        
        edit_url = ""
        if can_edit:
            edit_url = url_for('content_management.edit_flashcard_item', set_id=item.container_id, item_id=item_id, is_modal='true')

        markers = UserItemMarker.query.filter_by(user_id=user_id, item_id=item_id).all()
        marker_list = [m.marker_type for m in markers]

        durations = [log.review_duration for log in logs if log.review_duration]
        min_duration = min(durations) if durations else 0

        return {
            'markers': marker_list,
            'item': {
                'id': item.item_id, 'container_title': item.container.title if item.container else 'Unknown Set', 'container_id': item.container_id,
                'front': render_text_field(content.get('front', '?')), 'back': render_text_field(content.get('back', '?')),
                'pronunciation': content.get('pronunciation'), 'meaning': render_text_field(content.get('meaning')),
                'image': content.get('image'), 'audio': content.get('audio'), 'example': render_text_field(content.get('example')),
                'example_meaning': render_text_field(content.get('example_meaning')), 'phonetic': content.get('phonetic'),
                'tags': content.get('tags', []), 'custom_data': content.get('custom_data') or content.get('custom_content', {}),
                'ai_explanation': render_text_field(item.ai_explanation),
                'note': (progress.data or {}).get('note', '') if progress else '',
                'full_content': content
            },
            'progress': {
                'status': status, 'retrievability': round(retrievability * 100, 1), 'streak': streak, 'ease_factor': round(difficulty, 2),
                'due_relative': VocabularyStatsService._get_relative_time_string(next_due) if next_due else 'Sẵn sàng',
                'stability_trend': 0, 'mastery_trend': 0, 'first_reviewed': first_reviewed, 'last_reviewed_log': last_reviewed_log,
                'last_reviewed_relative': VocabularyStatsService._get_relative_time_string(last_reviewed_log) if last_reviewed_log else 'Chưa học'
            },
            'modes': mode_counts,
            'performance': {
                'total_reviews': total_attempts, 'accuracy': round(accuracy, 1), 'total_time_ms': total_duration_ms,
                'avg_time_ms': round(avg_duration, 0), 'min_time_ms': min_duration, 'total_score': total_score, 'avg_score': round(avg_score, 1)
            },
            'history': [
                {
                    'timestamp': log.timestamp, 'mode': log.learning_mode, 'result': 'Correct' if VocabularyStatsService._is_log_correct(log) else 'Incorrect',
                    'duration_ms': log.review_duration, 'user_answer': log.user_answer, 
                    'score_change': (log.gamification_snapshot or {}).get('score_change', 0), 
                    'rating': log.rating
                }
                for log in logs[:50]
            ],
            'permissions': {'can_edit': can_edit, 'edit_url': edit_url}
        }

    @staticmethod
    def get_course_overview_stats(user_id: int, container_id: int, page: int = 1, per_page: int = 12, sort_by: str = 'default') -> dict:
        base_query = LearningItem.query.filter(
            LearningItem.container_id == container_id,
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        )
        if sort_by == 'due_date':
            # REFAC: Use FsrsInterface.apply_ordering
            base_query = FsrsService.apply_ordering(base_query, user_id, 'due_date')
        elif sort_by == 'mastery':
            # REFAC: Use FsrsInterface.apply_ordering
            base_query = FsrsService.apply_ordering(base_query, user_id, 'mastery')
        else:
            base_query = base_query.order_by(LearningItem.order_in_container.asc(), LearningItem.item_id.asc())

        total_items = base_query.count()
        pagination = base_query.paginate(page=page, per_page=per_page, error_out=False)
        if not pagination.items: return {'items': [], 'pagination': {'total': total_items, 'page': page, 'per_page': per_page, 'pages': pagination.pages}, 'learned_count': 0}
        
        item_ids = [item.item_id for item in pagination.items]
        # REFAC: Use FsrsInterface
        progress_map = FsrsService.get_memory_states(user_id, item_ids)
        
        now = datetime.now(timezone.utc)
        result_items = []
        for item in pagination.items:
            progress = progress_map.get(item.item_id)
            content = item.content or {}
            raw_term = content.get('front', '') or content.get('term', '') or content.get('recto', '') or ''
            raw_definition = content.get('back', '') or content.get('definition', '') or content.get('verso', '') or ''
            term = render_text_field(raw_term)
            definition = render_text_field(raw_definition)
            if progress:
                retrievability = FsrsService.get_retrievability(progress)
                mastery = int(retrievability * 100)
                stability = progress.stability or 0.0
                state = progress.state
                if state == 0: status = 'new'
                elif state in [1, 3]: status = 'learning'
                elif stability >= 21.0: status = 'mastered'
                else: status = 'reviewing'
                
                due_date_raw = progress.due_date
                is_due = False
                if due_date_raw:
                    is_due = (due_date_raw.replace(tzinfo=timezone.utc) if due_date_raw.tzinfo is None else due_date_raw) <= now
                
                memory_level = (progress.data or {}).get('memory_level', 0) if progress.data else 0
                difficulty = progress.difficulty or 0.0
                repetitions = progress.repetitions or 0
                has_note = bool((progress.data or {}).get('note'))
                
                if progress.due_date:
                    due_date = progress.due_date.replace(tzinfo=timezone.utc) if progress.due_date.tzinfo is None else progress.due_date
                    diff = due_date - now
                    if diff.total_seconds() <= 0: next_review = "Ngay bây giờ"
                    elif diff.days > 365: next_review = f"{diff.days // 365} năm"
                    elif diff.days > 30: next_review = f"{diff.days // 30} tháng"
                    elif diff.days > 0: next_review = f"{diff.days} ngày"
                    elif diff.seconds > 3600: next_review = f"{diff.seconds // 3600} giờ"
                    else: next_review = f"{diff.seconds // 60} phút"
                else: next_review = "-"
                state_labels = {0: 'Mới (New)', 1: 'Đang học (Learning)', 2: 'Ôn tập (Review)', 3: 'Học lại (Relearning)'}
                state_label = state_labels.get(state, 'Unknown')
            else:
                mastery = retrievability = 0
                status = 'new'
                is_due = False
                memory_level = 0
                difficulty = stability = repetitions = 0
                has_note = False
                next_review = "-"
                state_label = "Mới (New)"
            
            has_ai = bool(item.ai_explanation and item.ai_explanation.strip())
            is_hard = False
            if progress: 
                # Check hard status locally or use service?
                # User asked to replace HardItemService.
                # Here we can just check properties.
                is_hard = (progress.difficulty or 0) >= 7.0

            result_items.append({
                'item_id': item.item_id, 'term': term, 'definition': definition, 'mastery': mastery, 'retrievability': retrievability, 
                'status': status, 'is_due': is_due, 'memory_level': memory_level, 'fsrs_stability': stability, 'fsrs_difficulty': difficulty, 
                'repetitions': repetitions, 'has_ai': has_ai, 'has_note': has_note, 'is_hard': is_hard, 'next_review': next_review, 'state_label': state_label
            })
        
        # REFAC: Use FsrsInterface
        container_stats = FsrsService.get_container_stats(user_id, container_id)
        learned_count = container_stats.get('learned', 0)
        
        return {'items': result_items, 'pagination': {'total': total_items, 'page': page, 'per_page': per_page, 'pages': pagination.pages}, 'learned_count': learned_count}

    @staticmethod
    def _is_log_correct(log) -> bool:
        if log.is_correct is not None: return log.is_correct
        if log.rating is not None: return log.rating >= 2
        return False

    @staticmethod
    def _get_start_date(timeframe: str) -> datetime | None:
        now = datetime.now(timezone.utc)
        if timeframe == 'day': return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == 'week': return (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == 'month': return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return None

    @staticmethod
    def _get_relative_time_string(dt: datetime) -> str:
        if not dt: return "N/A"
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = dt - now
        total_seconds = diff.total_seconds()
        is_past = total_seconds < 0
        seconds = abs(int(total_seconds))
        minutes = seconds // 60
        hours = minutes // 60
        days = hours // 24
        prefix = "Quá hạn" if is_past else "Trong"
        if days > 0: return f"{prefix} {days} ngày"
        elif hours > 0: return f"{prefix} {hours} giờ"
        elif minutes > 0: return f"{prefix} {minutes} phút"
        else: return "Ngay bây giờ"
