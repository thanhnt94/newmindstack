from typing import Optional, Tuple, List, Dict, Any
import datetime
from mindstack_app.modules.fsrs.models import ItemMemoryState
from mindstack_app.modules.fsrs.services.scheduler_service import SchedulerService
from mindstack_app.modules.fsrs.services.optimizer_service import FSRSOptimizerService
from mindstack_app.modules.fsrs.services.settings_service import FSRSSettingsService
from mindstack_app.modules.fsrs.schemas import SrsResultDTO

def get_due_counts(user_id: int) -> Dict[str, int]:
    """Get count of due items per type for a user."""
    return FSRSInterface.get_due_counts(user_id)

from .schemas import Rating, CardStateDTO

class FSRSInterface:
    # Re-export Enums/DTOs for external access
    Rating = Rating
    CardStateDTO = CardStateDTO

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
    def process_interaction(
        user_id: int,
        item_id: int,
        quality: int = 3,
        mode: str = 'mcq',
        only_count: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        High-level wrapper for processing a review interaction.
        Returns a dictionary for easy JSON serialization in routes.
        """
        from dataclasses import asdict
        state, result = SchedulerService.process_review(
            user_id=user_id,
            item_id=item_id,
            quality=quality,
            mode=mode,
            only_count=only_count,
            **kwargs
        )
        # Convert DTO to dict
        res_dict = asdict(result)
        
        # [FIX] Normalize datetimes for JSON serialization
        for key, value in res_dict.items():
            if hasattr(value, 'isoformat'):
                res_dict[key] = value.isoformat()
        
        res_dict['status'] = 'success'
        return res_dict

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
    def get_memory_state(user_id: int, item_id: int) -> Optional[ItemMemoryState]:
        """Alias for get_item_state (per architecture guidelines)."""
        return FSRSInterface.get_item_state(user_id, item_id)
        
    @staticmethod
    def batch_get_memory_states(user_id: int, item_ids: List[int]) -> Dict[int, ItemMemoryState]:
        """
        Get memory states for a list of items.
        Returns a dictionary mapping item_id -> ItemMemoryState.
        """
        if not item_ids: return {}
        
        # SQLite has limit on variables (999 usually). Break into chunks.
        chunk_size = 500
        all_states = []
        import math
        
        print(f" [FSRS] Batch Get U:{user_id} IDs:{len(item_ids)} (Chunked)")
        
        for i in range(0, len(item_ids), chunk_size):
            chunk = item_ids[i:i + chunk_size]
            batch = ItemMemoryState.query.filter(
                ItemMemoryState.user_id == user_id,
                ItemMemoryState.item_id.in_(chunk)
            ).all()
            all_states.extend(batch)
            
        print(f" [FSRS] Batch Get Found Total: {len(all_states)}")
        return {s.item_id: s for s in all_states}
        
    @staticmethod
    def get_memory_states(user_id: int, item_ids: List[int]) -> Dict[int, ItemMemoryState]:
        """Alias for batch_get_memory_states."""
        return FSRSInterface.batch_get_memory_states(user_id, item_ids)

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
        from sqlalchemy import func, select
        from mindstack_app.core.extensions import db
        from mindstack_app.models import LearningItem
        
        now = datetime.now(timezone.utc)
        
        # Use explicit select for IN clause to avoid SAWarning
        item_ids_select = select(LearningItem.item_id).filter(
            LearningItem.container_id == container_id
        )
        
        base_query = ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.item_id.in_(item_ids_select)
        )
        
        total = base_query.count()
        due = base_query.filter(ItemMemoryState.due_date <= now).count()
        mastered = base_query.filter(ItemMemoryState.stability >= 21.0).count()
        
        avg_stability = db.session.query(
            func.avg(ItemMemoryState.stability)
        ).filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.item_id.in_(item_ids_select),
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
    def get_learned_item_ids_for_container(container_id: int, user_id: int) -> List[int]:
        """Get IDs of learned items within a specific container for a user."""
        from mindstack_app.models import LearningItem
        from mindstack_app.core.extensions import db
        return [r[0] for r in db.session.query(ItemMemoryState.item_id).join(
            LearningItem, LearningItem.item_id == ItemMemoryState.item_id
        ).filter(
            LearningItem.container_id == container_id,
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.state != 0
        ).all()]

    @staticmethod
    def get_learned_item_ids(user_id: int) -> List[int]:
        """Get IDs of all items that have been learned (state != 0)."""
        from mindstack_app.core.extensions import db
        return [r[0] for r in db.session.query(ItemMemoryState.item_id).filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.state != 0
        ).all()]

    @staticmethod
    def get_learned_item_ids_for_container(container_id: int, user_id: int) -> List[int]:
        """Get IDs of learned items within a specific container for a user."""
        from mindstack_app.models import LearningItem
        from mindstack_app.core.extensions import db
        return [r[0] for r in db.session.query(ItemMemoryState.item_id).join(
            LearningItem, LearningItem.item_id == ItemMemoryState.item_id
        ).filter(
            LearningItem.container_id == container_id,
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.state != 0
        ).all()]

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
    def toggle_item_marker(user_id: int, item_id: int, marker: str) -> List[str]:
        """Toggle a specific marker (e.g. 'favorite', 'ignored', 'difficult') for an item."""
        from mindstack_app.core.extensions import db
        from datetime import datetime, timezone
        from sqlalchemy.orm.attributes import flag_modified
        
        state_record = ItemMemoryState.query.filter_by(
            user_id=user_id, item_id=item_id
        ).first()
        
        if not state_record:
            state_record = ItemMemoryState(
                user_id=user_id, item_id=item_id,
                state=0,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(state_record)
            
        data = dict(state_record.data) if state_record.data else {}
        markers = data.get('markers', [])
        
        if marker in markers:
            markers.remove(marker)
        else:
            markers.append(marker)
            
        data['markers'] = markers
        state_record.data = data
        
        flag_modified(state_record, 'data')
        db.session.commit()
        
        return markers

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



    @staticmethod
    def get_items_for_practice(user_id: int, mode: str = 'new', limit: int = 10, item_type: str = 'FLASHCARD', container_id: Optional[int] = None) -> List[Any]:
        """
        Get items for practice based on mode.
        Supported modes: 'review', 'mixed', 'hard', 'new'.
        Returns list of LearningItem objects.
        """
        from datetime import datetime, timezone
        from sqlalchemy import func
        from mindstack_app.models import LearningItem, db
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        
        base_query = LearningItem.query.filter(
            LearningItem.item_type == item_type
        )
        
        if container_id:
            base_query = base_query.filter(LearningItem.container_id == container_id)
        
        now = datetime.now(timezone.utc)
        items = []
        
        if mode == 'review':
            items = base_query.join(ItemMemoryState).filter(
                ItemMemoryState.user_id == user_id,
                ItemMemoryState.due_date <= now
            ).order_by(ItemMemoryState.due_date).limit(limit).all()
            
        elif mode == 'mixed':
            items = base_query.join(ItemMemoryState).filter(
                ItemMemoryState.user_id == user_id,
                ItemMemoryState.state != 0
            ).order_by(func.random()).limit(limit).all()
            
        elif mode == 'hard':
            items = base_query.join(ItemMemoryState).filter(
                ItemMemoryState.user_id == user_id,
                ItemMemoryState.difficulty >= 7.5
            ).limit(limit).all()
            
        elif mode == 'new':
            items = base_query.outerjoin(ItemMemoryState, (ItemMemoryState.item_id == LearningItem.item_id) & (ItemMemoryState.user_id == user_id)).filter(
                (ItemMemoryState.state == None) | (ItemMemoryState.state == 0)
            ).limit(limit).all()
            
        elif mode == 'all':
            # Fetch ALL items in container, regardless of state
            # If limit is None, fetch all.
            query = base_query
            if limit:
                query = query.limit(limit)
            items = query.all()
            
        return items

    @staticmethod
    def get_hard_items(user_id: int, limit: int = 10) -> List[Any]:
        """
        Get items classified as 'hard'.
        """
        from mindstack_app.models import LearningItem, db
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        
        return LearningItem.query.join(ItemMemoryState).filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.difficulty >= 7.5
        ).limit(limit).all()

    @staticmethod
    def get_review_aggregated_stats(user_id: int, start_date=None, end_date=None) -> Dict[str, int]:
        """
        Get aggregated review stats for DailyStatsService.
        """
        from sqlalchemy import func, and_, extract, case
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        from mindstack_app.models import db
        
        query = db.session.query(
            func.count(ItemMemoryState.item_id).label('total_items'),
            func.sum(case((ItemMemoryState.state == 0, 1), else_=0)).label('new_items')
        ).filter(ItemMemoryState.user_id == user_id)

        if start_date:
            query = query.filter(ItemMemoryState.last_review >= start_date)
        if end_date:
            query = query.filter(ItemMemoryState.last_review <= end_date)
            
        result = query.one()
        return {
            'total_items': result.total_items or 0,
            'new_items': result.new_items or 0
        }

    @staticmethod
    def get_daily_new_items_count(user_id: int, start_date, end_date) -> int:
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        return ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.created_at >= start_date,
            ItemMemoryState.created_at <= end_date
        ).count()

    @staticmethod
    def get_daily_reviewed_items_count(user_id: int, start_date, end_date) -> int:
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        from sqlalchemy import and_
        return ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.last_review >= start_date,
            ItemMemoryState.last_review <= end_date,
            ~and_(
                ItemMemoryState.created_at >= start_date,
                ItemMemoryState.created_at <= end_date
            )
        ).count()

    @staticmethod
    def apply_memory_filter(query, user_id: int, filter_type: str):
        """
        Apply complex FSRS-based filters to a SQLAlchemy query.
        Used by FlashcardQueryBuilder to avoid direct model access.
        """
        from sqlalchemy import func, or_, and_
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        from mindstack_app.models import LearningItem, db
        from datetime import datetime, timezone
        from flask import current_app
        
        current_app.logger.info(f"[FSRS] Apply filter '{filter_type}' User {user_id}")
        print(f" [FSRS] Apply filter '{filter_type}' User {user_id} (Type: {type(user_id)})")
        
        # Helper to join if not already joined? 
        # QueryBuilder manages joins, but here we assume we can add join or filter directly.
        # Ideally, we pass the query object and return modified query.
        
        # We need to know if ItemMemoryState is already joined.
        # SQLAlchemy's outerjoin is idempotent-ish if done correctly, but let's be careful.
        
        # Check if query already has ItemMemoryState? Hard to do reliably.
        # Strategy: Always outerjoin.
        
        query = query.outerjoin(
            ItemMemoryState,
            (ItemMemoryState.item_id == LearningItem.item_id) &
            (ItemMemoryState.user_id == user_id)
        )
        
        # DEBUG: Print query SQL
        try:
            compiled = query.statement.compile(db.session.bind, compile_kwargs={"literal_binds": True})
            print(f" [FSRS] Query SQL: {compiled}")
        except Exception as e:
            print(f" [FSRS] Query SQL (raw): {query}")
        
        now = datetime.now(timezone.utc)
        
        if filter_type == 'new':
            return query.filter(
                or_(
                    ItemMemoryState.state_id.is_(None),
                    ItemMemoryState.state == 0
                )
            ).order_by(LearningItem.order_in_container.asc())

        elif filter_type == 'learned':
            # Learned: state != 0 (and exists)
            return query.filter(
                ItemMemoryState.state != 0
            ).order_by(LearningItem.order_in_container.asc())
            
        elif filter_type == 'due':
            return query.filter(
                ItemMemoryState.state != 0,
                ItemMemoryState.due_date <= now
            ).order_by(ItemMemoryState.due_date.asc())
            
        elif filter_type == 'hard':
            return query.filter(
                ItemMemoryState.difficulty >= 7.0
            )

        elif filter_type == 'review':
             return query.filter(
                ItemMemoryState.state != 0
            ).order_by(func.random())

        elif filter_type == 'available': # New or Due
             return query.filter(
                or_(
                    ItemMemoryState.state_id.is_(None),
                    ItemMemoryState.state == 0,
                    and_(
                        ItemMemoryState.state != 0,
                        ItemMemoryState.due_date <= now
                    )
                )
            )
        
        elif filter_type == 'srs' or filter_type == 'mixed':
            # Priority 1: Due cards first (based on FSRS scheduling), shuffled
            # Priority 2: New cards second (Sequential)
            
            # Apply filter (available items only: New or Due)
            query = query.filter(
                or_(
                    ItemMemoryState.state_id.is_(None),
                    ItemMemoryState.state == 0,
                    and_(
                        ItemMemoryState.state != 0,
                        ItemMemoryState.due_date <= now
                    )
                )
            )
            
            # Import case for sorting
            from sqlalchemy import case
            
            # Use explicit CASE for sorting to ensure 1/0 values (handling NULLs from outerjoin)
            is_due_case = case(
                (and_(ItemMemoryState.state != 0, ItemMemoryState.due_date <= now), 1),
                else_=0
            )
            
            is_new_case = case(
                (or_(ItemMemoryState.state_id.is_(None), ItemMemoryState.state == 0), 1),
                else_=0
            )
            
            return query.order_by(
                is_due_case.desc(),  # Due items (1) first
                is_new_case.desc(),  # New items (1) second (backup if not due)
                case(
                    (and_(ItemMemoryState.state != 0, ItemMemoryState.due_date <= now), func.random()), # Randomize if Due
                    else_=LearningItem.order_in_container # Sequential if New
                )
            )
             
        return query
    @staticmethod
    def get_hard_count(user_id: int, container_id: int) -> int:
        """Get count of hard items in a container."""
        from sqlalchemy import func
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        from mindstack_app.models import LearningItem, db
        
        return db.session.query(func.count(ItemMemoryState.item_id)).join(
            LearningItem, LearningItem.item_id == ItemMemoryState.item_id
        ).filter(
            ItemMemoryState.user_id == user_id,
            LearningItem.container_id == container_id,
            ItemMemoryState.difficulty >= 7.5
        ).scalar() or 0

    @staticmethod
    def get_leaderboard_mastery(user_ids: List[int], item_ids_subquery) -> Dict[int, int]:
        """
        Get mastered count for use in leaderboards.
        Returns {user_id: mastered_count}.
        """
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        from sqlalchemy import func
        from mindstack_app.core.extensions import db
        
        mastered_data = db.session.query(
            ItemMemoryState.user_id, 
            func.count(ItemMemoryState.item_id)
        ).filter(
             ItemMemoryState.item_id.in_(item_ids_subquery), 
             ItemMemoryState.user_id.in_(user_ids), 
             ItemMemoryState.stability >= 21.0
        ).group_by(ItemMemoryState.user_id).all()
        
        return {uid: count for uid, count in mastered_data}

    @staticmethod
    def apply_ordering(query, user_id: int, order_type: str):
        """
        Apply ordering based on FSRS state without direct model access.
        """
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        from mindstack_app.models import LearningItem
        
        # Ensure join
        query = query.outerjoin(
            ItemMemoryState,
            (ItemMemoryState.item_id == LearningItem.item_id) &
            (ItemMemoryState.user_id == user_id)
        )
        
        if order_type == 'due_date':
            return query.order_by(ItemMemoryState.due_date.asc().nulls_last(), LearningItem.order_in_container.asc())
        elif order_type == 'mastery':
            return query.order_by(ItemMemoryState.stability.desc().nulls_last())
        
        return query

    @staticmethod
    def get_learned_count(user_id: int, container_id: int) -> int:
        """
        Get count of learned items (state != 0) in a container.
        Optimized SQL query.
        """
        from sqlalchemy import func
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        from mindstack_app.models import LearningItem, db
        
        return db.session.query(func.count(ItemMemoryState.state_id)).join(
            LearningItem, LearningItem.item_id == ItemMemoryState.item_id
        ).filter(
            LearningItem.container_id == container_id,
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.state != 0
        ).scalar() or 0

    @staticmethod
    def get_initial_state(user_id: int, item_id: int):
        """
        Create a new initial ItemMemoryState (not persisted).
        """
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        from datetime import datetime, timezone
        return ItemMemoryState(
            user_id=user_id, item_id=item_id,
            state=0, # NEW
            created_at=datetime.now(timezone.utc)
        )

    @staticmethod
    def get_detailed_container_stats(user_id: int, container_ids: Optional[List[int]] = None, item_type: str = 'FLASHCARD') -> Dict[int, Dict]:
        """
        Get detailed aggregated stats for containers (attempted, correct, streaks, etc).
        Returns {container_id: {attempted, correct, incorrect, avg_streak, best_streak, ...}}
        """
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        from mindstack_app.models import LearningItem, db
        from sqlalchemy import func, case
        
        query = (
            db.session.query(
                LearningItem.container_id,
                func.count(ItemMemoryState.state_id).label('attempted'),
                func.sum(ItemMemoryState.times_correct).label('correct'),
                func.sum(ItemMemoryState.times_incorrect).label('incorrect'),
                func.avg(ItemMemoryState.streak).label('avg_streak'),
                func.max(ItemMemoryState.streak).label('best_streak'),
                func.sum(case((ItemMemoryState.stability >= (21.0 if item_type == 'FLASHCARD' else 5.0), 1), else_=0)).label('mastered')
            )
            .join(LearningItem, LearningItem.item_id == ItemMemoryState.item_id)
            .filter(
                ItemMemoryState.user_id == user_id,
                LearningItem.item_type == item_type
            )
        )
        
        if container_ids is not None:
            query = query.filter(LearningItem.container_id.in_(container_ids))
            
        rows = query.group_by(LearningItem.container_id).all()
        
        result = {}
        for r in rows:
            result[r.container_id] = {
                'attempted': int(r.attempted or 0),
                'correct': int(r.correct or 0),
                'incorrect': int(r.incorrect or 0),
                'avg_streak': float(r.avg_streak or 0),
                'best_streak': int(r.best_streak or 0),
                'mastered': int(r.mastered or 0)
            }
        return result

    @staticmethod
    def get_course_container_stats(user_id: int, container_ids: Optional[List[int]] = None) -> Dict[int, Dict]:
        """
        Get aggregated stats for course containers (using LESSON items).
        """
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        from mindstack_app.models import LearningItem, db
        from sqlalchemy import func, case
        
        query = (
            db.session.query(
                LearningItem.container_id,
                func.count(ItemMemoryState.state_id).label('started'),
                func.sum(case((db.cast(ItemMemoryState.data['completion_percentage'], db.Integer) >= 100, 1), else_=0)).label('completed'),
                func.avg(db.cast(ItemMemoryState.data['completion_percentage'], db.Integer)).label('avg_completion'),
                func.max(ItemMemoryState.last_review).label('last_activity')
            )
            .join(LearningItem, LearningItem.item_id == ItemMemoryState.item_id)
            .filter(
                ItemMemoryState.user_id == user_id,
                LearningItem.item_type == 'LESSON'
            )
        )
        
        if container_ids is not None:
             query = query.filter(LearningItem.container_id.in_(container_ids))
            
        rows = query.group_by(LearningItem.container_id).all()
        
        result = {}
        for r in rows:
            result[r.container_id] = {
                'started': int(r.started or 0),
                'completed': int(r.completed or 0),
                'avg_completion': float(r.avg_completion or 0),
                'last_activity': r.last_activity
            }
        return result

    @staticmethod
    def get_daily_reviews_map(user_id: int, start_date, end_date) -> Dict[str, int]:
        """
        Get a map of date string -> review count for a date range.
        Used for charts.
        """
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        from sqlalchemy import func
        from mindstack_app.core.extensions import db
        
        # Note: ItemMemoryState only stores LAST review. 
        # For accurate review history counts, we should query StudyLog or ScoreLog.
        # But User requested to rely on FSRS logic where possible? 
        # Wait, `get_daily_reviewed_items_count` uses ItemMemoryState.last_review.
        # This is inaccurate for historical charts because it only shows the LAST review date.
        # If I review an item today, its last review date moves to today.
        
        # HOWEVER, the `LearningMetricsService` implementation plan relies on this method.
        # If we want accurate "Reviews per day" chart, we MUST use ScoreLog or StudyLog.
        # `ScoreLog` is available and used for Points.
        # Does ScoreLog track every review? Yes, usually.
        # Let's check `ScoreLog` usage. 
        # ScoreLog tracks score changes.
        
        # Alternative: Use `StudyLog` (if available in this context).
        # The checklist said "REFAC: StudyLog removed (Isolation)".
        # So we shouldn't rely on StudyLog if it's being removed/isolated?
        # But `LearningHistoryInterface` exists.
        
        # The prompt said "REFAC: ItemMemoryState removed... REFAC: StudyLog removed (Isolation)".
        # It seems I should access logs via `LearningHistoryInterface`?
        # But `LearningMetricsService` already queries `ScoreLog` directly.
        # So I will query `ScoreLog` here as a proxy for activity/reviews.
        # Or, I can check if `StudyLog` is still accessible.
        # `mindstack_app/modules/learning/services/learning_metrics_service.py` imports `StudyLog`.
        
        # Let's use `ScoreLog` or `StudyLog` here? 
        # Actually `FSRSInterface` should be about FSRS state.
        # Historical review counts are NOT FSRS state (which is snapshots).
        # But the method `get_daily_reviews_map` was requested to be in `FsrsInterface`?
        # Or maybe I should put it in `LearningMetricsService` directly?
        # `LearningMetricsService` called `FsrsInterface.get_daily_reviews_map`.
        # So I must implement it here.
        
        # I will implement it using `item_memory_state` last_review as a fallback 
        # OR better, if valid, query `LearningHistoryInterface`.
        # But `FsrsInterface` depending on `LearningHistoryInterface` might be a circular dep?
        # `Fsrs` -> `LearningHistory`?
        # `LearningHistory` -> `Fsrs`?
        
        # To avoid circular dep, I will query the `StudyLog` model directly if it's in `mindstack_app.models`.
        # Or `ScoreLog`.
        
        # Re-reading `learning_metrics_service.py` imports:
        # `from mindstack_app.models import ..., StudyLog`
        # So `StudyLog` is in core models.
        
        # I'll use `StudyLog` to get accurate review counts.
        from mindstack_app.models import StudyLog
    @staticmethod
    def get_daily_reviews_map(user_id: int, start_date, end_date, item_types: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Get a map of date string -> review count for a date range.
        Used for charts.
        """
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        from sqlalchemy import func
        from mindstack_app.core.extensions import db
        from mindstack_app.models import ScoreLog
        from datetime import datetime, time, timezone
        
        # Date filtering
        start_dt = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc)
        
        query = db.session.query(
            func.date(ScoreLog.timestamp).label('date'),
            func.count(ScoreLog.log_id).label('count')
        ).filter(
            ScoreLog.user_id == user_id,
            ScoreLog.timestamp >= start_dt
        )
        
        if item_types:
            query = query.filter(ScoreLog.item_type.in_(item_types))
        else:
            query = query.filter(ScoreLog.item_type.in_(['FLASHCARD', 'QUIZ_MCQ', 'LESSON']))
            
        rows = query.group_by(func.date(ScoreLog.timestamp)).all()
        
        return {str(row.date): int(row.count) for row in rows}

    @staticmethod
    def get_daily_new_items_map(user_id: int, start_date, end_date, item_types: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Get a map of date string -> new items count (created_at) for a date range.
        """
        from mindstack_app.modules.fsrs.models import ItemMemoryState
        from mindstack_app.models import LearningItem
        from sqlalchemy import func
        from mindstack_app.core.extensions import db
        from datetime import datetime, time, timezone
        
        start_dt = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc)
        
        query = db.session.query(
            func.date(ItemMemoryState.created_at).label('date'),
            func.count(ItemMemoryState.item_id).label('count')
        ).filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.created_at >= start_dt
        )

        if item_types:
            # Need to join with LearningItem to filter by type
            query = query.join(LearningItem, LearningItem.item_id == ItemMemoryState.item_id)\
                         .filter(LearningItem.item_type.in_(item_types))

        rows = query.group_by(func.date(ItemMemoryState.created_at)).all()
        
        return {str(row.date): int(row.count) for row in rows}

    @staticmethod
    def get_all_memory_states_query():
        """Returns the base query object for ItemMemoryState (for backup/export)."""
        from .models import ItemMemoryState
        return ItemMemoryState.query

    @staticmethod
    def get_parameters(user_id: int):
        """Returns FSRS parameters for a user."""
        from .services.settings_service import FSRSSettingsService
        # Note: Current SettingsService implementation doesn't use user_id yet, but interface allows it.
        return FSRSSettingsService.get_parameters()

    @staticmethod
    def save_lesson_progress(user_id: int, item_id: int, percentage: int):
        """
        Updates or creates lesson progress in ItemMemoryState.data.
        """
        from .models import ItemMemoryState
        from mindstack_app.models import db
        from sqlalchemy import func
        from sqlalchemy.orm.attributes import flag_modified
        
        progress = ItemMemoryState.query.filter_by(
            user_id=user_id,
            item_id=item_id
        ).first()

        if progress:
            if not progress.data:
                progress.data = {}
            progress.data['completion_percentage'] = int(percentage)
            flag_modified(progress, 'data')
        else:
            progress = ItemMemoryState(
                user_id=user_id,
                item_id=item_id,
                state=0, # NEW
                data={'completion_percentage': int(percentage)}
            )
            db.session.add(progress)

        progress.last_review = func.now()
        # Note: DB commit is NOT handled here to allow transaction grouping in routes.
        return progress

    @staticmethod
    def get_batch_memory_states(user_id: int, item_ids: List[int]) -> Dict[int, Any]:
        """
        Efficiently fetches memory states for multiple items.
        Returns mapping {item_id: state_record}
        """
        from .models import ItemMemoryState
        if not item_ids:
            return {}
            
        records = ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.item_id.in_(item_ids)
        ).all()
        
        return {r.item_id: r for r in records}

    @staticmethod
    def get_upcoming_reviews(user_id: int) -> Dict[str, Any]:
        """
        Get upcoming reviews count for the next 7 days.
        """
        from datetime import datetime, timedelta, timezone
        from sqlalchemy import func
        from .models import ItemMemoryState
        from mindstack_app.core.extensions import db
        
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=6)
        
        query = db.session.query(
            func.date(ItemMemoryState.due_date).label('due_date'),
            func.count(ItemMemoryState.state_id).label('count')
        ).filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.due_date >= start_date,
            ItemMemoryState.due_date <= end_date
        ).group_by(func.date(ItemMemoryState.due_date)).all()
        
        data_map = {}
        for row in query:
            d_val = row.due_date
            if isinstance(d_val, str):
                 data_map[d_val] = row.count
            elif hasattr(d_val, 'isoformat'):
                 data_map[d_val.isoformat()[:10]] = row.count
            else:
                 data_map[str(d_val)] = row.count

        labels = []
        counts = []
        
        current = start_date
        for _ in range(7):
            d_str = current.strftime('%Y-%m-%d')
            labels.append(current.strftime('%d/%m'))
            counts.append(data_map.get(d_str, 0))
            current += timedelta(days=1)
            
        return {
            'labels': labels,
            'data': counts
        }

    @staticmethod
    def get_memory_state_distribution(user_id: int) -> Dict[str, Any]:
        """
        Get distribution of items by FSRS state.
        0=New, 1=Learning, 2=Review, 3=Relearning
        """
        from sqlalchemy import func
        from .models import ItemMemoryState
        from mindstack_app.core.extensions import db
        
        query = db.session.query(
            ItemMemoryState.state,
            func.count(ItemMemoryState.state_id).label('count')
        ).filter(
            ItemMemoryState.user_id == user_id
        ).group_by(ItemMemoryState.state).all()
        
        counts = {0: 0, 1: 0, 2: 0, 3: 0}
        for row in query:
            if row.state in counts:
                counts[row.state] = row.count
                
        return {
            'labels': ['Mới', 'Đang học', 'Ôn tập', 'Học lại'],
            'data': [counts[0], counts[1], counts[2], counts[3]],
            'colors': ['#10b981', '#3b82f6', '#f59e0b', '#ef4444']
        }

    @staticmethod
    def calculate_retrievability_for_record(record: Any, now: Optional[datetime.datetime] = None) -> float:
        """
        Calculates retrievability for a given ItemMemoryState record.
        """
        from .engine.core import FSRSEngine
        from .services.scheduler_service import SchedulerService
        from .services.optimizer_service import FSRSOptimizerService
        from .services.settings_service import FSRSSettingsService
        
        if not record:
            return 0.0

        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc)

        # 1. Convert to DTO
        dto = SchedulerService._model_to_dto(record)
        
        # 2. Get Engine
        effective_weights = FSRSOptimizerService.get_user_parameters(record.user_id)
        desired_retention = float(FSRSSettingsService.get('FSRS_DESIRED_RETENTION', 0.9))
        engine = FSRSEngine(custom_weights=effective_weights, desired_retention=desired_retention)
        
        # 3. Calculate
        return engine.get_realtime_retention(dto, now)

    @staticmethod
    def apply_due_exclusion_filter(query, user_id: int, item_ids: List[int]):
        """
        Exclude specific item IDs, UNLESS they are currently due.
        Moves logic out of vocab_flashcard/query_builder.py.
        """
        from sqlalchemy import or_, and_
        from datetime import datetime, timezone
        from .models import ItemMemoryState
        from mindstack_app.models import LearningItem
        
        if not item_ids:
            return query
            
        now = datetime.now(timezone.utc)
        return query.filter(
            or_(
                LearningItem.item_id.notin_(item_ids),
                and_(
                    ItemMemoryState.item_id.in_(item_ids),
                    ItemMemoryState.due_date <= now
                )
            )
        )
