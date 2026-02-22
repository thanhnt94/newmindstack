from typing import Dict, Any, Tuple, Optional
import datetime
import logging
from mindstack_app.core.extensions import db
from mindstack_app.modules.fsrs.models import ItemMemoryState
from mindstack_app.modules.fsrs.engine.core import FSRSEngine
from mindstack_app.modules.fsrs.schemas import CardStateDTO, CardStateEnum, SrsResultDTO
from mindstack_app.modules.fsrs.services.settings_service import FSRSSettingsService
from mindstack_app.modules.fsrs.services.optimizer_service import FSRSOptimizerService
from mindstack_app.modules.fsrs.signals import card_reviewed
from mindstack_app.modules.fsrs.exceptions import CardNotDueError, InvalidRatingError

logger = logging.getLogger(__name__)

class SchedulerService:
    """
    Orchestrator for FSRS scheduling.
    Handles DB interactions, Engine calls, and Signal emission.
    """

    @staticmethod
    def _get_or_create_state(user_id: int, item_id: int) -> ItemMemoryState:
        state = ItemMemoryState.query.filter_by(user_id=user_id, item_id=item_id).first()
        if not state:
            state = ItemMemoryState(user_id=user_id, item_id=item_id)
            state.state = CardStateEnum.NEW
            state.streak = 0
            state.incorrect_streak = 0
            state.times_correct = 0
            state.times_incorrect = 0
            db.session.add(state)
            # Flush to get defaults if needed, but committing is better done at end of transaction
        return state

    @staticmethod
    def _model_to_dto(state: ItemMemoryState) -> CardStateDTO:
        return CardStateDTO(
            stability=state.stability or 0.0,
            difficulty=state.difficulty or 0.0,
            reps=state.repetitions or 0,
            lapses=state.lapses or 0,
            state=state.state or CardStateEnum.NEW,
            last_review=state.last_review,
            due=state.due_date
        )

    @staticmethod
    def process_review(
        user_id: int,
        item_id: int,
        quality: int,
        mode: str = 'flashcard',
        duration_ms: int = 0,
        container_id: int = None,
        only_count: bool = False,
        **kwargs
    ) -> Tuple[ItemMemoryState, SrsResultDTO]:
        """
        Main entry point for processing a review.
        """
        # [MODIFIED] Restrict FSRS updates to Flashcard/Typing only. 
        # MCQ and other modes are treated as practice (count reps, don't reschedule).
        if mode not in ('flashcard', 'typing', 'cram', 'review'):
            only_count = True

        # Validation
        if not (1 <= quality <= 4):
            raise InvalidRatingError(f"Quality must be 1-4, got {quality}")

        # 1. Fetch Data
        item_state = SchedulerService._get_or_create_state(user_id, item_id)
        card_dto = SchedulerService._model_to_dto(item_state)
        
        now = datetime.datetime.utcnow()
        
        if only_count:
            # [FIX] Do NOT update repetitions or last_review for practice modes.
            # Updating last_review would reset Retrievability to 100% (decay since now=0), which is unwanted.
            # Updating repetitions would de-sync FSRS parameters.
            # We ONLY update separate counters (mcq_reps) later in this function.
            
            # Prepare dummy result for DTO
            retrievability = 0.0
            try:
                effective_weights = FSRSOptimizerService.get_user_parameters(user_id)
                desired_retention = float(FSRSSettingsService.get('FSRS_DESIRED_RETENTION', 0.9))
                engine = FSRSEngine(custom_weights=effective_weights, desired_retention=desired_retention)
                card_for_r = SchedulerService._model_to_dto(item_state)
                # This returns CURRENT retention based on PREVIOUS last_review (correct decay)
                retrievability = engine.get_realtime_retention(card_for_r, now)
            except: pass
            
            srs_result_state = item_state.state
            srs_result_stability = item_state.stability
            srs_result_difficulty = item_state.difficulty
            srs_result_next_due = item_state.due_date or now
        else:
            # 2. Get Configuration & Parameters
            effective_weights = FSRSOptimizerService.get_user_parameters(user_id)
            desired_retention = float(FSRSSettingsService.get('FSRS_DESIRED_RETENTION', 0.9))
            enable_fuzz = bool(FSRSSettingsService.get('FSRS_ENABLE_FUZZING', True))
            
            # 3. Call Engine
            engine = FSRSEngine(custom_weights=effective_weights, desired_retention=desired_retention)
            
            try:
                new_card_state, next_due, log = engine.review_card(
                    card_dto, 
                    rating=quality, 
                    now=now, 
                    enable_fuzz=enable_fuzz
                )
            except Exception as e:
                logger.error(f"Engine calculation failed for user {user_id} item {item_id}: {e}")
                raise e

            # 4. Update DB Model
            item_state.stability = new_card_state.stability
            item_state.difficulty = new_card_state.difficulty
            item_state.state = new_card_state.state
            item_state.due_date = next_due
            item_state.last_review = now
            item_state.repetitions = new_card_state.reps
            item_state.lapses = new_card_state.lapses
            
            srs_result_state = new_card_state.state
            srs_result_stability = new_card_state.stability
            srs_result_difficulty = new_card_state.difficulty
            srs_result_next_due = next_due
            retrievability = engine.get_realtime_retention(new_card_state, now)
        
        # Update metrics (Always update streaks and correct counts)
        if quality >= 3:
            item_state.streak = (item_state.streak or 0) + 1
            item_state.incorrect_streak = 0
            item_state.times_correct = (item_state.times_correct or 0) + 1
        else:
            item_state.streak = 0
            item_state.incorrect_streak = (item_state.incorrect_streak or 0) + 1
            item_state.times_incorrect = (item_state.times_incorrect or 0) + 1
            
        # [NEW] Track mode-specific repetitions in data field
        if not item_state.data:
            item_state.data = {}
            
        current_data = dict(item_state.data) 
        if mode == 'mcq':
            current_data['mcq_reps'] = current_data.get('mcq_reps', 0) + 1
        elif mode == 'typing':
            current_data['typing_reps'] = current_data.get('typing_reps', 0) + 1
            
        item_state.data = current_data
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(item_state, 'data')
            
        # 5. Commit
        try:
            db.session.add(item_state)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
        
        # 6. Prepare Result & Emit Signal
        srs_result = SrsResultDTO(
            next_review=srs_result_next_due,
            interval_minutes=0, # Not strictly needed for DTO here
            retrievability=retrievability,
            state=srs_result_state,
            stability=srs_result_stability,
            difficulty=srs_result_difficulty,
            correct_streak=item_state.streak,
            incorrect_streak=item_state.incorrect_streak,
            repetitions=item_state.repetitions,
            lapses=item_state.lapses,
            score_points=0,
            score_breakdown={},
            mcq_reps=item_state.data.get('mcq_reps', 0) if item_state.data else 0,
            typing_reps=item_state.data.get('typing_reps', 0) if item_state.data else 0
        )
        
        card_reviewed.send(
            SchedulerService,
            user_id=user_id,
            item_id=item_id,
            rating=quality,
            new_state=item_state.to_dict()
        )
        
        return item_state, srs_result

    @staticmethod
    def get_preview_intervals(user_id: int, item_id: int) -> Dict[str, Dict[str, Any]]:
        """
        Get preview intervals for all ratings (1-4).
        """
        # Safe fallback values
        FALLBACK = {
            str(r): {'interval': 'N/A', 'stability': 0, 'difficulty': 0, 'retrievability': 0}
            for r in range(1, 5)
        }
        
        try:
            item_state = ItemMemoryState.query.filter_by(user_id=user_id, item_id=item_id).first()
            if not item_state:
                # Treat as new card
                card_dto = CardStateDTO(state=CardStateEnum.NEW)
            else:
                card_dto = SchedulerService._model_to_dto(item_state)
                # Recalculate scheduled_days based on due date vs last review if available
                # This logic was in the interface, preserving it here logic-wise
                if item_state.due_date and item_state.last_review:
                     # Calculate gap
                     pass 

            effective_weights = FSRSOptimizerService.get_user_parameters(user_id)
            desired_retention = float(FSRSSettingsService.get('FSRS_DESIRED_RETENTION', 0.9))
            engine = FSRSEngine(custom_weights=effective_weights, desired_retention=desired_retention)
            
            now = datetime.datetime.utcnow()
            previews = {}
            
            for rating in [1, 2, 3, 4]:
                try:
                    new_card, _, _ = engine.review_card(card_dto, rating, now, enable_fuzz=False)
                    
                    # Format interval string
                    days = new_card.scheduled_days
                    if days < 1.0:
                        ivl_str = f"{round(days * 1440)}m"
                    elif days >= 30.0:
                        ivl_str = f"{round(days/30.0, 1)}mo"
                    else:
                        ivl_str = f"{round(days, 1)}d"

                    previews[str(rating)] = {
                        'interval': ivl_str,
                        'stability': round(new_card.stability, 2),
                        'difficulty': round(new_card.difficulty, 2),
                        'retrievability': round(engine.get_realtime_retention(new_card, now) * 100, 1)
                    }
                except Exception:
                    previews[str(rating)] = FALLBACK[str(rating)]
            
            return previews
            
        except Exception as e:
            logger.error(f"FSRS get_preview_intervals failed for user={user_id}, item={item_id}: {e}")
            return FALLBACK
    @staticmethod
    def get_due_counts(user_id: int) -> Dict[str, int]:
        """
        Get count of due items per type for a user.
        """
        from mindstack_app.models import LearningItem
        from sqlalchemy import func
        
        # [FIX] SQLite stores naive datetimes — must compare with naive UTC
        now = datetime.datetime.utcnow()
        
        results = (
            db.session.query(
                LearningItem.item_type,
                func.count(ItemMemoryState.state_id)
            )
            .join(LearningItem, LearningItem.item_id == ItemMemoryState.item_id)
            .filter(
                ItemMemoryState.user_id == user_id,
                ItemMemoryState.due_date <= now
            )
            .group_by(LearningItem.item_type)
            .all()
        )
        
        counts = {'flashcard': 0, 'quiz': 0}
        for type_code, count in results:
             # standardize keys
            if type_code == 'FLASHCARD': counts['flashcard'] = count
            elif type_code == 'QUIZ_MCQ': counts['quiz'] = count
            
        return counts
