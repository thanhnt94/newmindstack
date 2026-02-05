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
        from mindstack_app.modules.fsrs.engine.core import FSRSEngine
        from datetime import datetime, timezone
        
        if not state.last_review:
            return 0.0
            
        dto = SchedulerService._model_to_dto(state)
        engine = FSRSEngine() 
        return engine.get_realtime_retention(dto, datetime.now(timezone.utc))

    @staticmethod
    def predict_next_intervals(user_id: int, item_id: int) -> Dict[int, str]:
        """Predict next intervals for an item."""
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
    def get_due_counts(user_id: int) -> Dict[str, int]:
        """Get count of due items per type for a user."""
        from mindstack_app.modules.fsrs.services.scheduler_service import SchedulerService
        return SchedulerService.get_due_counts(user_id)

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
        """Get global FSRS statistics for a user."""
        from datetime import datetime, timezone
        from sqlalchemy import func
        from mindstack_app.core.extensions import db
        
        now = datetime.now(timezone.utc)
        
        total_cards = ItemMemoryState.query.filter(ItemMemoryState.user_id == user_id).count()
        due_count = ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.due_date <= now
        ).count()
        mastered_count = ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.stability >= 21.0
        ).count()
        
        avg_stats = db.session.query(
            func.avg(ItemMemoryState.stability).label('avg_stability')
        ).filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.state != 0
        ).first()
        
        avg_stability = round(avg_stats.avg_stability or 0.0, 2)
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
        """Get FSRS statistics for a specific container."""
        from datetime import datetime, timezone
        from sqlalchemy import func
        from mindstack_app.core.extensions import db
        from mindstack_app.models import LearningItem
        
        now = datetime.now(timezone.utc)
        
        item_ids = db.session.query(LearningItem.item_id).filter(
            LearningItem.container_id == container_id
        ).subquery()
        
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
            'learned': total,
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
        from sqlalchemy.orm.attributes import flag_modified
        
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
        
        data = dict(state_record.data) if state_record.data else {}
        data['note'] = note_content
        state_record.data = data
        
        flag_modified(state_record, 'data')
        
        db.session.commit()
        return True

    @staticmethod
    def get_memory_stats_by_type(user_id: int, item_type: str) -> Dict[str, Any]:
        """
        Get detailed memory statistics for items of a specific type.
        (Refactored from LearningMetricsService)
        """
        from sqlalchemy import func, case
        from mindstack_app.core.extensions import db
        from mindstack_app.models import LearningItem
        from datetime import datetime, timezone

        # Mastery threshold differs by type
        mastery_threshold = 5.0 if item_type == 'QUIZ_MCQ' else 21.0

        stats = (
            db.session.query(
                func.count(ItemMemoryState.state_id).label('total'),
                func.sum(case((ItemMemoryState.stability >= mastery_threshold, 1), else_=0)).label('mastered'),
                func.sum(case((ItemMemoryState.state.in_([1, 3]), 1), else_=0)).label('learning'),
                func.sum(case((ItemMemoryState.state == 0, 1), else_=0)).label('new'),
                func.sum(case((ItemMemoryState.difficulty >= 8.0, 1), else_=0)).label('hard'),
                func.sum(case((ItemMemoryState.state == 2, 1), else_=0)).label('reviewing'),
                func.sum(case((ItemMemoryState.due_date <= func.now(), 1), else_=0)).label('due'),
                func.sum(ItemMemoryState.times_correct).label('correct'),
                func.sum(ItemMemoryState.times_incorrect).label('incorrect'),
                func.avg(ItemMemoryState.streak).label('avg_streak'),
                func.max(ItemMemoryState.streak).label('best_streak'),
                func.avg(case((ItemMemoryState.state != 0, ItemMemoryState.stability), else_=None)).label('avg_stability'),
            )
            .join(LearningItem, LearningItem.item_id == ItemMemoryState.item_id)
            .filter(
                ItemMemoryState.user_id == user_id,
                LearningItem.item_type == item_type
            )
            .one()
        )

        # Average Retention Calculation
        # For Flashcards, we calculate this precisely if possible, or use stability approx
        # For simplicity and performance, we can do the manual calculation here as strictly requested by user "move logic"
        
        avg_retention = 0.0
        if item_type == 'FLASHCARD':
            active_items = (
                db.session.query(ItemMemoryState.stability, ItemMemoryState.last_review)
                .join(LearningItem, LearningItem.item_id == ItemMemoryState.item_id)
                .filter(
                    ItemMemoryState.user_id == user_id,
                    LearningItem.item_type == 'FLASHCARD',
                    ItemMemoryState.state != 0,
                    ItemMemoryState.stability > 0
                )
                .all()
            )
            
            total_retention = 0.0
            count = 0
            now = datetime.now(timezone.utc)
            
            for stability, last_review in active_items:
                if not stability or not last_review: continue
                if last_review.tzinfo is None:
                    last_review = last_review.replace(tzinfo=timezone.utc)
                
                elapsed_days = max(0, (now - last_review).total_seconds() / 86400.0)
                retention = 0.9 ** (elapsed_days / stability)
                total_retention += retention
                count += 1
            
            avg_retention = (total_retention / count) if count > 0 else 0.0

        return {
            'total': int(stats.total or 0),
            'mastered': int(stats.mastered or 0),
            'learning': int(stats.learning or 0),
            'new': int(stats.new or 0),
            'hard': int(stats.hard or 0),
            'reviewing': int(stats.reviewing or 0),
            'due': int(stats.due or 0),
            'correct': int(stats.correct or 0),
            'incorrect': int(stats.incorrect or 0),
            'avg_streak': float(stats.avg_streak or 0),
            'best_streak': int(stats.best_streak or 0),
            'avg_stability': float(stats.avg_stability or 0),
            'avg_retention': avg_retention
        }

    @staticmethod
    def get_course_memory_stats(user_id: int) -> Dict[str, Any]:
        """
        Get aggregated memory/progress stats for courses/lessons.
        """
        from sqlalchemy import func, case
        from mindstack_app.core.extensions import db
        from mindstack_app.models import LearningItem
        
        # We need to cast JSON data field
        completion_pct = db.cast(ItemMemoryState.data['completion_percentage'], db.Integer)
        
        summary = (
            db.session.query(
                func.count(ItemMemoryState.state_id).label('total_lessons'),
                func.sum(case((completion_pct >= 100, 1), else_=0)).label('completed'),
                func.sum(case(((completion_pct > 0) & (completion_pct < 100), 1), else_=0)).label('in_progress'),
                func.avg(completion_pct).label('avg_completion'),
                func.max(ItemMemoryState.last_review).label('last_progress'),
            )
            .join(LearningItem, LearningItem.item_id == ItemMemoryState.item_id)
            .filter(
                ItemMemoryState.user_id == user_id,
                LearningItem.item_type == 'LESSON'
            )
            .one()
        )
        
        return {
            'total_lessons': int(summary.total_lessons or 0),
            'completed': int(summary.completed or 0),
            'in_progress': int(summary.in_progress or 0),
            'avg_completion': float(summary.avg_completion or 0.0),
            'last_progress': summary.last_progress
        }

    @staticmethod
    def get_started_container_count(user_id: int, container_type: str, item_type: str) -> int:
        """
        Count number of containers of a certain type that user has started.
		Started means at least one item inside has a state (ItemMemoryState exists).
        """
        from sqlalchemy import func, distinct
        from mindstack_app.core.extensions import db
        from mindstack_app.models import LearningContainer, LearningItem

        count = (
            db.session.query(func.count(distinct(LearningContainer.container_id)))
            .join(LearningItem, LearningItem.container_id == LearningContainer.container_id)
            .join(ItemMemoryState, ItemMemoryState.item_id == LearningItem.item_id)
            .filter(
                ItemMemoryState.user_id == user_id,
                LearningItem.item_type == item_type,
                LearningContainer.container_type == container_type
            )
            .scalar() or 0
        )
        return count

    @staticmethod
    def get_activity_counts_by_type(user_id: int, start_date) -> Dict[str, int]:
        """
        Get count of items active since start_date, grouped by item_type.
        """
        from collections import defaultdict
        from sqlalchemy import func
        from mindstack_app.core.extensions import db
        from mindstack_app.models import LearningItem
        
        results = (
            db.session.query(
                LearningItem.item_type,
                func.count(ItemMemoryState.state_id)
            )
            .join(LearningItem, LearningItem.item_id == ItemMemoryState.item_id)
            .filter(
                ItemMemoryState.user_id == user_id,
                ItemMemoryState.last_review >= start_date
            )
            .group_by(LearningItem.item_type)
            .all()
        )
        
        counts = defaultdict(int)
        for item_type, count in results:
            counts[item_type] = count
        
        return dict(counts)



