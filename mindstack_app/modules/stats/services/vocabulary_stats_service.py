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
# REFAC: StudyLog removed (Isolation)
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
        from mindstack_app.models import LearningContainer, LearningItem
        from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsService
        
        # 1. Total Learning Sets (Sets containing items the user has started learning)
        learned_item_ids = FsrsService.get_learned_item_ids(user_id)
        learning_sets_count = 0
        if learned_item_ids:
            learning_sets_count = db.session.query(func.count(func.distinct(LearningItem.container_id))).filter(
                LearningItem.item_id.in_(learned_item_ids)
            ).scalar() or 0
            
        # 2. Total Explore Sets (Public OR owned by user, and NOT in learning list)
        explore_query = LearningContainer.query.filter(
            LearningContainer.container_type == 'FLASHCARD_SET',
            or_(
                LearningContainer.is_public == True,
                LearningContainer.creator_user_id == user_id
            )
        )
        if learned_item_ids:
             learned_container_ids = db.session.query(LearningItem.container_id).filter(
                LearningItem.item_id.in_(learned_item_ids)
            ).distinct()
             explore_query = explore_query.filter(~LearningContainer.container_id.in_(learned_container_ids))
        
        explore_sets_count = explore_query.count()

        fsrs_stats = FsrsService.get_global_stats(user_id)
        
        # [NEW] Enhanced Global Retention Calculation
        avg_retention = 0.0
        if learned_item_ids:
            states = FsrsService.get_memory_states(user_id, learned_item_ids)
            total_r = sum(FsrsService.get_retrievability(s) for s in states.values())
            avg_retention = round((total_r / len(learned_item_ids)) * 100, 1)

        return {
            'total_learning_sets': learning_sets_count,
            'total_explore_sets': explore_sets_count,
            'total_cards': fsrs_stats.get('total_cards', 0), 
            'learned_count': fsrs_stats.get('total_cards', 0),
            'mastered_count': fsrs_stats.get('mastered_count', 0), 
            'due_count': fsrs_stats.get('due_count', 0),
            'mastery_percentage': round((fsrs_stats.get('mastered_count', 0) / max(fsrs_stats.get('total_cards', 0), 1) * 100), 1),
            'average_retention': avg_retention
        }

    @staticmethod
    def get_difficult_items_overview(user_id: int, limit: int = 10) -> list:
        """Get the most difficult items for a user based on FSRS difficulty."""
        # Using FSRS interface to get items with high difficulty
        hard_items_data = FsrsService.get_hard_items(user_id, limit=limit)
        
        results = []
        for item_data in hard_items_data:
            item_id = item_data['item_id']
            item = LearningItem.query.get(item_id)
            if not item: continue
            
            content = item.content or {}
            
            # [NEW] Item Insights for Hub 2.0
            social = VocabularyStatsService.get_item_social_metrics(item_id)
            
            results.append({
                'id': item_id,
                'front': render_text_field(content.get('front', '?')),
                'container_title': item.container.title if item.container else 'Unknown',
                'difficulty': item_data['difficulty'],
                'retrievability': round(item_data['retrievability'] * 100, 1),
                'audio_url': content.get('audio'),
                'image_url': content.get('image'),
                'social': social
            })
        return results

    @staticmethod
    def get_item_social_metrics(item_id: int) -> dict:
        """Get aggregated social/community metrics for a specific item (anonymized)."""
        from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
        
        # 1. Get memory-related community stats from FSRS
        fsrs_metrics = FsrsService.get_item_community_aggregates(item_id)
        
        # 2. Get history-related community metrics from LearningHistory
        history_metrics = LearningHistoryInterface.get_item_community_metrics(item_id)
        
        # Combine metrics
        return {
            'learners_count': fsrs_metrics.get('learners_count', 0),
            'community_difficulty': fsrs_metrics.get('community_difficulty', 0.0),
            'community_accuracy': fsrs_metrics.get('community_accuracy', 0.0),
            'total_reviews': fsrs_metrics.get('total_reviews', 0),
            'mastered_count': fsrs_metrics.get('mastered_count', 0),
            'community_avg_duration': history_metrics.get('community_avg_duration', 0),
            'most_popular_mode': history_metrics.get('most_popular_mode')
        }

    @staticmethod
    def get_user_activity_heatmap(user_id: int, weeks: int = 12) -> list:
        """Get activity data for a heatmap (reviews per day)."""
        from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
        start_date = datetime.now(timezone.utc) - timedelta(weeks=weeks)
        return LearningHistoryInterface.get_daily_activity_counts(user_id, start_date)

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
    def get_chart_data(user_id: int, container_id: int, user_timezone_str: Optional[str] = None) -> dict:
        items = LearningItem.query.filter(LearningItem.container_id == container_id, LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])).all()
        item_ids = [item.item_id for item in items]
        if not item_ids: return {
            'distribution': {'weak': 0, 'medium': 0, 'strong': 0}, 
            'timeline': {'dates': [], 'values': []},
            'activity': {'new_items': [], 'reviews': []}
        }
        
        # REFAC: Use FsrsInterface
        progress_map = FsrsService.get_memory_states(user_id, item_ids)
        
        weak = medium = strong = 0
        for p in progress_map.values():
            r = FsrsService.get_retrievability(p)
            if r < 0.7: weak += 1
            elif r < 0.9: medium += 1
            else: strong += 1
        
        from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
        
        import pytz
        
        # We need a start_date for the timeline, let's assume 30 days ago for now
        now_utc = datetime.now(timezone.utc)
        
        # Handle user timezone
        user_tz = pytz.timezone(user_timezone_str) if user_timezone_str else pytz.UTC
        now_local = now_utc.astimezone(user_tz)
        start_date_utc = (now_local - timedelta(days=30)).astimezone(pytz.UTC)
        
        logs = LearningHistoryInterface.get_study_log_timeline(user_id, item_ids, start_date_utc)
        
        # 2. Activity Timeline (New vs Review)
        # To accurately identify "New" items, we need the absolute first review timestamp for each item
        first_review_map = LearningHistoryInterface.get_first_review_dates(user_id, item_ids)
        
        timeline_data = defaultdict(list) # For retention/mastery
        new_items_daily = defaultdict(set) # item_id per day
        reviews_daily = defaultdict(int) 

        for log in logs:
            fsrs = log.get('fsrs_snapshot') or {}
            stability = fsrs.get('stability')
            timestamp_utc = log.get('timestamp')
            item_id = log.get('item_id')
            
            if timestamp_utc:
                # Convert UTC timestamp to user local time
                if timestamp_utc.tzinfo is None:
                    timestamp_utc = pytz.UTC.localize(timestamp_utc)
                local_timestamp = timestamp_utc.astimezone(user_tz)
                
                date_key = local_timestamp.strftime('%d/%m')
                if stability is not None:
                    timeline_data[date_key].append(min((stability)/21.0, 1.0) * 100)
                
                # Activity tracking
                # A log is "New" if its timestamp matches the absolute first review of that item
                if timestamp_utc == first_review_map.get(item_id):
                    new_items_daily[date_key].add(item_id)
                else:
                    reviews_daily[date_key] += 1
        
        dates, values = [], []
        new_items_values = []
        reviews_values = []
        
        for i in range(29, -1, -1):
            date_local = now_local - timedelta(days=i)
            date_key = date_local.strftime('%d/%m')
            dates.append(date_key)
            
            # Retention
            if date_key in timeline_data: 
                values.append(round(sum(timeline_data[date_key]) / len(timeline_data[date_key]), 1))
            else: 
                values.append(None)
            
            # Activity
            new_items_values.append(len(new_items_daily[date_key]))
            reviews_values.append(reviews_daily[date_key])
            
        # Get UTC offset for label (e.g., UTC+7)
        offset = now_local.strftime('%z')
        if offset:
            # format +0700 -> UTC+7
            hours = int(offset[:3])
            timezone_label = f"UTC{hours:+d}"
        else:
            timezone_label = "UTC"

        return {
            'distribution': {'weak': weak, 'medium': medium, 'strong': strong}, 
            'timeline': {'dates': dates, 'values': values},
            'activity': {
                'new_items': new_items_values,
                'reviews': reviews_values
            },
            'timezone_label': timezone_label
        }

    @staticmethod
    def get_item_stats(user_id: int, item_id: int) -> dict:
        item = LearningItem.query.get(item_id)
        if not item: return None
        content = item.content or {}
        
        # REFAC: Use FsrsInterface
        progress = FsrsService.get_item_state(user_id, item_id)
        
        from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
        
        # Fetch detailed history (limit 500 for detailed log list)
        logs = LearningHistoryInterface.get_item_history(item_id, limit=500)
        # Note: HistoryQueryService.get_item_history now returns DTO dicts.
        
        total_attempts = len(logs)
        total_correct = sum(1 for log in logs if VocabularyStatsService._is_log_dict_correct(log))
            
        total_duration_ms = sum(log['review_duration'] for log in logs if log.get('review_duration'))
        
        total_score = 0
        for log in logs:
            game = log.get('gamification_snapshot') or {}
            total_score += game.get('score_change', 0)
        
        mode_counts = {}
        for log in logs:
            mode = log.get('learning_mode') or 'unknown'
            if mode not in mode_counts: mode_counts[mode] = {'count': 0, 'correct': 0, 'duration': 0, 'score': 0}
            mode_counts[mode]['count'] += 1
            if log.get('review_duration'): mode_counts[mode]['duration'] += log['review_duration']
            if VocabularyStatsService._is_log_dict_correct(log): mode_counts[mode]['correct'] += 1
            
            game = log.get('gamification_snapshot') or {}
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
        
        if logs:
            timestamps = [log['timestamp'] for log in logs if log.get('timestamp')]
            if timestamps:
                first_reviewed = min(timestamps)
                last_reviewed_log = max(timestamps)
            else:
                first_reviewed = None
                last_reviewed_log = None
        else:
            first_reviewed = None
            last_reviewed_log = None
        
        status = 'new'
        if progress:
            now = datetime.now(timezone.utc)
            if stability >= 21.0: status = 'mastered'
            elif progress.due_date and (progress.due_date.replace(tzinfo=timezone.utc) if progress.due_date.tzinfo is None else progress.due_date) <= now: status = 'due'
            else:
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

        # [NEW] Single Source of Truth for Notes
        from mindstack_app.modules.notes.interface import get_note as get_user_note
        note_content = ""
        try:
            note_result = get_user_note(user_id, 'item', item_id)
            if note_result.get('success') and note_result.get('exists'):
                note_content = note_result.get('content', '')
            else:
                # Fallback to old FSRS state
                note_content = (progress.data or {}).get('note', '') if progress else ''
        except Exception:
            pass

        durations = [log['review_duration'] for log in logs if log.get('review_duration')]
        min_duration = min(durations) if durations else 0

        # [NEW] Advanced Memory Insights
        time_to_mastery = "N/A"
        forgetting_curve = []
        if progress and progress.stability > 0:
            # Estimate days to mastery (stability >= 21)
            # Stability grows roughly by a factor (S_new = S_old * factor)
            # For simplicity, we assume a growth factor of 2.5 per successful review
            # S * (2.5 ^ n) = 21 => n = log2.5(21/S)
            import math
            if stability < 21:
                reviews_needed = math.ceil(math.log(21/stability, 2.5)) if stability > 0 else 5
                # Assuming avg interval is equal to current stability
                days_estimated = reviews_needed * stability
                time_to_mastery = f"~{int(days_estimated)} ngày"
            else:
                time_to_mastery = "Đã thành thạo"

            # Generate Forgetting Curve (Next 30 days)
            now = datetime.now(timezone.utc)
            for i in range(0, 31, 5):
                elapsed = i
                # retrievability = 0.9 ^ (elapsed / stability)
                r = 0.9 ** (elapsed / stability)
                forgetting_curve.append({
                    'day': i,
                    'retrievability': round(r * 100, 1)
                })

        # [NEW] Item Insights for Detail Hub 2.0
        social = VocabularyStatsService.get_item_social_metrics(item_id)

        return {
            'social': social,
            'markers': marker_list,
            'item': {
                'id': item.item_id, 'container_title': item.container.title if item.container else 'Unknown Set', 'container_id': item.container_id,
                'front': render_text_field(content.get('front', '?')), 'back': render_text_field(content.get('back', '?')),
                'pronunciation': content.get('pronunciation'), 'meaning': render_text_field(content.get('meaning')),
                'image': content.get('image') or content.get('image_url') or content.get('image_front'),
                'audio': content.get('audio') or content.get('audio_url') or content.get('audio_front'),
                'audio_back': content.get('audio_back'),
                'image_back': content.get('image_back'),
                'example': render_text_field(content.get('example')),
                'example_meaning': render_text_field(content.get('example_meaning')), 'phonetic': content.get('phonetic'),
                'tags': content.get('tags', []), 'custom_data': content.get('custom_data') or content.get('custom_content', {}),
                'ai_explanation': render_text_field(item.ai_explanation),
                'note': note_content,
                'full_content': content
            },
            'progress': {
                'status': status, 'retrievability': round(retrievability * 100, 1), 'streak': streak, 'ease_factor': round(difficulty, 2),
                'due_relative': VocabularyStatsService._get_relative_time_string(next_due) if next_due else 'Sẵn sàng',
                'stability_trend': 0, 'mastery_trend': 0, 'first_reviewed': first_reviewed, 'last_reviewed_log': last_reviewed_log,
                'last_reviewed_relative': VocabularyStatsService._get_relative_time_string(last_reviewed_log) if last_reviewed_log else 'Chưa học',
                # [NEW] FSRS Stats & Interaction Counters
                'fsrs_stability': stability, 'fsrs_difficulty': difficulty, 'fsrs_state': getattr(progress, 'state', 0) if progress else 0,
                'mastery_days': time_to_mastery,
                'forgetting_curve': forgetting_curve,
                'total_reps': total_attempts,
                'mcq_reps': (progress.data or {}).get('mcq_reps', 0) if progress else 0,
                'typing_reps': (progress.data or {}).get('typing_reps', 0) if progress else 0,
            },
            'modes': mode_counts,
            'performance': {
                'total_reviews': total_attempts, 'accuracy': round(accuracy, 1), 'total_time_ms': total_duration_ms,
                'avg_time_ms': round(avg_duration, 0), 'min_time_ms': min_duration, 'total_score': total_score, 'avg_score': round(avg_score, 1)
            },
            'history': [
                {
                    'timestamp': log['timestamp'].replace(tzinfo=timezone.utc).isoformat() if log.get('timestamp') else None, 
                    'mode': log.get('learning_mode'), 
                    'result': 'Correct' if VocabularyStatsService._is_log_dict_correct(log) else 'Incorrect',
                    'duration_ms': log.get('review_duration', 0), 
                    'user_answer': log.get('user_answer'), 
                    'score_change': (log.get('gamification_snapshot') or {}).get('score_change', 0), 
                    'score_base': (log.get('gamification_snapshot') or {}).get('score_base', 0),
                    'score_bonus': (log.get('gamification_snapshot') or {}).get('score_bonus', 0),
                    'rating': log.get('rating'),
                    'gamification_snapshot': log.get('gamification_snapshot') or {},
                    'fsrs_snapshot': log.get('fsrs_snapshot') or {},
                    'context_snapshot': log.get('context_snapshot') or {}
                }
                for log in logs[:100] # Increased limit for better charts
            ],
            'permissions': {'can_edit': can_edit, 'edit_url': edit_url}
        }

    @staticmethod
    def get_course_overview_stats(user_id: int, container_id: int, page: int = 1, per_page: int = 12, sort_by: str = 'default', filter_mode: str = 'all') -> dict:
        base_query = LearningItem.query.filter(
            LearningItem.container_id == container_id,
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        )

        # [NEW] Apply Filter First
        if filter_mode in ['learned', 'due']:
             base_query = FsrsService.apply_memory_filter(base_query, user_id, filter_mode)

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
        
        # [NEW] Batch fetch notes from dedicated module
        from mindstack_app.modules.notes.interface import get_notes_map
        notes_map = {}
        try:
            notes_map = get_notes_map(user_id, 'item', item_ids)
        except Exception:
            pass

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
                repetitions = (progress.times_correct or 0) + (progress.times_incorrect or 0)
                
                # Check both dedicated module and fallback
                has_note = bool(notes_map.get(item.item_id) or (progress.data or {}).get('note'))
                
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
                state_labels = {0: 'New', 1: 'Learning', 2: 'Review', 3: 'Relearning'}
                state_label = state_labels.get(state, 'Unknown')
            else:
                mastery = retrievability = 0
                status = 'new'
                is_due = False
                memory_level = 0
                difficulty = stability = repetitions = 0
                has_note = False
                next_review = "-"
                state_label = "New"
            
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
    def _is_log_dict_correct(log: dict) -> bool:
        is_correct = log.get('is_correct')
        if is_correct is not None: return is_correct
        rating = log.get('rating')
        if rating is not None: return rating >= 2
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
