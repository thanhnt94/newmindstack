# File: mindstack_app/modules/stats/services/vocabulary_stats_service.py
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, or_, desc
from flask import current_app, url_for
from collections import defaultdict
from mindstack_app.models import (
    db, LearningItem, ReviewLog, User, ContainerContributor, LearningContainer, 
    UserItemMarker, LearningProgress, ScoreLog
)
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsService
from mindstack_app.modules.fsrs.services.hard_item_service import FSRSHardItemService as HardItemService
from mindstack_app.utils.content_renderer import render_text_field

class VocabularyStatsService:
    """Service for calculating vocabulary-related statistics."""

    @staticmethod
    def get_container_leaderboard(container_id: int, limit: int = 20, timeframe: str = 'all') -> list:
        """
        Lấy bảng xếp hạng người dùng cho một bộ từ vựng cụ thể.
        Xếp hạng dựa trên ĐIỂM SỐ (từ ScoreLog) và số từ đã thuộc.
        Hỗ trợ filter theo timeframe: 'day', 'week', 'month', 'all'.
        """

        # 1. Lấy danh sách item_id trong container để filter ScoreLog
        item_ids_query = db.session.query(LearningItem.item_id).filter(
            LearningItem.container_id == container_id
        ).subquery()

        # 2. Xử lý timeframe
        start_date = VocabularyStatsService._get_start_date(timeframe)
        
        # 3. Query ScoreLog để tính điểm
        # ScoreLog: user_id, item_id, score_change, timestamp
        query = db.session.query(
            User.user_id,
            User.username,
            User.avatar_url,
            func.sum(ScoreLog.score_change).label('total_score'),
            func.count(ScoreLog.log_id).label('review_count')
        ).join(
            ScoreLog, User.user_id == ScoreLog.user_id
        ).filter(
            ScoreLog.item_id.in_(item_ids_query)
        )

        if start_date:
            # Ensure robustness by converting both to naive if needed, but since we return naive from helper now:
            query = query.filter(ScoreLog.timestamp >= start_date)

        score_results = (
            query
            .group_by(User.user_id, User.username, User.avatar_url)
            .order_by(desc('total_score'))
            .limit(limit)
            .all()
        )

        # 4. Lấy thêm thông tin Mastered Count (có thể không cần filter theo time cho cái này, 
        # nhưng để nhất quán thì ta hiển thị mastered hiện tại của user cho set này)
        # Để đơn giản và hiệu năng, ta query riêng hoặc subquery. 
        # Ở đây ta sẽ lấy mastered count HIỆN TẠI (trạng thái snapshot) của user đối với set này.
        user_ids = [r.user_id for r in score_results]
        mastered_map = {}
        if user_ids:
            mastered_data = db.session.query(
                LearningProgress.user_id,
                func.count(LearningProgress.item_id)
            ).filter(
                 LearningProgress.item_id.in_(item_ids_query),
                 LearningProgress.user_id.in_(user_ids),
                 LearningProgress.fsrs_stability >= 21.0
            ).group_by(LearningProgress.user_id).all()
            mastered_map = {uid: count for uid, count in mastered_data}

        leaderboard = []
        for idx, row in enumerate(score_results, start=1):
            # Logic Avatar
            avatar_url = None
            if row.avatar_url:
                if row.avatar_url.startswith(('http://', 'https://')):
                    avatar_url = row.avatar_url
                else:
                    try:
                        avatar_url = url_for('media_uploads', filename=row.avatar_url)
                    except: pass
            
            leaderboard.append({
                'rank': idx,
                'user_id': row.user_id,
                'username': row.username,
                'avatar_url': avatar_url,
                'total_score': int(row.total_score or 0),
                'review_count': int(row.review_count or 0),
                'mastered_count': mastered_map.get(row.user_id, 0)
            })
            
        return leaderboard

    @staticmethod
    def get_global_stats(user_id: int) -> dict:
        total_sets = LearningContainer.query.filter(
            LearningContainer.creator_user_id == user_id,
            LearningContainer.container_type == 'FLASHCARD_SET'
        ).count()
        total_cards = LearningItem.query.join(
            LearningContainer, LearningItem.container_id == LearningContainer.container_id
        ).filter(
            LearningContainer.creator_user_id == user_id,
            LearningContainer.container_type == 'FLASHCARD_SET',
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        ).count()
        now = datetime.now(timezone.utc)
        mastered = LearningProgress.query.filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD,
            LearningProgress.fsrs_stability >= 21.0
        ).count()
        due = LearningProgress.query.filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD,
            LearningProgress.fsrs_due <= now
        ).count()
        return {'total_sets': total_sets, 'total_cards': total_cards, 'mastered': mastered, 'due': due}

    @staticmethod
    def get_full_stats(user_id: int, container_id: int) -> dict:
        items = LearningItem.query.filter(
            LearningItem.container_id == container_id,
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        ).all()
        item_ids = [item.item_id for item in items]
        total = len(item_ids)
        if not item_ids: return VocabularyStatsService._empty_stats()
        
        progress_records = LearningProgress.query.filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD,
            LearningProgress.item_id.in_(item_ids)
        ).all()
        progress_map = {p.item_id: p for p in progress_records}
        now = datetime.now(timezone.utc)
        new_count = learning_count = mastered_count = due_count = 0
        total_retrievability = total_correct = total_incorrect = total_reviews = 0
        last_reviewed = None
        
        for item_id in item_ids:
            p = progress_map.get(item_id)
            if not p: new_count += 1
            else:
                stability = p.fsrs_stability or 0.0
                retrievability = FsrsService.get_retrievability(p)
                total_retrievability += retrievability
                if stability >= 21.0: mastered_count += 1
                else: learning_count += 1
                if p.fsrs_due and p.fsrs_due.replace(tzinfo=timezone.utc) <= now: due_count += 1
                total_correct += p.times_correct or 0
                total_incorrect += p.times_incorrect or 0
                total_reviews += (p.times_correct or 0) + (p.times_incorrect or 0)
                if p.fsrs_last_review:
                    if not last_reviewed or p.fsrs_last_review > last_reviewed: last_reviewed = p.fsrs_last_review
        
        learned_count = len(progress_records)
        return {
            'total': total, 'new': new_count, 'learning': learning_count, 'mastered': mastered_count, 'due': due_count,
            'hard': HardItemService.get_hard_count(user_id, container_id), 'learned': learned_count,
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
        
        progress_records = LearningProgress.query.filter(LearningProgress.user_id == user_id, LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD, LearningProgress.item_id.in_(item_ids)).all()
        weak = medium = strong = 0
        for p in progress_records:
            r = FsrsService.get_retrievability(p)
            if r < 0.7: weak += 1
            elif r < 0.9: medium += 1
            else: strong += 1
        
        now = datetime.now(timezone.utc)
        timeline_data = defaultdict(list)
        start_date = now - timedelta(days=30)
        logs = ReviewLog.query.filter(ReviewLog.user_id == user_id, ReviewLog.item_id.in_(item_ids), ReviewLog.timestamp >= start_date, ReviewLog.fsrs_stability.isnot(None)).order_by(ReviewLog.timestamp).all()
        for log in logs:
            date_key = log.timestamp.strftime('%d/%m')
            timeline_data[date_key].append(min((log.fsrs_stability or 0)/21.0, 1.0) * 100)
        
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
        progress = LearningProgress.query.filter_by(user_id=user_id, item_id=item_id, learning_mode=LearningProgress.MODE_FLASHCARD).first()
        logs = ReviewLog.query.filter_by(user_id=user_id, item_id=item_id).order_by(ReviewLog.timestamp.desc()).all()
        
        total_attempts = len(logs)
        total_correct = sum(1 for log in logs if VocabularyStatsService._is_log_correct(log))
        total_duration_ms = sum(log.review_duration for log in logs if log.review_duration)
        total_score = sum(log.score_change for log in logs if log.score_change is not None)
        
        mode_counts = {}
        for log in logs:
            mode = log.review_type or 'unknown'
            if mode not in mode_counts: mode_counts[mode] = {'count': 0, 'correct': 0, 'duration': 0, 'score': 0}
            mode_counts[mode]['count'] += 1
            if log.review_duration: mode_counts[mode]['duration'] += log.review_duration
            if VocabularyStatsService._is_log_correct(log): mode_counts[mode]['correct'] += 1
            if log.score_change: mode_counts[mode]['score'] += log.score_change

        for mode_data in mode_counts.values():
            mode_data['accuracy'] = round((mode_data['correct'] / mode_data['count'] * 100), 1) if mode_data['count'] > 0 else 0
            mode_data['avg_duration'] = round(mode_data['duration'] / mode_data['count'], 0) if mode_data['count'] > 0 else 0

        stability = progress.fsrs_stability if progress else 0.0
        difficulty = progress.fsrs_difficulty if progress else 0.0
        retrievability = FsrsService.get_retrievability(progress) if progress else 0.0
        streak = progress.correct_streak if progress else 0
        next_due = progress.fsrs_due if progress else None
        
        accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
        avg_duration = (total_duration_ms / total_attempts) if total_attempts > 0 else 0
        avg_score = (total_score / total_attempts) if total_attempts > 0 else 0
        
        first_reviewed = logs[-1].timestamp if logs else None
        last_reviewed_log = logs[0].timestamp if logs else None
        
        status = 'new'
        if progress:
            now = datetime.now(timezone.utc)
            if stability >= 21.0: status = 'mastered'
            elif progress.fsrs_due and progress.fsrs_due.replace(tzinfo=timezone.utc) <= now: status = 'due'
            elif HardItemService.is_hard_item(user_id, item_id): status = 'hard'
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
                'note': (progress.mode_data or {}).get('note', '') if progress else '',
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
                    'timestamp': log.timestamp, 'mode': log.review_type, 'result': 'Correct' if VocabularyStatsService._is_log_correct(log) else 'Incorrect',
                    'duration_ms': log.review_duration, 'user_answer': log.user_answer, 'score_change': log.score_change, 'rating': log.rating
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
        
        # [NEW] Sorting Logic
        if sort_by == 'due_date':
            # Sort by Next Review (Due Date)
            # Need to join with LearningProgress (outer join to include unlearned items)
            base_query = base_query.outerjoin(
                LearningProgress, 
                (LearningItem.item_id == LearningProgress.item_id) & 
                (LearningProgress.user_id == user_id) &
                (LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD)
            ).order_by(
                # Items with due date (past first) -> Future -> None (New items last)
                # SQLite/Postgres nulls handling varies, usually nulls last/first.
                # We want Due (Past) < Due (Future) < Null (New)
                # asc() puts Null last typically or first? Default is Null First often.
                # Let's use nulls_last if supported or case statement.
                # Simpler: order by fsrs_due asc.
                LearningProgress.fsrs_due.asc().nulls_last(),
                LearningItem.order_in_container.asc()
            )
        elif sort_by == 'mastery':
            # Sort by Mastery (Retrievability) - High to Low or Low to High?
            # Usually "Weakest first" is better for learning.
            base_query = base_query.outerjoin(
                LearningProgress, 
                (LearningItem.item_id == LearningProgress.item_id) & 
                (LearningProgress.user_id == user_id) &
                (LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD)
            ).order_by(
                # We want Low Retrievability first. (Ascending)
                # Nulls (New) count as 0 retrievability? Or separate?
                # Let's treat New as failure? No.
                # Standard: Weakest -> Strongest -> New
                # Or New -> Weakest -> Strongest?
                # User request was "soft theo thoi gian toi han".
                # Let's stick to just 'due_date' and 'default' for now as requested.
                LearningItem.order_in_container.asc()
            )
        else:
            # Default: Order by custom order or ID
            base_query = base_query.order_by(LearningItem.order_in_container.asc(), LearningItem.item_id.asc())

        total_items = base_query.count()
        pagination = base_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        if not pagination.items:
            return {'items': [], 'pagination': {'total': total_items, 'page': page, 'per_page': per_page, 'pages': pagination.pages}}
        
        item_ids = [item.item_id for item in pagination.items]
        progress_records = LearningProgress.query.filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD,
            LearningProgress.item_id.in_(item_ids)
        ).all()
        progress_map = {p.item_id: p for p in progress_records}
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
                stability = progress.fsrs_stability or 0.0
                state = progress.fsrs_state
                if state == 0: status = 'new'
                elif state in [1, 3]: status = 'learning'
                elif stability >= 21.0: status = 'mastered'
                else: status = 'reviewing'
                is_due = progress.fsrs_due and progress.fsrs_due.replace(tzinfo=timezone.utc) <= now if progress.fsrs_due else False
                memory_level = progress.memory_level if hasattr(progress, 'memory_level') else 0
                difficulty = progress.fsrs_difficulty or 0.0
                repetitions = progress.repetitions or 0
                has_note = bool((progress.mode_data or {}).get('note'))
                
                # Format Next Review
                if progress.fsrs_due:
                    due_date = progress.fsrs_due.replace(tzinfo=timezone.utc)
                    diff = due_date - now
                    if diff.total_seconds() <= 0:
                        next_review = "Ngay bây giờ"
                    elif diff.days > 365:
                         next_review = f"{diff.days // 365} năm"
                    elif diff.days > 30:
                        next_review = f"{diff.days // 30} tháng"
                    elif diff.days > 0:
                        next_review = f"{diff.days} ngày"
                    elif diff.seconds > 3600:
                        next_review = f"{diff.seconds // 3600} giờ"
                    else:
                        next_review = f"{diff.seconds // 60} phút"
                else:
                    next_review = "-"

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
            
            # Check for AI explanation existence (check if string is not empty/null)
            has_ai = bool(item.ai_explanation and item.ai_explanation.strip())
            
            # Check if hard
            is_hard = False
            if progress:
                # Simple check compatible with HardItemService logic
                is_hard = (progress.incorrect_streak or 0) >= 3 or ((progress.repetitions or 0) > 10 and (progress.fsrs_stability or 0) < 7.0)

            result_items.append({
                'item_id': item.item_id, 
                'term': term, 
                'definition': definition, 
                'mastery': mastery, 
                'retrievability': retrievability, 
                'status': status, 
                'is_due': is_due, 
                'memory_level': memory_level,
                'fsrs_stability': stability,
                'fsrs_difficulty': difficulty,
                'repetitions': repetitions,
                'has_ai': has_ai,
                'has_note': has_note,
                'is_hard': is_hard,
                'next_review': next_review,
                'state_label': state_label
            })
        
        learned_count = db.session.query(func.count(LearningProgress.progress_id)).join(LearningItem, LearningProgress.item_id == LearningItem.item_id).filter(
            LearningItem.container_id == container_id, LearningProgress.user_id == user_id, LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD, LearningProgress.fsrs_state != LearningProgress.STATE_NEW
        ).scalar()
        
        return {'items': result_items, 'pagination': {'total': total_items, 'page': page, 'per_page': per_page, 'pages': pagination.pages}, 'learned_count': learned_count}

    @staticmethod
    def _is_log_correct(log) -> bool:
        if log.is_correct is not None: return log.is_correct
        if log.rating is not None: return log.rating >= 2
        return False

    @staticmethod
    def _get_start_date(timeframe: str) -> datetime | None:
        # Use naive utcnow to match SQLite's likely storage format
        now = datetime.utcnow()
        if timeframe == 'day':
            # Start of today (UTC)
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == 'week':
            # Start of week (Monday)
            start = now - timedelta(days=now.weekday())
            return start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == 'month':
            # Start of month
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
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
