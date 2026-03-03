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
    Updates study_logs.gamification_snapshot, fixes/creates score_logs, and syncs user totals.
    """

    @staticmethod
    def recalculate_scores(days: int = 0) -> dict:
        """
        Full recalculation:
        1. Update gamification_snapshot in study_logs (for receipt UI)
        2. Fill missing score_logs (for sessions where award_points silently failed)
        3. Update existing score_logs with new values
        4. Sync user total_scores
        """
        print(f"[Recalculation] Started. days={days}")
        
        config_keys = {1: 'SCORE_FSRS_AGAIN', 2: 'SCORE_FSRS_HARD', 3: 'SCORE_FSRS_GOOD', 4: 'SCORE_FSRS_EASY'}
        
        # ── Step 1: Update study_logs + collect gap info ──
        query = StudyLog.query
        if days > 0:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(StudyLog.timestamp >= start_date)
        
        study_logs = query.order_by(StudyLog.timestamp.desc()).all()
        print(f"[Recalculation] Found {len(study_logs)} study logs.")
        
        snapshot_updated = 0
        gaps_filled = 0
        skipped = 0
        errors = 0
        
        for slog in study_logs:
            try:
                rating = slog.rating
                if not rating or rating < 1 or rating > 4:
                    skipped += 1
                    continue
                
                event_key = config_keys.get(rating, 'SCORE_FSRS_GOOD')
                
                context = {
                    'difficulty': (slog.fsrs_snapshot or {}).get('difficulty', 0.0),
                    'stability': (slog.fsrs_snapshot or {}).get('stability', 0.0),
                    'streak': (slog.fsrs_snapshot or {}).get('streak', 0),
                    'is_correct': slog.is_correct,
                    'duration_ms': slog.review_duration or 0
                }
                
                new_score, breakdown = ScoreCalculator.calculate(event_key, context)
                
                # Update gamification_snapshot
                old_snapshot = slog.gamification_snapshot or {}
                new_snapshot = dict(old_snapshot)
                new_snapshot['score_earned'] = new_score
                new_snapshot['total_score'] = new_score
                new_snapshot['breakdown'] = breakdown
                
                old_score = old_snapshot.get('score_earned', old_snapshot.get('total_score', -1))
                if old_score != new_score or old_snapshot.get('breakdown') != breakdown:
                    slog.gamification_snapshot = new_snapshot
                    snapshot_updated += 1
                
                # Check if matching score_log exists (gap fill)
                has_score_log = ScoreLog.query.filter(
                    ScoreLog.user_id == slog.user_id,
                    ScoreLog.item_id == slog.item_id,
                    ScoreLog.timestamp >= slog.timestamp - timedelta(minutes=5),
                    ScoreLog.timestamp <= slog.timestamp + timedelta(minutes=5)
                ).first()
                
                if not has_score_log and new_score > 0:
                    # Create missing score_log
                    new_log = ScoreLog(
                        user_id=slog.user_id,
                        item_id=slog.item_id,
                        score_change=new_score,
                        reason=event_key,
                        item_type='FLASHCARD',
                        timestamp=slog.timestamp
                    )
                    db.session.add(new_log)
                    gaps_filled += 1
                    
            except Exception as e:
                print(f"[Recalculation] Error study_log #{slog.log_id}: {e}")
                errors += 1
                continue
        
        db.session.commit()
        print(f"[Recalculation] Step 1 done. Snapshots updated={snapshot_updated}, Gaps filled={gaps_filled}, Skipped={skipped}, Errors={errors}")
        
        # ── Step 2: Update existing score_logs with new values ──
        score_updated = 0
        try:
            score_query = ScoreLog.query
            if days > 0:
                start_date = datetime.now(timezone.utc) - timedelta(days=days)
                score_query = score_query.filter(ScoreLog.timestamp >= start_date)
            
            score_logs = score_query.all()
            
            for log in score_logs:
                try:
                    event_key = log.reason
                    is_flashcard = (
                        event_key.startswith('Flashcard Answer') or 
                        event_key == "Vocab Flashcard Practice" or
                        event_key == "Flashcard Practice" or
                        log.item_type == 'FLASHCARD'
                    )
                    is_system = event_key in {
                        'SCORE_FSRS_AGAIN', 'SCORE_FSRS_HARD', 'SCORE_FSRS_GOOD', 'SCORE_FSRS_EASY',
                        'VOCAB_MCQ_CORRECT_BONUS', 'VOCAB_TYPING_CORRECT_BONUS',
                        'VOCAB_MATCHING_CORRECT_BONUS', 'VOCAB_LISTENING_CORRECT_BONUS', 'VOCAB_SPEED_CORRECT_BONUS',
                        'QUIZ_CORRECT_BONUS'
                    }
                    
                    if not is_system and not is_flashcard:
                        continue
                    
                    if not log.item_id:
                        continue
                    
                    study_log = StudyLog.query.filter(
                        StudyLog.user_id == log.user_id,
                        StudyLog.item_id == log.item_id,
                        StudyLog.timestamp >= log.timestamp - timedelta(minutes=15),
                        StudyLog.timestamp <= log.timestamp + timedelta(minutes=15)
                    ).first()
                    
                    if study_log:
                        rating = study_log.rating or 3
                        event_key = config_keys.get(rating, 'SCORE_FSRS_GOOD')
                        context = {
                            'difficulty': (study_log.fsrs_snapshot or {}).get('difficulty', 0.0),
                            'stability': (study_log.fsrs_snapshot or {}).get('stability', 0.0),
                            'is_correct': study_log.is_correct,
                        }
                    else:
                        context = {'is_correct': (event_key != 'SCORE_FSRS_AGAIN')}
                    
                    new_score, _ = ScoreCalculator.calculate(event_key, context)
                    if log.score_change != new_score:
                        log.score_change = new_score
                        score_updated += 1
                        
                except Exception:
                    continue
            
            db.session.commit()
            print(f"[Recalculation] Step 2 done. Score logs updated={score_updated}")
        except Exception as e:
            print(f"[Recalculation] Step 2 skipped: {e}")
            db.session.rollback()
        
        # ── Step 3: Sync User total_scores from SUM(score_logs) ──
        try:
            from mindstack_app.modules.gamification.interface import sync_all_users_scores
            sync_all_users_scores()
            print("[Recalculation] Step 3 done. User totals synced.")
        except Exception as e:
            print(f"[Recalculation] Step 3 error: {e}")

        total_updated = snapshot_updated + gaps_filled + score_updated
        print(f"[Recalculation] ALL DONE. Total changes: {total_updated}")
        
        return {
            'success': True,
            'updated_count': total_updated,
            'skipped_count': skipped,
            'message': f'Cập nhật {snapshot_updated} biên lai, bù {gaps_filled} bản ghi thiếu, sửa {score_updated} điểm cũ.'
        }
