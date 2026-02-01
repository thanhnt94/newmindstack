# File: flashcard/engine/core.py
# FlashcardEngine - Core logic for flashcard learning

from datetime import datetime, timezone
from mindstack_app.models import db, User, LearningItem
from mindstack_app.modules.learning.models import LearningProgress
from mindstack_app.core.signals import card_reviewed
from mindstack_app.utils.db_session import safe_commit
from mindstack_app.modules.fsrs.interface import FSRSInterface


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
        
        Args:
            user_id: ID of the user.
            item_id: ID of the item.
            quality: Answer quality (0-5).
            current_user_total_score: Current score for UI update.
            mode: Learning mode (e.g., 'all_review').
            update_srs: Whether to update SRS progress (False for Collab).
            session_id: Learning session ID for context.
            container_id: Container ID for faster queries.
            learning_mode: Learning mode string for ReviewLog.
            
        Returns:
            tuple: (score_change, new_total_score, result_type, new_status, item_stats, memory_power_data)
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
        progress = None
        memory_power_data = None  # NEW: Track Memory Power metrics
        
        # Capture previous state for delta animation
        old_memory_power = 0.0
        old_progress = LearningProgress.query.filter_by(
            user_id=user_id, item_id=item_id, learning_mode='flashcard'
        ).first()
        if old_progress:
            old_memory_power = round(FsrsService.get_memory_power(old_progress) * 100, 1)

        if update_srs:
            # Update SRS via Interface (Pure FSRS)
            from mindstack_app.modules.fsrs.interface import FSRSInterface
            
            progress, srs_result = FSRSInterface.process_review(
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
            # For backward compatibility, let's assume we still need score_change here if srs_result has it
            # (Our SrsResultDTO has score_points=0 currently, we need to bridge with Scoring module)
            from mindstack_app.modules.learning.logics.scoring_engine import ScoringEngine
            is_correct = (quality >= 3)
            score_result = ScoringEngine.calculate_answer_points(
                mode='flashcard',
                quality=quality,
                is_correct=is_correct,
                correct_streak=progress.correct_streak,
                stability=progress.fsrs_stability,
                difficulty=progress.fsrs_difficulty
            )
            score_change = score_result.total_points
            
            # Extract FSRS metrics for frontend
            memory_power_data = {
                'stability': round(srs_result.stability, 2),  # Days
                'retrievability': round(srs_result.retrievability * 100, 1),  # %
                'old_retrievability': old_memory_power,  # % (for delta animation)
                'correct_streak': srs_result.correct_streak,
                'incorrect_streak': srs_result.incorrect_streak,
                'next_review': srs_result.next_review.isoformat() if srs_result.next_review else None,
                'interval_minutes': srs_result.interval_minutes
            }
        else:
            # No SRS update (Collab or All Review)
            progress = LearningProgress.query.filter_by(
                user_id=user_id, item_id=item_id, learning_mode='flashcard'
            ).first()
            if not progress:
                # Temporary progress object for stats (not committed unless needed)
                progress = LearningProgress(
                    user_id=user_id, item_id=item_id, 
                    learning_mode='flashcard', status='new'
                )
                db.session.add(progress)

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

        # Optimistic score update (actual DB update happens in listener)
        new_total_score = current_user_total_score + score_change

        safe_commit(db.session)

        # distinct statistics retrieval
        item_stats = cls.get_item_statistics(user_id, item_id)

        return score_change, new_total_score, result_type, {0: 'new', 1: 'learning', 2: 'review', 3: 'relearning'}.get(progress.fsrs_state, 'new'), item_stats, memory_power_data

    @staticmethod
    def get_item_statistics(user_id: int, item_id: int) -> dict:
        """
        Get detailed statistics for a flashcard item.
        Mirroring logic from legacy stats_logic.py
        """
        progress = LearningProgress.query.filter_by(
            user_id=user_id, item_id=item_id, learning_mode='flashcard'
        ).first()
        
        base_stats = {
            'times_reviewed': 0, 'correct_count': 0, 'incorrect_count': 0, 'vague_count': 0,
            'correct_rate': 0.0, 'current_streak': 0, 'longest_streak': 0,
            'first_seen': None, 'last_reviewed': None, 'next_review': None,
            'easiness_factor': 0.0, 'repetitions': 0, 'interval': 0,
            'status': 'new', 'mastery': 0.0, 'memory_power': 0.0,
            'preview_count': 0, 'has_real_reviews': False,
            'has_preview_history': False, 'has_preview_only': False,
            'preview_count': 0, 'has_real_reviews': False,
            'has_preview_history': False, 'has_preview_only': False,
            'recent_reviews': [],
            'rating_counts': {1: 0, 2: 0, 3: 0, 4: 0},
        }

        if not progress:
            return base_stats

        stats = base_stats.copy()
        
        # Safe timezone formatting helper
        def _fmt_date(dt):
            if not dt: return None
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()

        stats.update({
            'first_seen': _fmt_date(progress.first_seen_timestamp) if hasattr(progress, 'first_seen_timestamp') else None,
            'last_reviewed': _fmt_date(progress.fsrs_last_review),
            'next_review': _fmt_date(progress.fsrs_due),
            'easiness_factor': round(progress.fsrs_difficulty, 2),
            'repetitions': progress.repetitions,
            'interval': progress.current_interval or 0,
            'status': {0: 'new', 1: 'learning', 2: 'review', 3: 'relearning'}.get(progress.fsrs_state, 'new'),
            'mastery': round(min((progress.fsrs_stability or 0)/21.0, 1.0), 4),
            'memory_power': round(FSRSInterface.get_retrievability(progress) * 100, 1),
            # Spec v7: Custom state from mode_data
            'custom_state': progress.mode_data.get('custom_state', 'new') if progress.mode_data else 'new',
        })

        # Query ReviewLog table instead of legacy JSON review_history
        from mindstack_app.models import ReviewLog
        logs = ReviewLog.query.filter_by(
            user_id=user_id, item_id=item_id
        ).order_by(ReviewLog.timestamp.asc()).all()
        
        if not logs:
            return stats

        review_qualities = []
        normalized_entries = []

        for log in logs:
            quality = log.rating
            ts_str = log.timestamp.isoformat() if log.timestamp else None
            
            norm_entry = {
                'timestamp': ts_str, 
                'type': log.review_type or 'review',
                'user_answer_quality': quality,
                'result': 'correct' if quality >= 4 else ('vague' if quality >= 2 else 'incorrect')
            }
            
            review_qualities.append(quality)
            normalized_entries.append(norm_entry)

        stats['preview_count'] = 0  # No preview tracking in ReviewLog
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
