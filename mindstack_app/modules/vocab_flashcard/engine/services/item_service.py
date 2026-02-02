"""
FlashcardItemService - Service for retrieving flashcard items

Provides methods for fetching flashcard items based on various
learning criteria (new, due, review, hard, capability-based, etc.)
"""
from typing import Optional, Union, List
from flask import current_app
from sqlalchemy import func, and_, or_, cast, String

from mindstack_app.models import (
    db,
    LearningItem,
    LearningContainer,
    UserContainerState,
)
from .permission_service import FlashcardPermissionService
from .query_builder import FlashcardQueryBuilder


def _normalize_capability_flags(raw_flags) -> set:
    """Normalize capability flags from ai_settings to a set of strings."""
    normalized = set()
    if isinstance(raw_flags, (list, tuple, set)):
        for value in raw_flags:
            if isinstance(value, str) and value:
                normalized.add(value)
    elif isinstance(raw_flags, dict):
        for key, enabled in raw_flags.items():
            if enabled and isinstance(key, str) and key:
                normalized.add(key)
    elif isinstance(raw_flags, str) and raw_flags:
        normalized.add(raw_flags)
    return normalized


class FlashcardItemService:
    """
    Service for retrieving flashcard items based on learning criteria.
    
    All methods follow a consistent pattern:
    - Returns a Query object if session_size is None
    - Returns a list of items if session_size is specified
    """
    
    @classmethod
    def get_new_items(
        cls, 
        user_id: int, 
        container_id: Union[int, str, List], 
        session_size: Optional[int] = None
    ):
        """
        Get new items (not yet learned or in NEW state).
        """
        current_app.logger.debug(
            f"FlashcardItemService.get_new_items: user={user_id}, container={container_id}"
        )
        
        accessible_ids = FlashcardPermissionService.normalize_container_id(user_id, container_id)
        builder = (FlashcardQueryBuilder(user_id)
            .filter_by_containers(accessible_ids)
            .filter_new_only())
        
        if session_size is None or session_size == 999999:
            return builder.get_query()
        
        items = builder.get_query().limit(session_size).all()
        current_app.logger.debug(f"FlashcardItemService.get_new_items: found {len(items)} items")
        return items
    
    @classmethod
    def get_due_items(
        cls, 
        user_id: int, 
        container_id: Union[int, str, List], 
        session_size: Optional[int] = None
    ):
        """
        Get items due for review (due_date <= now).
        """
        current_app.logger.debug(
            f"FlashcardItemService.get_due_items: user={user_id}, container={container_id}"
        )
        
        accessible_ids = FlashcardPermissionService.normalize_container_id(user_id, container_id)
        builder = (FlashcardQueryBuilder(user_id)
            .filter_by_containers(accessible_ids)
            .filter_due_only())
        
        if session_size is None or session_size == 999999:
            return builder.get_query()
        
        items = builder.get_query().limit(session_size).all()
        current_app.logger.debug(f"FlashcardItemService.get_due_items: found {len(items)} items")
        return items
    
    @classmethod
    def get_all_review_items(
        cls, 
        user_id: int, 
        container_id: Union[int, str, List], 
        session_size: Optional[int] = None
    ):
        """
        Get all items with learning progress (not NEW state).
        """
        current_app.logger.debug(
            f"FlashcardItemService.get_all_review_items: user={user_id}, container={container_id}"
        )
        
        accessible_ids = FlashcardPermissionService.normalize_container_id(user_id, container_id)
        builder = (FlashcardQueryBuilder(user_id)
            .filter_by_containers(accessible_ids)
            .filter_all_review())
        
        if session_size is None or session_size == 999999:
            return builder.get_query()
        
        items = builder.get_query().limit(session_size).all()
        current_app.logger.debug(f"FlashcardItemService.get_all_review_items: found {len(items)} items")
        return items
    
    @classmethod
    def get_hard_items(
        cls, 
        user_id: int, 
        container_id: Union[int, str, List], 
        session_size: Optional[int] = None
    ):
        """
        Get difficult items using HardItemService.
        """
        current_app.logger.debug(
            f"FlashcardItemService.get_hard_items: user={user_id}, container={container_id}"
        )
        
        # Use centralized HardItemService for core "hard" logic
        from mindstack_app.modules.fsrs.services.hard_item_service import FSRSHardItemService as HardItemService
        
        hard_items_query = HardItemService.get_hard_items_query(
            user_id=user_id,
            container_id=container_id,
            learning_mode='flashcard'
        )
        
        # Add archive filter
        hard_items_query = hard_items_query.outerjoin(
            UserContainerState,
            and_(
                UserContainerState.container_id == LearningItem.container_id,
                UserContainerState.user_id == user_id
            )
        ).filter(
            or_(
                UserContainerState.is_archived == False,
                UserContainerState.is_archived == None
            )
        )
        
        if session_size is None or session_size == 999999:
            return hard_items_query
        
        items = hard_items_query.order_by(func.random()).limit(session_size).all()
        current_app.logger.debug(f"FlashcardItemService.get_hard_items: found {len(items)} items")
        return items
    
    @classmethod
    def get_mixed_items(
        cls, 
        user_id: int, 
        container_id: Union[int, str, List], 
        session_size: Optional[int] = None
    ):
        """
        Get mixed due + new items (union query for counting).
        """
        current_app.logger.debug(
            f"FlashcardItemService.get_mixed_items: user={user_id}, container={container_id}"
        )
        
        # Build queries WITHOUT ordering (required for UNION in SQLite)
        accessible_ids = FlashcardPermissionService.normalize_container_id(user_id, container_id)
        # Order-less queries for UNION
        due_query = (FlashcardQueryBuilder(user_id)
            .filter_by_containers(accessible_ids)
            .filter_due_only()
            .get_query())
        
        new_query = (FlashcardQueryBuilder(user_id)
            .filter_by_containers(accessible_ids)
            .filter_new_only()
            .get_query())
        
        # Union for counting unique items
        mixed_query = due_query.union(new_query)
        
        return mixed_query
    
    @classmethod
    def get_autoplay_items(
        cls, 
        user_id: int, 
        container_id: Union[int, str, List], 
        session_size: Optional[int] = None
    ):
        """
        Get all items for autoplay mode (including new).
        """
        current_app.logger.debug(
            f"FlashcardItemService.get_autoplay_items: user={user_id}, container={container_id}"
        )
        
        accessible_ids = FlashcardPermissionService.normalize_container_id(user_id, container_id)
        builder = (FlashcardQueryBuilder(user_id)
            .filter_by_containers(accessible_ids)
            .filter_sequential()) # Autoplay is often sequential
        
        if session_size is None or session_size == 999999:
            return builder.get_query()
        
        items = builder.get_query().limit(session_size).all()
        current_app.logger.debug(f"FlashcardItemService.get_autoplay_items: found {len(items)} items")
        return items
    
    @classmethod
    def get_sequential_items(
        cls, 
        user_id: int, 
        container_id: Union[int, str, List], 
        session_size: Optional[int] = None
    ):
        """
        Get due or new items in sequential order.
        """
        current_app.logger.debug(
            f"FlashcardItemService.get_sequential_items: user={user_id}, container={container_id}"
        )
        
        accessible_ids = FlashcardPermissionService.normalize_container_id(user_id, container_id)
        builder = (FlashcardQueryBuilder(user_id)
            .filter_by_containers(accessible_ids)
            .filter_sequential())
        
        if session_size is None or session_size == 999999:
            return builder.get_query()
        
        items = builder.get_query().limit(session_size).all()
        current_app.logger.debug(f"FlashcardItemService.get_sequential_items: found {len(items)} items")
        return items
    
    @classmethod
    def get_items_by_capability(
        cls, 
        user_id: int, 
        container_id: Union[int, str, List], 
        capability_flag: str,
        session_size: Optional[int] = None
    ):
        """
        Get items with a specific capability flag.
        """
        current_app.logger.debug(
            f"FlashcardItemService.get_items_by_capability: user={user_id}, "
            f"container={container_id}, capability={capability_flag}"
        )
        
        accessible_ids = FlashcardPermissionService.normalize_container_id(
            user_id, container_id
        )
        
        if not accessible_ids:
            # No accessible containers
            empty_query = LearningItem.query.filter(False)
            return empty_query if session_size is None else []
        
        # Find containers with this capability enabled
        enabled_set_ids = set()
        containers = LearningContainer.query.filter(
            LearningContainer.container_id.in_(accessible_ids)
        ).all()
        
        for container in containers:
            capabilities = set()
            if hasattr(container, 'capability_flags'):
                capabilities = container.capability_flags()
            else:
                settings_payload = getattr(container, 'ai_settings', None)
                if isinstance(settings_payload, dict):
                    capabilities = _normalize_capability_flags(
                        settings_payload.get('capabilities')
                    )
            if capability_flag in capabilities:
                enabled_set_ids.add(container.container_id)
        
        # Build query
        base_query = LearningItem.query.filter(
            LearningItem.item_type == 'FLASHCARD',
            LearningItem.container_id.in_(accessible_ids)
        )
        
        # Add archive filter
        base_query = base_query.outerjoin(
            UserContainerState,
            and_(
                UserContainerState.container_id == LearningItem.container_id,
                UserContainerState.user_id == user_id
            )
        ).filter(
            or_(
                UserContainerState.is_archived == False,
                UserContainerState.is_archived == None
            )
        )
        
        # Filter by capability (item-level or container-level)
        capability_json_value = cast(LearningItem.content[capability_flag], String)
        capability_filters = [
            func.lower(func.coalesce(capability_json_value, 'false')) == 'true'
        ]
        if enabled_set_ids:
            capability_filters.append(LearningItem.container_id.in_(enabled_set_ids))
        
        final_query = base_query.filter(or_(*capability_filters))
        final_query = final_query.order_by(
            LearningItem.order_in_container.asc(),
            LearningItem.item_id.asc()
        )
        
        if session_size is None or session_size == 999999:
            return final_query
        
        items = final_query.limit(session_size).all()
        current_app.logger.debug(
            f"FlashcardItemService.get_items_by_capability: found {len(items)} items"
        )
        return items
    
    # Convenience methods for specific capabilities
    @classmethod
    def get_pronunciation_items(cls, user_id, container_id, session_size=None):
        return cls.get_items_by_capability(user_id, container_id, 'supports_pronunciation', session_size)
    
    @classmethod
    def get_writing_items(cls, user_id, container_id, session_size=None):
        return cls.get_items_by_capability(user_id, container_id, 'supports_writing', session_size)
    
    @classmethod
    def get_quiz_items(cls, user_id, container_id, session_size=None):
        return cls.get_items_by_capability(user_id, container_id, 'supports_quiz', session_size)
    
    @classmethod
    def get_essay_items(cls, user_id, container_id, session_size=None):
        return cls.get_items_by_capability(user_id, container_id, 'supports_essay', session_size)
    
    @classmethod
    def get_listening_items(cls, user_id, container_id, session_size=None):
        return cls.get_items_by_capability(user_id, container_id, 'supports_listening', session_size)
    
    @classmethod
    def get_speaking_items(cls, user_id, container_id, session_size=None):
        return cls.get_items_by_capability(user_id, container_id, 'supports_speaking', session_size)