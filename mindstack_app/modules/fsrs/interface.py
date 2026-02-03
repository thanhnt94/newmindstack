# File: mindstack_app/modules/fsrs/interface.py
from typing import Optional, Tuple, List, Dict, Any
import datetime
from sqlalchemy import func
from mindstack_app.models import db
from mindstack_app.modules.fsrs.models import ItemMemoryState
from .engine.processor import FSRSProcessor
from .services.settings_service import FSRSSettingsService
from mindstack_app.modules.fsrs.services.optimizer_service import FSRSOptimizerService
from .schemas import SrsResultDTO, CardStateDTO

class FSRSInterface:
    """Public API for FSRS module."""
    
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
        """Process a learning interaction and return updated state and result."""
        return FSRSProcessor.process_review(
            user_id=user_id,
            item_id=item_id,
            quality=quality,
            mode=mode,
            duration_ms=duration_ms,
            container_id=container_id,
            **kwargs
        )

    # Legacy alias
    process_answer = process_review

    @staticmethod
    def get_retrievability(state: ItemMemoryState) -> float:
        """Calculate current retrievability (memory power)."""
        return FSRSProcessor.get_retrievability(state)

    @staticmethod
    def predict_next_intervals(user_id: int, item_id: int) -> Dict[int, str]:
        """Predict next intervals for an item."""
        state_record = ItemMemoryState.query.filter_by(user_id=user_id, item_id=item_id).first()
        
        # Build CardStateDTO from model
        from .schemas import CardStateDTO, CardStateEnum
        from .services.settings_service import FSRSSettingsService
        from .logics.fsrs_engine import FSRSEngine
        
        if not state_record:
            card_dto = CardStateDTO(state=CardStateEnum.NEW)
        else:
            card_dto = CardStateDTO(
                stability=state_record.stability or 0.0,
                difficulty=state_record.difficulty or 0.0,
                reps=state_record.repetitions or 0,
                lapses=state_record.lapses or 0,
                state=state_record.state or CardStateEnum.NEW,
                last_review=state_record.last_review
            )
            
        effective_weights = FSRSOptimizerService.get_user_parameters(user_id)
        desired_retention = float(FSRSSettingsService.get('FSRS_DESIRED_RETENTION', 0.9))
        
        engine = FSRSEngine(custom_weights=effective_weights, desired_retention=desired_retention)
        return engine.predict_next_intervals(card_dto)

    @staticmethod
    def train_user_parameters(user_id: int) -> Optional[List[float]]:
        """Train and save optimized parameters for a user."""
        return FSRSOptimizerService.train_for_user(user_id)

    @staticmethod
    def get_config(key: str, default: Any = None) -> Any:
        """Get FSRS configuration."""
        return FSRSSettingsService.get(key, default)

    @staticmethod
    def process_interaction(
        user_id: int,
        item_id: int,
        mode: str,
        result_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        High-level wrapper to process any learning interaction.
        Maps mode-specific result_data to FSRS parameters.
        """
        # Determine quality and duration from result_data
        is_correct = result_data.get('is_correct', False)
        duration_ms = result_data.get('duration_ms', 0)
        
        # Default mapping: Correct=Good(3), Incorrect=Again(1)
        quality = 3 if is_correct else 1
        
        # Forward to processor
        state, srs_result = FSRSInterface.process_review(
            user_id=user_id,
            item_id=item_id,
            quality=quality,
            mode=mode,
            duration_ms=duration_ms,
            **result_data
        )
        
        # Return summary dict for UI
        return {
            'next_review': srs_result.next_review.isoformat() if srs_result.next_review else None,
            'interval_days': round(srs_result.interval_minutes / 1440.0, 2),
            'retrievability': round(srs_result.retrievability * 100, 1),
            'state': srs_result.state
        }

    # === New Phase 2 Methods ===

    @staticmethod
    def get_item_state(user_id: int, item_id: int) -> Optional[ItemMemoryState]:
        """Get the memory state for a specific item."""
        return ItemMemoryState.query.filter_by(user_id=user_id, item_id=item_id).first()

    @staticmethod
    def get_due_items(user_id: int, limit: int = 100) -> List[ItemMemoryState]:
        """Get items due for review."""
        now = datetime.datetime.now(datetime.timezone.utc)
        return ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.due_date <= now
        ).order_by(ItemMemoryState.due_date).limit(limit).all()

    @staticmethod
    def update_item_state(state: ItemMemoryState):
        """Persist state changes."""
        db.session.add(state)
        db.session.commit()

    @staticmethod
    def get_preview_intervals(user_id: int, item_id: int) -> Dict[str, Dict[str, Any]]:
        """
        Get preview intervals for all ratings (1-4).
        
        Returns a dict keyed by rating string with preview data:
        {
            "1": {"interval": "1d", "stability": 0.5, "difficulty": 5.0, "retrievability": 100},
            "2": {"interval": "3d", ...},
            ...
        }
        
        On error, returns safe fallback values.
        """
        import logging
        from datetime import timezone
        from .schemas import CardStateDTO, CardStateEnum
        from .logics.fsrs_engine import FSRSEngine
        
        logger = logging.getLogger(__name__)
        
        # Safe fallback values
        FALLBACK = {
            str(r): {'interval': 'N/A', 'stability': 0, 'difficulty': 0, 'retrievability': 0}
            for r in range(1, 5)
        }
        
        try:
            # Get current state
            state_record = ItemMemoryState.query.filter_by(
                user_id=user_id, item_id=item_id
            ).first()
            
            # Build CardStateDTO
            if not state_record:
                card_dto = CardStateDTO(state=CardStateEnum.NEW)
            else:
                # Calculate scheduled_days from due_date
                scheduled_days = 0.0
                if state_record.due_date and state_record.last_review:
                    try:
                        due = state_record.due_date.replace(tzinfo=timezone.utc)
                        last = state_record.last_review.replace(tzinfo=timezone.utc)
                        scheduled_days = max(0.0, (due - last).total_seconds() / 86400.0)
                    except Exception:
                        pass
                
                card_dto = CardStateDTO(
                    stability=state_record.stability or 0.0,
                    difficulty=state_record.difficulty or 0.0,
                    reps=state_record.repetitions or 0,
                    lapses=state_record.lapses or 0,
                    state=state_record.state or CardStateEnum.NEW,
                    last_review=state_record.last_review,
                    scheduled_days=scheduled_days
                )
            
            # Get user parameters and create engine
            effective_weights = FSRSOptimizerService.get_user_parameters(user_id)
            desired_retention = float(FSRSSettingsService.get('FSRS_DESIRED_RETENTION', 0.9))
            engine = FSRSEngine(custom_weights=effective_weights, desired_retention=desired_retention)
            
            # Calculate preview for each rating
            now = datetime.datetime.now(datetime.timezone.utc)
            previews = {}
            
            for rating in [1, 2, 3, 4]:
                try:
                    new_card, _, _ = engine.review_card(card_dto, rating, now, enable_fuzz=False)
                    previews[str(rating)] = {
                        'interval': f"{round(new_card.scheduled_days, 1)}d",
                        'stability': round(new_card.stability, 2),
                        'difficulty': round(new_card.difficulty, 2),
                        'retrievability': round(engine.get_realtime_retention(new_card, now) * 100, 1)
                    }
                except Exception as e:
                    logger.warning(f"FSRS preview calculation failed for rating {rating}: {e}")
                    previews[str(rating)] = FALLBACK[str(rating)]
            
            return previews
            
        except Exception as e:
            logger.error(f"FSRS get_preview_intervals failed for user={user_id}, item={item_id}: {e}")
            return FALLBACK