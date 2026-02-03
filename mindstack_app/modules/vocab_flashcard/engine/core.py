# File: flashcard/engine/core.py
# FlashcardEngine - Core logic for flashcard learning

from datetime import datetime, timezone
from mindstack_app.models import db, User, LearningItem
from mindstack_app.modules.fsrs.models import ItemMemoryState
from mindstack_app.core.signals import card_reviewed
from mindstack_app.utils.db_session import safe_commit
from mindstack_app.modules.fsrs.interface import FSRSInterface
from mindstack_app.modules.learning_history.services import HistoryRecorder
from mindstack_app.modules.learning_history.models import StudyLog

class FlashcardEngine:
    """
    Centralized engine for Flashcard learning logic.
    Handles answer processing, scoring, and statistics retrieval.
    """

    @staticmethod
    def _get_config_score(key: str, default: int) -> int:
        """Fetch integer score from config."""
        from mindstack_app.services.config_service import get_runtime_config
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

        # Determine result type
        if quality >= 4:
            result_type = 'correct'
        elif quality >= 2:
            result_type = 'vague'
        else:
            result_type = 'incorrect'

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
                # Custom flags
                is_cram=is_all_review,
                learning_mode=learning_mode or mode
            )
            
            # Note: Scoring is now handled via card_reviewed signal or should be called separately
            from mindstack_app.modules.learning.logics.scoring_engine import ScoringEngine
            is_correct = (quality >= 3)
            score_result = ScoringEngine.calculate_answer_points(
                mode='flashcard',
                quality=quality,
                is_correct=is_correct,
                correct_streak=state_record.streak,
                stability=state_record.stability,
                difficulty=state_record.difficulty
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
            # No SRS update (Collab or All Review)
            # Fetch existing state without updating
            state_record = ItemMemoryState.query.filter_by(
                user_id=user_id, item_id=item_id
            ).first()
            if not state_record:
                # Temporary progress object for stats (not committed unless needed)
                # But ItemMemoryState has required fields.
                # Just create dummy
                state_record = ItemMemoryState(
                    user_id=user_id, item_id=item_id, 
                    state=0
                )
                # db.session.add(progress) # Don't add if we don't want to persist?

            # Scoring for Collab/No-SRS
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

        # Emit signal for decoupled scoring (Gamification module listens)
        card_reviewed.send(
            None,  # sender (None for class-based calls)
            user_id=user_id,
            item_id=item_id,
            quality=quality,
            is_correct=(quality >= 3),
            learning_mode='flashcard',
            score_points=score_change,
            item_type='FLASHCARD',
            reason=log_reason
        )

        # Optimistic score update
        new_total_score = current_user_total_score + score_change
        
        # === Record Interaction via HistoryRecorder ===
        HistoryRecorder.record_interaction(
            user_id=user_id,
            item_id=item_id,
            result_data={
                'rating': quality,
                'user_answer': user_answer_text,
                'is_correct': (quality >= 3),
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

        # distinct statistics retrieval
        item_stats = cls.get_item_statistics(user_id, item_id)

        return score_change, new_total_score, result_type, {0: 'new', 1: 'learning', 2: 'review', 3: 'relearning'}.get(state_record.state, 'new'), item_stats, srs_data

    @staticmethod
    def get_item_statistics(user_id: int, item_id: int) -> dict:
        """
        Get detailed statistics for a flashcard item.
        Mirroring logic from legacy stats_logic.py
        """
        state_record = ItemMemoryState.query.filter_by(
            user_id=user_id, item_id=item_id
        ).first()
        
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
            return base_stats

        stats = base_stats.copy()
        
        # Safe timezone formatting helper
        def _fmt_date(dt):
            if not dt: return None
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
            
        # Calculate interval if due date exists
        interval_val = 0
        if state_record.due_date and state_record.last_review:
             delta = (state_record.due_date.replace(tzinfo=timezone.utc) - state_record.last_review.replace(tzinfo=timezone.utc))
             interval_val = max(0.0, delta.total_seconds() / 86400.0)

        stats.update({
            'first_seen': _fmt_date(state_record.created_at),
            'last_reviewed': _fmt_date(state_record.last_review),
            'next_review': _fmt_date(state_record.due_date),
            'easiness_factor': round(state_record.difficulty or 0.0, 2), # Legacy support
            'difficulty': round(state_record.difficulty or 0.0, 2),
            'stability': round(state_record.stability or 0.0, 2),
            'retrievability': round(FSRSInterface.get_retrievability(state_record) * 100, 1),
            'retention': round(FSRSInterface.get_retrievability(state_record) * 100, 1), # Aliases
            'repetitions': state_record.repetitions,
            'interval': interval_val,
            'status': {0: 'new', 1: 'learning', 2: 'review', 3: 'relearning'}.get(state_record.state, 'new'),
            # Spec v7: Custom state from data
            'custom_state': (state_record.data or {}).get('custom_state', 'new') if state_record.data else 'new',
            'predicted_intervals': FSRSInterface.predict_next_intervals(user_id, item_id)
        })

        # Query StudyLog table
        logs = StudyLog.query.filter_by(
            user_id=user_id, item_id=item_id
        ).order_by(StudyLog.timestamp.asc()).all()
        
        if not logs:
            return stats

        review_qualities = []
        normalized_entries = []

        for log in logs:
            quality = log.rating
            ts_str = log.timestamp.isoformat() if log.timestamp else None
            
            norm_entry = {
                'timestamp': ts_str, 
                'type': log.learning_mode or 'review',
                'user_answer_quality': quality,
                'result': 'correct' if quality >= 4 else ('vague' if quality >= 2 else 'incorrect')
            }
            
            review_qualities.append(quality)
            normalized_entries.append(norm_entry)

        stats['preview_count'] = 0  # No preview tracking
        stats['has_preview_history'] = False

        if not review_qualities:
            return stats

        # Calculate aggregates
        c = 0
        ic = 0
        v = 0
        curr_s = 0
        long_s = 0
        
        for q in review_qualities:
            if q >= 3:
                c += 1
                curr_s += 1
            else:
                ic += 1
                if curr_s > long_s: long_s = curr_s
                curr_s = 0
            
            if q == 2:
                v += 1
        
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
            'has_preview_only': False,
            'recent_reviews': normalized_entries[-20:], # Return last 20 for detailed history
            'rating_counts': {
                1: review_qualities.count(1),
                2: review_qualities.count(2),
                3: review_qualities.count(3),
                4: review_qualities.count(4)
            }
        })

        return stats
