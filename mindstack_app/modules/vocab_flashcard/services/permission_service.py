# File: mindstack_app/modules/vocab_flashcard/services/permission_service.py
"""
FlashcardPermissionService - Access Control for Flashcard Containers

Handles permission checking and access control logic for flashcard sets.
"""
from typing import Set, List, Union
from flask import current_app
from flask_login import current_user

from mindstack_app.models import (
    db,
    LearningContainer,
    ContainerContributor,
    User,
)
from sqlalchemy import or_


class FlashcardPermissionService:
    """
    Service for managing access permissions to flashcard containers.
    
    Handles:
    - Determining accessible container IDs based on user role
    - Permission checks for specific containers
    - Filtering container lists by accessibility
    """
    
    @staticmethod
    def get_accessible_set_ids(user_id: int) -> Set[int]:
        """
        Return IDs of flashcard sets accessible to the user.
        """
        user_obj = User.query.get(user_id)
        if not user_obj:
            return set()

        base_query = LearningContainer.query.filter(
            LearningContainer.container_type == 'FLASHCARD_SET'
        )

        # Admin sees everything
        if user_obj.user_role == User.ROLE_ADMIN:
            return {c.container_id for c in base_query.all()}

        # Free users only see their own sets
        if user_obj.user_role == User.ROLE_FREE:
            return {
                c.container_id
                for c in base_query.filter(
                    LearningContainer.creator_user_id == user_id
                ).all()
            }

        # Standard users: own + public + contributed
        contributed_ids_subquery = db.session.query(
            ContainerContributor.container_id
        ).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor',
        ).subquery()

        accessible_query = base_query.filter(
            or_(
                LearningContainer.creator_user_id == user_id,
                LearningContainer.is_public == True,
                LearningContainer.container_id.in_(contributed_ids_subquery),
            )
        )

        return {c.container_id for c in accessible_query.all()}

    @staticmethod
    def can_access_container(user_id: int, container_id: int) -> bool:
        """
        Check if user can access a specific container.
        
        Args:
            user_id: The user ID to check
            container_id: The container ID to check access for
            
        Returns:
            True if user has access, False otherwise
        """
        accessible_ids = FlashcardPermissionService.get_accessible_set_ids(user_id)
        return container_id in accessible_ids

    @staticmethod
    def filter_accessible_ids(user_id: int, container_ids: List[int]) -> List[int]:
        """
        Filter a list of container IDs to only include accessible ones.
        
        Args:
            user_id: The user ID to check permissions for
            container_ids: List of container IDs to filter
            
        Returns:
            Filtered list of accessible container IDs
        """
        accessible_ids = FlashcardPermissionService.get_accessible_set_ids(user_id)
        return [cid for cid in container_ids if cid in accessible_ids]

    @staticmethod
    def normalize_container_id(
        user_id: int, 
        container_id: Union[int, str, List]
    ) -> Set[int]:
        """
        Normalize container_id input to a set of accessible container IDs.
        
        Handles:
        - Single integer ID
        - String 'all' (returns all accessible)
        - List of IDs (filters to accessible only)
        
        Args:
            user_id: The user ID
            container_id: Container identifier (int, 'all', or list)
            
        Returns:
            Set of normalized, accessible container IDs
        """
        accessible_ids = FlashcardPermissionService.get_accessible_set_ids(user_id)
        
        if isinstance(container_id, list):
            # Multi-selection mode
            normalized = set()
            for cid in container_id:
                try:
                    cid_int = int(cid)
                    if cid_int in accessible_ids:
                        normalized.add(cid_int)
                except (TypeError, ValueError):
                    continue
            return normalized
            
        elif container_id == 'all':
            # All accessible sets
            return accessible_ids
            
        else:
            # Single container
            try:
                cid_int = int(container_id)
                if cid_int in accessible_ids:
                    return {cid_int}
            except (TypeError, ValueError):
                pass
            return set()


# Backward compatibility alias
def get_accessible_flashcard_set_ids(user_id: int) -> List[int]:
    return list(FlashcardPermissionService.get_accessible_set_ids(user_id))
