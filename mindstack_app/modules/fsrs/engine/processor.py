# File: mindstack_app/modules/fsrs/engine/processor.py
from __future__ import annotations
import datetime
import random
from typing import Optional, Tuple, Dict, Any
from flask import current_app
from sqlalchemy import func
from mindstack_app.models import db, ReviewLog, LearningProgress
from ..schemas import SrsResultDTO, CardStateDTO, Rating, CardStateEnum
from ..logics.fsrs_engine import FSRSEngine
from ..services.settings_service import FSRSSettingsService
from mindstack_app.modules.fsrs.services.optimizer_service import FSRSOptimizerService

class FSRSProcessor:
    """Orchestrator for FSRS operations."""

    @staticmethod
    def _calculate_quiz_rating(is_correct: bool, duration_ms: int) -> int:
        if not is_correct: return Rating.Again
        easy_threshold = FSRSSettingsService.get('QUIZ_RATING_EASY_MS', 3000)
        good_threshold = FSRSSettingsService.get('QUIZ_RATING_GOOD_MS', 10000)
        if duration_ms < easy_threshold: return Rating.Easy
        elif duration_ms <= good_threshold: return Rating.Good
        else: return Rating.Hard

    @staticmethod
    def _calculate_typing_rating(target_text: str, user_answer: str, duration_ms: int) -> int:
        if not target_text or not user_answer: return Rating.Again
        t = target_text.strip().lower()
        u = user_answer.strip().lower()
        if t == u:
            if duration_ms > 0:
                wpm = (len(t) / 5.0) / (duration_ms / 60000.0)
                if wpm >= 40: return Rating.Easy
            return Rating.Good
        
        # Simple similarity check
        from ..logics.fsrs_engine import FSRSEngine # For typing imports if needed elsewhere
        # We'll use a local simple distance if needed or just skip for now as per original
        return Rating.Again

    @staticmethod
    def process_review(
        user_id: int,
        item_id: int,
        quality: int,
        mode: str = 'flashcard',
        duration_ms: int = 0,
        container_id: int = None,
        **kwargs
    ) -> Tuple[LearningProgress, SrsResultDTO]:
        # 0. Mode-Based Rating Calculation
        if mode in ['quiz', 'quiz_mcq', 'mcq']:
            is_correct_arg = kwargs.get('is_correct', quality >= 3)
            fsrs_rating = FSRSProcessor._calculate_quiz_rating(is_correct_arg, duration_ms)
        elif mode in ['typing', 'listening']:
            target_text = kwargs.get('target_text', '')
            user_answer = kwargs.get('user_answer', '')
            fsrs_rating = FSRSProcessor._calculate_typing_rating(target_text, user_answer, duration_ms)
        else:
            fsrs_rating = FSRSProcessor._normalize_rating(quality)
            
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # 2. Fetch/Create Progress
        progress = LearningProgress.query.filter_by(
            user_id=user_id, item_id=item_id, learning_mode=mode
        ).first()
        
        if not progress:
            progress = LearningProgress(
                user_id=user_id, item_id=item_id, learning_mode=mode,
                fsrs_state=CardStateEnum.NEW, fsrs_stability=0.0, fsrs_difficulty=0.0,
                repetitions=0, current_interval=0.0, correct_streak=0, incorrect_streak=0
            )
            db.session.add(progress)
            db.session.flush()

        # 3. Build CardState
        last_review = progress.fsrs_last_review
        if last_review and last_review.tzinfo is None:
            last_review = last_review.replace(tzinfo=datetime.timezone.utc)
            
        card_dto = CardStateDTO(
            stability=progress.fsrs_stability or 0.0,
            difficulty=progress.fsrs_difficulty or 0.0,
            reps=progress.repetitions or 0,
            lapses=progress.lapses or 0,
            state=progress.fsrs_state if progress.fsrs_state is not None else CardStateEnum.NEW,
            last_review=last_review,
            scheduled_days=progress.current_interval or 0.0
        )

        # 4. Get Config
        desired_retention = float(FSRSSettingsService.get('FSRS_DESIRED_RETENTION', 0.9))
        enable_fuzz = bool(FSRSSettingsService.get('FSRS_ENABLE_FUZZ', False))
        max_interval_days = int(FSRSSettingsService.get('FSRS_MAX_INTERVAL', 365))
        effective_weights = FSRSOptimizerService.get_user_parameters(user_id)

        # 5. Run Engine
        engine = FSRSEngine(custom_weights=effective_weights, desired_retention=desired_retention)
        new_card, next_due, log_info = engine.review_card(
            card_state=card_dto, rating=fsrs_rating, now=now, enable_fuzz=enable_fuzz
        )
        
        # Enforce Max Interval
        if new_card.scheduled_days > max_interval_days:
            new_card.scheduled_days = float(max_interval_days)
            next_due = now + datetime.timedelta(days=max_interval_days)

        # 6. Load Balancing
        daily_limit = int(FSRSSettingsService.get('FSRS_DAILY_LIMIT', 200))
        due_on_date_count = LearningProgress.query.filter(
            LearningProgress.user_id == user_id,
            func.date(LearningProgress.fsrs_due) == next_due.date()
        ).count()
        
        if due_on_date_count > daily_limit and fsrs_rating >= Rating.Good:
            shift = random.choice([-1, 1])
            next_due = next_due + datetime.timedelta(days=shift)

        # 7. Update Progress
        is_correct = fsrs_rating >= Rating.Good
        progress.fsrs_state = new_card.state
        progress.fsrs_stability = new_card.stability
        progress.fsrs_difficulty = new_card.difficulty
        progress.current_interval = float(new_card.scheduled_days)
        progress.interval = int(new_card.scheduled_days * 1440) # Legacy support
        progress.repetitions = new_card.reps
        progress.lapses = new_card.lapses
        progress.fsrs_due = next_due
        progress.fsrs_last_review = now
        progress.last_review_duration = duration_ms
        
        progress.correct_streak = (progress.correct_streak or 0) + 1 if is_correct else 0
        progress.incorrect_streak = (progress.incorrect_streak or 0) + 1 if not is_correct else 0
        
        if is_correct: progress.times_correct = (progress.times_correct or 0) + 1
        else: progress.times_incorrect = (progress.times_incorrect or 0) + 1

        # 8. Log Review
        log_entry = ReviewLog(
            user_id=user_id, item_id=item_id, timestamp=now, rating=fsrs_rating,
            scheduled_days=new_card.scheduled_days, elapsed_days=log_info.get('days_elapsed', 0.0),
            review_duration=duration_ms, state=card_dto.state,
            fsrs_stability=new_card.stability, fsrs_difficulty=new_card.difficulty,
            review_type=mode, is_correct=is_correct, container_id=container_id
        )
        db.session.add(log_entry)
        
        # 9. Return Result
        srs_result = SrsResultDTO(
            next_review=next_due,
            interval_minutes=progress.interval,
            state=new_card.state,
            stability=new_card.stability,
            difficulty=new_card.difficulty,
            retrievability=engine.get_realtime_retention(new_card, now),
            correct_streak=progress.correct_streak,
            incorrect_streak=progress.incorrect_streak,
            score_points=0, # Will be filled by Scoring module
            score_breakdown={},
            repetitions=new_card.reps,
            lapses=new_card.lapses
        )
        
        return progress, srs_result

    @staticmethod
    def get_retrievability(progress: LearningProgress) -> float:
        if not progress or not progress.fsrs_stability or progress.fsrs_stability <= 0:
            return 1.0
        
        now = datetime.datetime.now(datetime.timezone.utc)
        last_review = progress.fsrs_last_review
        if not last_review: return 1.0
        
        if last_review.tzinfo is None:
            last_review = last_review.replace(tzinfo=datetime.timezone.utc)
        
        elapsed_days = (now - last_review).total_seconds() / 86400.0
        if elapsed_days <= 0: return 1.0
        
        try:
            return 0.9 ** (elapsed_days / progress.fsrs_stability)
        except:
            return 0.0
