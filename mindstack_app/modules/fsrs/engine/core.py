from __future__ import annotations
import datetime
import logging
from typing import Optional, Tuple, Dict, Any, List
from fsrs_rs_python import FSRS, DEFAULT_PARAMETERS
from ..schemas import Rating, CardStateEnum, CardStateDTO

logger = logging.getLogger(__name__)

class FSRSEngine:
    """
    Standard FSRS-5 Engine using fsrs-rs-python.
    Pure Logic Layer: No Database, No Flask Context.
    """
    
    def __init__(self, custom_weights: Optional[List[float]] = None, desired_retention: float = 0.9):
        params = custom_weights if custom_weights else list(DEFAULT_PARAMETERS)
        self.fsrs = FSRS(parameters=params)
        self.desired_retention = desired_retention

    def _to_memory_state(self, state: CardStateDTO):
        if state.state == CardStateEnum.NEW or (state.stability <= 0 and state.reps == 0):
            return None
        
        from fsrs_rs_python import MemoryState
        return MemoryState(
            stability=max(0.1, float(state.stability)),
            difficulty=max(1.0, min(10.0, float(state.difficulty)))
        )

    def _from_next_state(self, item_state, card_state: CardStateDTO, rating: int) -> CardStateDTO:
        memory = item_state.memory
        interval = float(item_state.interval)
        
        GRADUATION_THRESHOLD_DAYS = 1.0
        if interval >= GRADUATION_THRESHOLD_DAYS:
            new_state = CardStateEnum.REVIEW
        else:
            if rating == Rating.Again:
                if card_state.state == CardStateEnum.REVIEW:
                    new_state = CardStateEnum.RELEARNING
                elif card_state.state == CardStateEnum.RELEARNING:
                    new_state = CardStateEnum.RELEARNING
                else:
                    new_state = CardStateEnum.LEARNING
            else:
                if card_state.state == CardStateEnum.RELEARNING:
                    new_state = CardStateEnum.RELEARNING
                elif card_state.state == CardStateEnum.REVIEW:
                    new_state = CardStateEnum.REVIEW
                else:
                    new_state = CardStateEnum.LEARNING
        
        new_lapses = card_state.lapses
        if rating == Rating.Again and card_state.state == CardStateEnum.REVIEW:
            new_lapses += 1
        
        return CardStateDTO(
            stability=memory.stability,
            difficulty=memory.difficulty,
            elapsed_days=0.0,
            scheduled_days=interval,
            reps=card_state.reps + 1,
            lapses=new_lapses,
            state=new_state,
            last_review=card_state.last_review,
            due=card_state.due
        )

    def get_realtime_retention(self, card_state: CardStateDTO, now: datetime.datetime) -> float:
        """Calculate current retention probability."""
        # A NEW card always has 0 retrievability until first review
        if card_state.state == CardStateEnum.NEW:
            return 0.0

        # If we have no stability, it's effectively 100% if seen once, or 0% if new
        if card_state.stability <= 0:
            return 1.0 if card_state.reps > 0 else 0.0

        if not card_state.last_review:
            # If no last review, we can't calculate decay. 
            # If it's not NEW, assume it was just seen to avoid 0% shock.
            return 1.0
            
        last_review = card_state.last_review
        if last_review.tzinfo is None:
            last_review = last_review.replace(tzinfo=datetime.timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=datetime.timezone.utc)
            
        elapsed = (now - last_review).total_seconds() / 86400.0
        if elapsed <= 0:
            return 1.0
            
        try:
            return 0.9 ** (elapsed / card_state.stability)
        except (ZeroDivisionError, OverflowError):
            return 0.0

    def review_card(self, card_state: CardStateDTO, rating: int, now: Optional[datetime.datetime] = None, enable_fuzz: bool = False) -> Tuple[CardStateDTO, datetime.datetime, Dict[str, Any]]:
        """
        Process a review and return the new state, next due date, and log data.
        """
        if now is None:
            now = datetime.datetime.utcnow()
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)

        fsrs_rating = max(1, min(4, rating))
        memory_state = self._to_memory_state(card_state)
        
        if card_state.last_review:
            last_review = card_state.last_review
            if last_review.tzinfo is not None:
                last_review = last_review.replace(tzinfo=None)
            days_elapsed = (now - last_review).total_seconds() / 86400.0
        else:
            days_elapsed = 0.0
        
        days_elapsed_rounded = max(0, round(days_elapsed))
        
        try:
            next_states = self.fsrs.next_states(
                memory_state,
                self.desired_retention,
                days_elapsed_rounded
            )
        except Exception as e:
            logger.error(f"[FSRS ENGINE] next_states error: {e}")
            raise e
        
        rating_map = {
            Rating.Again: next_states.again,
            Rating.Hard: next_states.hard,
            Rating.Good: next_states.good,
            Rating.Easy: next_states.easy
        }
        selected_state = rating_map[fsrs_rating]
        raw_interval = float(selected_state.interval)
        
        # Apply Caps
        FLOOR_DAYS = 20.0 / 1440.0 # 20 minutes
        CEILING_DAYS = 365.0
        final_interval = max(FLOOR_DAYS, min(CEILING_DAYS, raw_interval))
            
        new_card_state = self._from_next_state(selected_state, card_state, fsrs_rating)
        
        fuzzed_interval = final_interval
        if enable_fuzz and final_interval > 3.0:
             import random as py_random
             fuzz_factor = py_random.uniform(0.95, 1.05)
             fuzzed_interval = max(3.0, final_interval * fuzz_factor)
        
        new_card_state.scheduled_days = fuzzed_interval
        new_card_state.last_review = now
        new_card_state.due = now + datetime.timedelta(days=fuzzed_interval)
        
        log = {
            "rating": fsrs_rating,
            "days_elapsed": days_elapsed,
            "scheduled_days": fuzzed_interval,
            "start_state": card_state.state,
            "end_state": new_card_state.state,
            "original_interval": final_interval
        }
        
        return new_card_state, new_card_state.due, log

    def predict_next_intervals(self, card_state: CardStateDTO) -> Dict[int, str]:
        """
        Predict next intervals for all 4 ratings without updating state.
        Returns a dict mapping Rating -> Display String (e.g. '1d').
        """
        memory_state = self._to_memory_state(card_state)
        now = datetime.datetime.utcnow()
        
        if card_state.last_review:
            last_review = card_state.last_review
            if last_review.tzinfo is not None:
                last_review = last_review.replace(tzinfo=None)
            days_elapsed = (now - last_review).total_seconds() / 86400.0
        else:
            days_elapsed = 0.0
            
        days_elapsed_rounded = max(0, round(days_elapsed))
        next_states = self.fsrs.next_states(
            memory_state,
            self.desired_retention,
            days_elapsed_rounded
        )
        
        def _fmt_ivl(days):
            days = float(days)
            if days < 1.0:
                mins = round(days * 1440)
                return f"{mins}m"
            if days >= 30.0:
                return f"{round(days/30.0, 1)}mo"
            return f"{round(days, 1)}d"

        return {
            Rating.Again: _fmt_ivl(next_states.again.interval),
            Rating.Hard: _fmt_ivl(next_states.hard.interval),
            Rating.Good: _fmt_ivl(next_states.good.interval),
            Rating.Easy: _fmt_ivl(next_states.easy.interval)
        }
