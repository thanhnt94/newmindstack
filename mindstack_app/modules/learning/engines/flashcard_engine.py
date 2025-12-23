
from datetime import datetime, timezone
from mindstack_app.models import db, User, LearningItem, FlashcardProgress
from mindstack_app.modules.gamification.services import ScoreService
from mindstack_app.modules.shared.utils.db_session import safe_commit
from mindstack_app.services.config_service import get_runtime_config
from mindstack_app.modules.learning.core.services.srs_service import SrsService

class FlashcardEngine:
    """
    Centralized engine for Flashcard learning logic.
    Handles answer processing, scoring, and statistics retrieval.
    """

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
                      update_srs: bool = True):
        """
        Process a flashcard answer.
        
        Args:
            user_id: ID of the user.
            item_id: ID of the item.
            quality: Answer quality (0-5).
            current_user_total_score: Current score for UI update.
            mode: Learning mode (e.g., 'all_review').
            update_srs: Whether to update SRS progress (False for Collab).
            
        Returns:
            tuple: (score_change, new_total_score, result_type, new_status, item_stats)
        """
        item = LearningItem.query.get(item_id)
        if not item:
            return 0, current_user_total_score, 'error', "Error: Item not found", None

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

        if update_srs and not is_all_review:
            # Update SRS via Service (which uses MemoryEngine)
            progress = SrsService.update_with_memory_power(
                user_id, item_id, quality, source_mode='flashcard'
            )
            
            # Scoring Logic
            if quality >= 4:
                score_change = cls._get_config_score('FLASHCARD_REVIEW_HIGH', 10)
            elif quality >= 2:
                score_change = cls._get_config_score('FLASHCARD_REVIEW_MEDIUM', 5)
            else:
                score_change = 0
        else:
            # No SRS update (Collab or All Review)
            progress = FlashcardProgress.query.filter_by(user_id=user_id, item_id=item_id).first()
            if not progress:
                # Temporary progress object for stats (not committed unless needed)
                progress = FlashcardProgress(user_id=user_id, item_id=item_id, status='new')
                db.session.add(progress)

            # Scoring for Collab/No-SRS
            if quality >= 4:
                score_change = cls._get_config_score('FLASHCARD_COLLAB_CORRECT', 10)
            elif quality >= 2:
                score_change = cls._get_config_score('FLASHCARD_COLLAB_VAGUE', 5)
            else:
                score_change = 0

        # Award Points
        log_reason = f"Flashcard Answer (Quality: {quality})"
        if not update_srs:
            log_reason += " [Collab Mode]"

        result = ScoreService.award_points(
            user_id=user_id,
            amount=score_change,
            reason=log_reason,
            item_id=item_id,
            item_type='FLASHCARD'
        )

        new_total_score = result.get('new_total') if result.get('success') and result.get('new_total') is not None else (current_user_total_score + score_change)

        safe_commit(db.session)

        # distinct statistics retrieval
        item_stats = cls.get_item_statistics(user_id, item_id)

        return score_change, new_total_score, result_type, progress.status, item_stats

    @staticmethod
    def get_item_statistics(user_id: int, item_id: int) -> dict:
        """
        Get detailed statistics for a flashcard item.
        Mirroring logic from legacy stats_logic.py
        """
        progress = FlashcardProgress.query.filter_by(user_id=user_id, item_id=item_id).first()
        
        base_stats = {
            'times_reviewed': 0, 'correct_count': 0, 'incorrect_count': 0, 'vague_count': 0,
            'correct_rate': 0.0, 'current_streak': 0, 'longest_streak': 0,
            'first_seen': None, 'last_reviewed': None, 'next_review': None,
            'easiness_factor': 2.5, 'repetitions': 0, 'interval': 0,
            'status': 'new', 'mastery': 0.0, 'memory_power': 0.0,
            'preview_count': 0, 'has_real_reviews': False,
            'has_preview_history': False, 'has_preview_only': False,
            'recent_reviews': [],
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
            'first_seen': _fmt_date(progress.first_seen_timestamp),
            'last_reviewed': _fmt_date(progress.last_reviewed),
            'next_review': _fmt_date(progress.due_time),
            'easiness_factor': round(progress.easiness_factor, 2),
            'repetitions': progress.repetitions,
            'interval': progress.interval,
            'status': progress.status,
            'mastery': round(progress.mastery or 0.0, 4),
            'memory_power': round(SrsService.get_memory_power(progress) * 100, 1),
        })

        # Process History (Legacy JSON + potentially new ReviewLog if we switch completely)
        # For now, relying on 'review_history' field as per legacy code
        history = progress.review_history or []
        if not history:
            return stats

        preview_entries = []
        review_qualities = []
        normalized_entries = []

        for entry in history:
            if not isinstance(entry, dict): continue
            
            quality = entry.get('user_answer_quality')
            
            # Normalize timestamp
            ts_val = entry.get('timestamp')
            ts_str = None
            if isinstance(ts_val, datetime):
                ts_str = _fmt_date(ts_val)
            elif isinstance(ts_val, str):
                ts_str = ts_val # Assume already string or fix if needed
            
            entry_type = entry.get('type') or ('preview' if quality is None else 'review')
            
            norm_entry = {'timestamp': ts_str, 'type': entry_type}

            if quality is None:
                preview_entries.append(norm_entry)
                continue

            try:
                q_val = int(float(quality))
            except (TypeError, ValueError):
                continue

            norm_entry['user_answer_quality'] = q_val
            norm_entry['result'] = 'correct' if q_val >= 4 else ('vague' if q_val >= 2 else 'incorrect')
            
            review_qualities.append(q_val)
            normalized_entries.append(norm_entry)

        stats['preview_count'] = len(preview_entries)
        stats['has_preview_history'] = stats['preview_count'] > 0

        if not review_qualities:
            stats['has_preview_only'] = stats['has_preview_history']
            return stats

        # Calculate aggregates
        total = len(review_qualities)
        correct = sum(1 for q in review_qualities if q >= 3)
        vague = sum(1 for q in review_qualities if q == 2)
        incorrect = total - correct # Note: legacy vague count was separate but incorrect included vague? 
        # Legacy logic:
        # if quality >= 3: correct++
        # else: incorrect++
        # if quality == 2: vague++
        # So 'incorrect' in legacy code includes vague?
        # Let's re-implement legacy loop exactly for safety.
        
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
            'recent_reviews': normalized_entries[-10:]
        })

        return stats
