# File: mindstack_app/modules/fsrs/engine/processor.py
from __future__ import annotations
import datetime
import random
from typing import Optional, Tuple, Dict, Any
from flask import current_app
from sqlalchemy import func
from mindstack_app.models import db
from mindstack_app.modules.fsrs.models import ItemMemoryState
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
    def _normalize_rating(quality: int) -> int:
        """Map generic quality (1-4) to FSRS Rating."""
        if quality <= 1: return Rating.Again
        if quality == 2: return Rating.Hard
        if quality == 3: return Rating.Good
        return Rating.Easy

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
    ) -> Tuple[ItemMemoryState, SrsResultDTO]:
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
        
        # 2. Fetch/Create Progress (Unified Item Memory)
        state_record = ItemMemoryState.query.filter_by(
            user_id=user_id, item_id=item_id
        ).first()
        
        if not state_record:
            state_record = ItemMemoryState(
                user_id=user_id, item_id=item_id,
                state=CardStateEnum.NEW, stability=0.0, difficulty=5.0,
                repetitions=0, streak=0, lapses=0
            )
            db.session.add(state_record)
            db.session.flush()

        # 3. Build CardState
        last_review = state_record.last_review
        if last_review and last_review.tzinfo is None:
            last_review = last_review.replace(tzinfo=datetime.timezone.utc)
            
        # Calculate current_interval (scheduled_days) from stability/last_review if not stored explicitly?
        # FSRS formula: interval = (due - last_review).days approximately
        # Or better, just pass 0.0 if new.
        # We don't store current_interval explicitly in ItemMemoryState?
        # LearningProgress had it. I should use (due_date - last_review) or 0.
        current_ivl = 0.0
        if state_record.due_date and last_review:
             delta = (state_record.due_date.replace(tzinfo=datetime.timezone.utc) - last_review)
             current_ivl = max(0.0, delta.total_seconds() / 86400.0)

        card_dto = CardStateDTO(
            stability=state_record.stability or 0.0,
            difficulty=state_record.difficulty or 0.0,
            reps=state_record.repetitions or 0,
            lapses=state_record.lapses or 0,
            state=state_record.state if state_record.state is not None else CardStateEnum.NEW,
            last_review=last_review,
            scheduled_days=current_ivl
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
        due_on_date_count = ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            func.date(ItemMemoryState.due_date) == next_due.date().isoformat()
        ).count()
        
        if due_on_date_count > daily_limit and fsrs_rating >= Rating.Good:
            shift = random.choice([-1, 1])
            next_due = next_due + datetime.timedelta(days=shift)

        # 7. Update Progress
        is_correct = fsrs_rating >= Rating.Good
        
        state_record.state = new_card.state
        state_record.stability = new_card.stability
        state_record.difficulty = new_card.difficulty
        # current_interval logic handled by due_date
        state_record.repetitions = new_card.reps
        state_record.lapses = new_card.lapses
        state_record.due_date = next_due
        state_record.last_review = now
        
        state_record.streak = (state_record.streak or 0) + 1 if is_correct else 0
        state_record.incorrect_streak = (state_record.incorrect_streak or 0) + 1 if not is_correct else 0
        
        if is_correct:
            state_record.times_correct = (state_record.times_correct or 0) + 1
        else:
            state_record.times_incorrect = (state_record.times_incorrect or 0) + 1
        
        # 8. Log Review - DELEGATED to HistoryRecorder (via caller)
        
        # 9. Return Result
        interval_mins = int(new_card.scheduled_days * 1440)
        
        srs_result = SrsResultDTO(
            next_review=next_due,
            interval_minutes=interval_mins,
            state=new_card.state,
            stability=new_card.stability,
            difficulty=new_card.difficulty,
            retrievability=engine.get_realtime_retention(new_card, now),
            correct_streak=state_record.streak,
            incorrect_streak=0, # Not tracked in ItemMemoryState, assume 0 or derived
            score_points=0,
            score_breakdown={},
            repetitions=new_card.reps,
            lapses=new_card.lapses
        )
        
        return state_record, srs_result

    @staticmethod
    def get_retrievability(state: ItemMemoryState) -> float:
        if not state or not state.stability or state.stability <= 0:
            return 1.0
        
        now = datetime.datetime.now(datetime.timezone.utc)
        last_review = state.last_review
        if not last_review: return 1.0
        
        if last_review.tzinfo is None:
            last_review = last_review.replace(tzinfo=datetime.timezone.utc)
        
        elapsed_days = (now - last_review).total_seconds() / 86400.0
        if elapsed_days <= 0: return 1.0
        
        try:
            return 0.9 ** (elapsed_days / state.stability)
        except:
            return 0.0