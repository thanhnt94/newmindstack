from datetime import datetime, timedelta, timezone
from mindstack_app.core.extensions import db
from mindstack_app.models import User
from mindstack_app.modules.gamification.models import ScoreLog
from mindstack_app.modules.learning_history.models import StudyLog
from .scoring_config_service import ScoringConfigService
from ..logics.calculator import ScoreCalculator

class RecalculationService:
    """
    Service to handle massive score recalculations when configs change.
    Updates BOTH score_logs AND gamification_snapshot in study_logs.
    """

    @staticmethod
    def recalculate_scores(days: int = 0) -> dict:
        """
        Full recalculation: updates score_logs + study_logs snapshot + user totals.
        If days > 0, only recalculate last N days. Otherwise, recalculate all.
        """
        print(f"[Recalculation] Started. days={days}")
        
        # ── Step 1: Fetch all study_logs (the source of truth for interactions) ──
        query = StudyLog.query
        if days > 0:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(StudyLog.timestamp >= start_date)
        
        study_logs = query.order_by(StudyLog.timestamp.desc()).all()
        print(f"[Recalculation] Found {len(study_logs)} study logs to process.")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for slog in study_logs:
            try:
                # Determine the quality/event_key from the study log
                rating = slog.rating
                if not rating or rating < 1 or rating > 4:
                    skipped_count += 1
                    continue
                
                config_keys = {1: 'SCORE_FSRS_AGAIN', 2: 'SCORE_FSRS_HARD', 3: 'SCORE_FSRS_GOOD', 4: 'SCORE_FSRS_EASY'}
                event_key = config_keys.get(rating, 'SCORE_FSRS_GOOD')
                
                # Build context from the study log's snapshots
                context = {
                    'difficulty': (slog.fsrs_snapshot or {}).get('difficulty', 0.0),
                    'stability': (slog.fsrs_snapshot or {}).get('stability', 0.0),
                    'streak': (slog.fsrs_snapshot or {}).get('streak', 0),
                    'is_correct': slog.is_correct,
                    'duration_ms': slog.review_duration or 0
                }
                if not context.get('streak') and slog.gamification_snapshot:
                    context['streak'] = (slog.gamification_snapshot or {}).get('streak', 0)
                
                # Calculate new score with current config
                new_score, breakdown = ScoreCalculator.calculate(event_key, context)
                
                # Update gamification_snapshot in study_log
                old_snapshot = slog.gamification_snapshot or {}
                old_score = old_snapshot.get('score_earned', old_snapshot.get('total_score', -1))
                
                new_snapshot = dict(old_snapshot)
                new_snapshot['score_earned'] = new_score
                new_snapshot['total_score'] = new_score
                new_snapshot['breakdown'] = breakdown
                
                if old_score != new_score or old_snapshot.get('breakdown') != breakdown:
                    slog.gamification_snapshot = new_snapshot
                    updated_count += 1
                else:
                    skipped_count += 1
                    
            except Exception as e:
                print(f"[Recalculation] Error study_log #{slog.log_id}: {e}")
                error_count += 1
                continue
        
        print(f"[Recalculation] Study logs: updated={updated_count}, unchanged={skipped_count}, errors={error_count}")
        
        # ── Step 2: Also update score_logs to match ──
        score_query = ScoreLog.query
        if days > 0:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            score_query = score_query.filter(ScoreLog.timestamp >= start_date)
        
        score_logs = score_query.all()
        score_updated = 0
        
        system_reasons = {
            'SCORE_FSRS_AGAIN', 'SCORE_FSRS_HARD', 'SCORE_FSRS_GOOD', 'SCORE_FSRS_EASY',
            'VOCAB_MCQ_CORRECT_BONUS', 'VOCAB_TYPING_CORRECT_BONUS',
            'VOCAB_MATCHING_CORRECT_BONUS', 'VOCAB_LISTENING_CORRECT_BONUS', 'VOCAB_SPEED_CORRECT_BONUS',
            'QUIZ_CORRECT_BONUS'
        }
        
        for log in score_logs:
            try:
                event_key = log.reason
                is_flashcard = (
                    event_key.startswith('Flashcard Answer') or 
                    event_key == "Vocab Flashcard Practice" or
                    event_key == "Flashcard Practice" or
                    log.item_type == 'FLASHCARD'
                )
                is_system = event_key in system_reasons
                
                if not is_system and not is_flashcard:
                    continue
                
                # Find matching study_log
                if log.item_id:
                    study_log = StudyLog.query.filter(
                        StudyLog.user_id == log.user_id,
                        StudyLog.item_id == log.item_id,
                        StudyLog.timestamp >= log.timestamp - timedelta(minutes=15),
                        StudyLog.timestamp <= log.timestamp + timedelta(minutes=15)
                    ).first()
                    
                    if study_log:
                        rating = study_log.rating or 3
                        event_key = {1: 'SCORE_FSRS_AGAIN', 2: 'SCORE_FSRS_HARD', 3: 'SCORE_FSRS_GOOD', 4: 'SCORE_FSRS_EASY'}.get(rating, 'SCORE_FSRS_GOOD')
                        context = {
                            'difficulty': (study_log.fsrs_snapshot or {}).get('difficulty', 0.0),
                            'stability': (study_log.fsrs_snapshot or {}).get('stability', 0.0),
                            'streak': (study_log.fsrs_snapshot or {}).get('streak', 0),
                            'is_correct': study_log.is_correct,
                            'duration_ms': study_log.review_duration or 0
                        }
                    else:
                        # Fallback: parse from reason string
                        if is_flashcard and 'Quality' in event_key:
                            import re
                            match = re.search(r'Quality: (\d)', event_key)
                            if match:
                                q = int(match.group(1))
                                event_key = {1: 'SCORE_FSRS_AGAIN', 2: 'SCORE_FSRS_HARD', 3: 'SCORE_FSRS_GOOD', 4: 'SCORE_FSRS_EASY'}.get(q)
                                context = {'is_correct': (q >= 2)}
                            else:
                                continue
                        elif is_system:
                            context = {'is_correct': (event_key != 'SCORE_FSRS_AGAIN')}
                        else:
                            continue
                else:
                    continue
                
                new_score, _ = ScoreCalculator.calculate(event_key, context)
                if log.score_change != new_score:
                    log.score_change = new_score
                    log.meta = context
                    score_updated += 1
                    
            except Exception:
                continue
        
        print(f"[Recalculation] Score logs: updated={score_updated}")
        
        db.session.commit()
        
        # ── Step 3: Sync User total_scores ──
        try:
            from mindstack_app.modules.gamification.interface import sync_all_users_scores
            sync_all_users_scores()
            print("[Recalculation] User totals synced.")
        except Exception as e:
            print(f"[Recalculation] Sync error: {e}")

        total_updated = updated_count + score_updated
        print(f"[Recalculation] DONE. Total updated: {total_updated}")
        
        return {
            'success': True,
            'updated_count': total_updated,
            'skipped_count': skipped_count,
            'message': f'Đã cập nhật {total_updated} bản ghi.'
        }
