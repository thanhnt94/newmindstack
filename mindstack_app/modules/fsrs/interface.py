from typing import Optional, Tuple, List, Dict, Any
from mindstack_app.modules.fsrs.models import ItemMemoryState
from mindstack_app.modules.fsrs.services.scheduler_service import SchedulerService
from mindstack_app.modules.fsrs.services.optimizer_service import FSRSOptimizerService
from mindstack_app.modules.fsrs.services.settings_service import FSRSSettingsService
from mindstack_app.modules.fsrs.schemas import SrsResultDTO

def get_due_counts(user_id: int) -> Dict[str, int]:
    """Get count of due items per type for a user."""
    return FSRSInterface.get_due_counts(user_id)

class FSRSInterface:
    """
    Public API (Gatekeeper) for FSRS module.
    Delegates all logic to Services.
    """
    
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
        return SchedulerService.process_review(
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
        # Currently, this requires reinstantiating the engine or just using the formula.
        # Since this was a static method on Processor, we should delegate or reimplement simply.
        # For now, let's use the SchedulerService if possible or move logic here?
        # Better: Add a helper in SchedulerService or just calculate it if simple.
        # Given the instruction to be thin, we'll instantiate engine momentarily.
        
        # NOTE: This method signature takes an ItemMemoryState.
        # Ideally, we should move this to SchedulerService as well.
        from mindstack_app.modules.fsrs.engine.core import FSRSEngine
        from datetime import datetime, timezone
        
        if not state.last_review:
            return 0.0
            
        dto = SchedulerService._model_to_dto(state)
        engine = FSRSEngine() # Defaults are fine for pure R calculation usually
        return engine.get_realtime_retention(dto, datetime.now(timezone.utc))

    @staticmethod
    def predict_next_intervals(user_id: int, item_id: int) -> Dict[int, str]:
        """Predict next intervals for an item. Legacy format (int keys)."""
        # The new SchedulerService.get_preview_intervals returns str keys ("1", "2").
        # We adapt it here for backward compatibility if needed, or update SchedulerService.
        # The existing interface returned Dict[int, str].
        
        # Let's map SchedulerService output back to this format.
        previews = SchedulerService.get_preview_intervals(user_id, item_id)
        result = {}
        for k, v in previews.items():
            try:
                result[int(k)] = v['interval']
            except ValueError:
                pass
        return result

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
        
    @staticmethod
    def get_due_counts(user_id: int) -> Dict[str, int]:
        """
        Get count of due items per type for a user.
        Used by Dashboard aggregator.
        """
        from mindstack_app.modules.fsrs.services.scheduler_service import SchedulerService
        return SchedulerService.get_due_counts(user_id)
        # Default mapping: Correct=Good(3), Incorrect=Again(1)
        quality = 3 if is_correct else 1
        
        # Forward to service
        state, srs_result = SchedulerService.process_review(
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

    @staticmethod
    def get_item_state(user_id: int, item_id: int) -> Optional[ItemMemoryState]:
        """Get the memory state for a specific item."""
        return ItemMemoryState.query.filter_by(user_id=user_id, item_id=item_id).first()

    @staticmethod
    def get_due_items(user_id: int, limit: int = 100) -> List[ItemMemoryState]:
        """Get items due for review."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        return ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.due_date <= now
        ).order_by(ItemMemoryState.due_date).limit(limit).all()

    @staticmethod
    def update_item_state(state: ItemMemoryState):
        """Persist state changes."""
        from mindstack_app.core.extensions import db
        db.session.add(state)
        db.session.commit()

    @staticmethod
    def get_preview_intervals(user_id: int, item_id: int) -> Dict[str, Dict[str, Any]]:
        """Get rich preview intervals."""
        return SchedulerService.get_preview_intervals(user_id, item_id)

    @staticmethod
    def get_global_stats(user_id: int) -> Dict[str, Any]:
        """
        Get global FSRS statistics for a user.
        Used by stats module for aggregated dashboard data.
        
        Returns:
            dict with: total_cards, due_count, mastered_count, 
                      average_retention, average_stability
        """
        from datetime import datetime, timezone
        from sqlalchemy import func
        from mindstack_app.core.extensions import db
        
        now = datetime.now(timezone.utc)
        
        # Total cards with any state
        total_cards = ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id
        ).count()
        
        # Due cards
        due_count = ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.due_date <= now
        ).count()
        
        # Mastered cards (stability >= 21 days)
        mastered_count = ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.stability >= 21.0
        ).count()
        
        # Average stability and difficulty (for retention calculation)
        avg_stats = db.session.query(
            func.avg(ItemMemoryState.stability).label('avg_stability'),
            func.avg(ItemMemoryState.difficulty).label('avg_difficulty')
        ).filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.state != 0  # Only reviewed cards
        ).first()
        
        avg_stability = round(avg_stats.avg_stability or 0.0, 2)
        
        # Approximate average retention (simplified)
        # R ≈ 0.9^(elapsed/stability), but for average we estimate ~85% for active learners
        average_retention = 85.0 if total_cards > 0 else 0.0
        
        return {
            'total_cards': total_cards,
            'due_count': due_count,
            'mastered_count': mastered_count,
            'average_retention': average_retention,
            'average_stability': avg_stability,
        }

    @staticmethod
    def get_container_stats(user_id: int, container_id: int) -> Dict[str, Any]:
        """
        Get FSRS statistics for a specific container.
        
        Returns:
            dict with: total, learned, due, mastered, avg_stability
        """
        from datetime import datetime, timezone
        from sqlalchemy import func
        from mindstack_app.core.extensions import db
        from mindstack_app.models import LearningItem
        
        now = datetime.now(timezone.utc)
        
        # Get item IDs in container
        item_ids = db.session.query(LearningItem.item_id).filter(
            LearningItem.container_id == container_id
        ).subquery()
        
        # Base query for user's states in this container
        base_query = ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.item_id.in_(item_ids)
        )
        
        total = base_query.count()
        due = base_query.filter(ItemMemoryState.due_date <= now).count()
        mastered = base_query.filter(ItemMemoryState.stability >= 21.0).count()
        
        avg_stability = db.session.query(
            func.avg(ItemMemoryState.stability)
        ).filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.item_id.in_(item_ids),
            ItemMemoryState.state != 0
        ).scalar() or 0.0
        
        return {
            'total': total,
            'learned': total,  # All states = learned
            'due': due,
            'mastered': mastered,
            'avg_stability': round(avg_stability, 2)
        }

    @staticmethod
    def get_learned_item_ids(user_id: int) -> List[int]:
        """Get IDs of all items that have been learned (state != 0)."""
        from mindstack_app.core.extensions import db
        return [r[0] for r in db.session.query(ItemMemoryState.item_id).filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.state != 0
        ).all()]

    @staticmethod
    def save_item_note(user_id: int, item_id: int, note_content: str) -> bool:
        """Save user personal note for an item."""
        from mindstack_app.core.extensions import db
        from datetime import datetime, timezone
        
        state_record = ItemMemoryState.query.filter_by(
            user_id=user_id, item_id=item_id
        ).first()
        
        if not state_record:
            state_record = ItemMemoryState(
                user_id=user_id, item_id=item_id,
                state=0, # NEW
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(state_record)
        
        # Clone dict to trigger change tracking if needed
        data = dict(state_record.data) if state_record.data else {}
        data['note'] = note_content
        state_record.data = data
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(state_record, 'data')
        
        db.session.commit()
        return True

