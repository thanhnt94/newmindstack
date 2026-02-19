# File: flashcard/engine/core.py
# FlashcardEngine - Core logic for flashcard learning

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Union

from mindstack_app.models import db, User, LearningItem, StudyLog
from mindstack_app.core.signals import card_reviewed
from mindstack_app.utils.db_session import safe_commit
from mindstack_app.modules.fsrs.interface import FSRSInterface
from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
from mindstack_app.modules.learning.interface import LearningInterface

from mindstack_app.services.config_service import get_runtime_config
from mindstack_app.utils.content_renderer import render_content_dict
from mindstack_app.utils.media_paths import build_relative_media_path

from ..services.query_builder import FlashcardQueryBuilder
from .algorithms import get_accessible_flashcard_set_ids
from .vocab_flashcard_mode import get_flashcard_mode_by_id
from flask import url_for, current_app

class FlashcardEngine:
    """
    Centralized engine for Flashcard learning logic.
    Handles answer processing, scoring, and statistics retrieval.
    """

    @staticmethod
    def get_next_batch(user_id: int, set_id: Union[int, str, List[int]], mode: str, processed_ids: List[int], 
                      db_session_id: Optional[int] = None, batch_size: int = 1, current_db_item_id: Optional[int] = None):
        """
        Stateless fetching of next flashcard items.
        Handles resume logic (if db_session_id provided) and standard query building.
        """
        # 1. RESUME LOGIC
        items = []
        if current_db_item_id and current_db_item_id not in processed_ids:
            # The session has a pending item stored in DB
            item = LearningItem.query.get(current_db_item_id)
            if item:
                items = [item]

        # 2. FETCH LOGIC
        if not items:
            qb = FlashcardQueryBuilder(user_id)
            
            # Resolve Set IDs
            if set_id == 'all':
                accessible_ids = get_accessible_flashcard_set_ids(user_id)
                qb.filter_by_containers(accessible_ids)
            else:
                s_ids = set_id if isinstance(set_id, list) else [int(set_id)]
                qb.filter_by_containers(s_ids)

            # Apply Mode Filter
            mode_obj = get_flashcard_mode_by_id(mode)
            if mode_obj and hasattr(qb, mode_obj.filter_method):
                filter_func = getattr(qb, mode_obj.filter_method)
                filter_func()
            else:
                qb.filter_mixed()
            
            # Exclude processed
            qb.exclude_items(processed_ids)
            
            items = qb.get_query().limit(batch_size).all()
        
        if not items:
            return None

        # 3. FORMAT RESPONSE
        items_data = []
        user_role = getattr(User.query.get(user_id), 'user_role', 'user')

        for item in items:
            # Check permission
            can_edit = False
            if item.container:
                can_edit = (item.container.creator_user_id == user_id or user_role == 'admin')
            
            edit_url = ''
            if can_edit:
                edit_url = url_for('content_management.edit_item', container_id=item.container_id, item_id=item.item_id)

            # Initial Stats
            initial_stats = FlashcardEngine.get_item_statistics(user_id, item.item_id)
            
            # First Time Check
            is_first_time_card = (initial_stats.get('status') == 'new' and initial_stats.get('times_reviewed') == 0)

            item_content = render_content_dict(item.content) if item.content else {}

            # Audio Path Resolution
            media_folder = item.container.media_audio_folder if item.container else None
            for field in ['front_audio_url', 'back_audio_url']:
                val = item_content.get(field)
                if val and not val.startswith(('http://', 'https://', '/')):
                    rel_path = build_relative_media_path(val, media_folder)
                    if rel_path:
                        item_content[field] = f"/media/{rel_path}"

            # Backend Rendering [Refactor - Thin Client]
            from .renderer import FlashcardRenderer
            
            # Fetch container display settings if available
            display_settings = {
                'can_edit': can_edit,
                'edit_url': edit_url,
                'is_media_hidden': False,
                'is_audio_autoplay': True
            }
            
            if item.container and item.container.settings:
                container_display = item.container.settings.get('display', {})
                display_settings.update(container_display)

            # Bridge for renderer
            item_for_renderer = {
                'id': item.item_id,
                'front_text': item_content.get('front', ''),
                'back_text': item_content.get('back', ''),
                'front_image': item_content.get('front_img'),
                'back_image': item_content.get('back_img'),
                'front_audio_url': item_content.get('front_audio_url'),
                'back_audio_url': item_content.get('back_audio_url'),
                'has_front_audio': bool(item_content.get('front_audio_url')),
                'has_back_audio': bool(item_content.get('back_audio_url')),
                'front_audio_content': item_content.get('front_text') or item_content.get('front'),
                'back_audio_content': item_content.get('back_text') or item_content.get('back'),
                'category': item_content.get('category', 'default'),
                'buttons_html': item_content.get('buttons_html', '')
            }

            html_payload = FlashcardRenderer.render_item(item_for_renderer, initial_stats, display_settings=display_settings)

            item_dict = {
                'item_id': item.item_id,
                'container_id': item.container_id,
                'content': item_content,
                'html_front': html_payload['front'],
                'html_back': html_payload['back'],
                'html_full': html_payload['full_html'],
                'ai_explanation': item.ai_explanation,
                'can_edit': can_edit,
                'edit_url': edit_url,
                'initial_stats': initial_stats,
                'initial_streak': initial_stats.get('current_streak', 0),
                'is_first_time_card': is_first_time_card
            }
            items_data.append(item_dict)

        return items_data

    @staticmethod
    def _get_config_score(key: str, default: int) -> int:
        """Fetch integer score from config."""
        try:
            return int(get_runtime_config(key, default))
        except (TypeError, ValueError):
            return default

    @classmethod
    def process_answer(cls, user_id: int, item_id: int, quality: int, 
                      current_user_total_score: int, mode: str = None, 
                      update_srs: bool = True,
                      duration_ms: int = 0, user_answer_text: str = None,
                      session_id: int = None, container_id: int = None,
                      learning_mode: str = None):
        """
        Process a flashcard answer.
        """
        item = LearningItem.query.get(item_id)
        if not item:
            return 0, current_user_total_score, 'error', "Error: Item not found", None, None

        is_all_review = (mode == 'all_review')

        # Determine result type (Spec: >= 2 is a pass/correct for session tracking)
        if quality >= 2:
            result_type = 'correct'
        else:
            result_type = 'incorrect'
            
        is_correct = (quality >= 2) # Pass threshold is 2 (Hard)

        score_change = 0
        state_record = None
        srs_data = None
        fsrs_snapshot = None

        if update_srs:
            # Update SRS via Interface (Pure FSRS)
            state_record, srs_result = FSRSInterface.process_review(
                user_id=user_id,
                item_id=item_id,
                quality=quality,
                mode='flashcard',
                duration_ms=duration_ms,
                container_id=container_id or (item.container_id if item else None),
                is_cram=is_all_review,
                learning_mode=learning_mode or mode
            )
            
            # Scoring
            is_first_time = (state_record.repetitions == 1) if state_record else False
            current_streak = state_record.streak if state_record else 0
            
            score_result = LearningInterface.calculate_answer_points(
                mode='flashcard',
                quality=quality,
                is_correct=is_correct,
                is_first_time=is_first_time,
                correct_streak=current_streak,
                response_time_seconds=duration_ms/1000 if duration_ms else None,
                stability=srs_result.stability if srs_result else 0,
                difficulty=srs_result.difficulty if srs_result else 0
            )
            score_change = score_result.total_points
            
            # Extract minimal FSRS metrics for UI
            srs_data = {
                'next_review': srs_result.next_review.isoformat() if srs_result.next_review else None,
                'interval_minutes': srs_result.interval_minutes
            }
            
            # Prepare Snapshot for History
            current_ivl = 0.0
            if state_record.due_date and state_record.last_review:
                 delta = (state_record.due_date.replace(tzinfo=timezone.utc) - state_record.last_review.replace(tzinfo=timezone.utc))
                 current_ivl = max(0.0, delta.total_seconds() / 86400.0)

            fsrs_snapshot = {
                'stability': srs_result.stability,
                'difficulty': srs_result.difficulty,
                'state': srs_result.state,
                'scheduled_days': current_ivl,
                'next_review': srs_result.next_review.isoformat() if srs_result.next_review else None
            }
        else:
            # No SRS update
            state_record = FSRSInterface.get_item_state(user_id, item_id)
            if not state_record:
                state_record = FSRSInterface.get_initial_state(user_id, item_id)

            if quality >= 4:
                score_change = cls._get_config_score('FLASHCARD_COLLAB_CORRECT', 10)
            elif quality >= 2:
                score_change = cls._get_config_score('FLASHCARD_COLLAB_VAGUE', 5)
            else:
                score_change = 0

        # Build reason for score log
        log_reason = f"Flashcard Answer (Quality: {quality})"
        if not update_srs:
            log_reason += " [Collab Mode]"

        # Emit signal for decoupled scoring
        card_reviewed.send(
            None,
            user_id=user_id,
            item_id=item_id,
            quality=quality,
            is_correct=is_correct,
            learning_mode='flashcard',
            score_points=score_change,
            item_type='FLASHCARD',
            reason=log_reason
        )

        new_total_score = current_user_total_score + score_change
        
        # Record Interaction via History
        LearningHistoryInterface.record_log(
            user_id=user_id,
            item_id=item_id,
            result_data={
                'rating': quality,
                'user_answer': user_answer_text,
                'is_correct': is_correct,
                'review_duration': duration_ms
            },
            context_data={
                'session_id': session_id,
                'container_id': container_id or (item.container_id if item else None),
                'learning_mode': learning_mode or 'flashcard'
            },
            fsrs_snapshot=fsrs_snapshot,
            game_snapshot={'score_earned': score_change}
        )

        safe_commit(db.session)

        item_stats = cls.get_item_statistics(user_id, item_id)

        return score_change, new_total_score, result_type, {0: 'new', 1: 'learning', 2: 'review', 3: 'relearning'}.get(state_record.state, 'new'), item_stats, srs_data

    @staticmethod
    def get_item_statistics(user_id: int, item_id: int) -> dict:
        """
        Get detailed statistics for a flashcard item.
        """
        state_record = FSRSInterface.get_item_state(user_id, item_id)
        
        base_stats = {
            'times_reviewed': 0, 'correct_count': 0, 'incorrect_count': 0, 'vague_count': 0,
            'correct_rate': 0.0, 'current_streak': 0, 'longest_streak': 0,
            'first_seen': None, 'last_reviewed': None, 'next_review': None,
            'easiness_factor': 0.0, 'difficulty': 0.0, 'stability': 0.0,
            'retrievability': 0.0, 'retention': 0.0,
            'repetitions': 0, 'interval': 0,
            'status': 'new',
            'preview_count': 0, 'has_real_reviews': False,
            'has_preview_history': False, 'has_preview_only': False,
            'recent_reviews': [],
            'rating_counts': {1: 0, 2: 0, 3: 0, 4: 0},
            'custom_state': 'new'
        }

        if not state_record:
            # Add minimal display DTO for NEW cards
            base_stats['display'] = {
                'difficulty': '0.0',
                'stability': '0',
                'retrievability': '0%',
                'times_reviewed': '0',
                'status_label': 'NEW',
                'status_color': 'blue'
            }
            return base_stats

        stats = base_stats.copy()
        
        def _fmt_date(dt):
            if not dt: return None
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
            
        interval_val = 0
        if state_record.due_date and state_record.last_review:
             delta = (state_record.due_date.replace(tzinfo=timezone.utc) - state_record.last_review.replace(tzinfo=timezone.utc))
             interval_val = max(0.0, delta.total_seconds() / 86400.0)

        stats.update({
            'first_seen': _fmt_date(state_record.created_at),
            'last_reviewed': _fmt_date(state_record.last_review),
            'next_review': _fmt_date(state_record.due_date),
            'easiness_factor': round(state_record.difficulty or 0.0, 2),
            'difficulty': round(state_record.difficulty or 0.0, 2),
            'stability': round(state_record.stability or 0.0, 2),
            'retrievability': round(FSRSInterface.get_retrievability(state_record) * 100, 1),
            'retention': round(FSRSInterface.get_retrievability(state_record) * 100, 1),
            'repetitions': state_record.repetitions,
            'interval': interval_val,
            'status': {0: 'new', 1: 'learning', 2: 'review', 3: 'relearning'}.get(state_record.state, 'new'),
            'custom_state': (state_record.data or {}).get('custom_state', 'new') if state_record.data else 'new',
            'predicted_intervals': FSRSInterface.predict_next_intervals(user_id, item_id)
        })

        # Use LearningHistoryInterface to fetch item history
        logs = LearningHistoryInterface.get_item_history(item_id)
        
        # Fallback: if logs are empty but repetitions > 0 (legacy data), 
        # use repetitions as the review count for the UI.
        if not logs and state_record.repetitions > 0:
            # Add display DTO for legacy fallback
            stats['display'] = {
                'difficulty': f"{stats['difficulty']:.1f}",
                'stability': f"{stats['stability']:.1f}" if stats['stability'] >= 1 else str(int(stats['stability'])),
                'retrievability': f"{int(stats['retrievability'])}%",
                'times_reviewed': str(stats['times_reviewed']),
                'status_label': stats['status'].upper(),
                'status_color': 'emerald' if stats['status'] == 'review' else 'blue'
            }
            return stats

        if not logs:
            # Add display DTO for cards with FSRS state but no logs (e.g. newly migrated)
            stats['display'] = {
                'difficulty': f"{stats['difficulty']:.1f}",
                'stability': f"{stats['stability']:.1f}" if stats['stability'] >= 1 else str(int(stats['stability'])),
                'retrievability': f"{int(stats['retrievability'])}%",
                'times_reviewed': str(stats['times_reviewed']),
                'status_label': stats['status'].upper(),
                'status_color': 'blue'
            }
            return stats

        review_qualities = []
        normalized_entries = []

        for log in logs:
            quality = log.get('rating', 0)
            timestamp = log.get('timestamp')
            ts_str = timestamp.isoformat() if timestamp else None
            
            norm_entry = {
                'timestamp': ts_str, 
                'type': 'review',
                'user_answer_quality': quality,
                'result': 'correct' if quality >= 4 else ('vague' if quality >= 2 else 'incorrect')
            }
            review_qualities.append(quality)
            normalized_entries.append(norm_entry)

        if not review_qualities:
            return stats

        c = 0 ; ic = 0 ; v = 0 ; curr_s = 0 ; long_s = 0
        for q in review_qualities:
            if q >= 2:
                c += 1 ; curr_s += 1
            else:
                ic += 1
                if curr_s > long_s: long_s = curr_s
                curr_s = 0
        
        if curr_s > long_s: long_s = curr_s
        
        total = len(review_qualities)
        stats.update({
            'times_reviewed': total,
            'correct_count': c,
            'incorrect_count': ic,
            'vague_count': v,
            'correct_rate': round((c/total)*100, 2) if total > 0 else 0.0,
            'current_streak': curr_s,
            'longest_streak': long_s,
            'has_real_reviews': True,
            'recent_reviews': normalized_entries[-20:],
            'rating_counts': {
                1: review_qualities.count(1),
                2: review_qualities.count(2),
                3: review_qualities.count(3),
                4: review_qualities.count(4)
            }
        })

        # Final Display DTO [Refactor - Thin Client]
        stats['display'] = {
            'difficulty': f"{stats['difficulty']:.1f}",
            'stability': f"{stats['stability']:.1f}" if stats['stability'] >= 1 else str(int(stats['stability'])),
            'retrievability': f"{int(stats['retrievability'])}%",
            'times_reviewed': str(stats['times_reviewed']),
            'status_label': stats['status'].upper(),
            'status_color': {
                'new': 'blue',
                'learning': 'orange',
                'review': 'emerald',
                'relearning': 'rose'
            }.get(stats['status'], 'blue')
        }

        return stats
