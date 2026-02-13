# File: mindstack_app/modules/session/interface.py
"""
Session Interface
=================
Public API for other modules to interact with learning session functionality.
All cross-module session operations must go through this interface.
"""

from typing import Optional, List, Union
from .services.session_service import LearningSessionService

# Re-export driver components for cross-module usage
from .drivers import (
    BaseSessionDriver,
    SessionState,
    InteractionPayload,
    SubmissionResult,
    SessionSummary,
    DriverRegistry
)


class SessionInterface:
    """Public interface for session module operations."""
    
    @staticmethod
    def create_session(
        user_id: int,
        learning_mode: str,
        mode_config_id: Optional[int],
        set_id_data: Union[int, List[int]],
        total_items: int = 0
    ):
        """
        Create a new learning session.
        
        Args:
            user_id: User ID
            learning_mode: Mode type (flashcard, mcq, typing, etc.)
            mode_config_id: Optional configuration ID
            set_id_data: Container ID or list of container IDs
            total_items: Expected total items in session
            
        Returns:
            LearningSession object or None on error
        """
        return LearningSessionService.create_session(
            user_id=user_id,
            learning_mode=learning_mode,
            mode_config_id=mode_config_id,
            set_id_data=set_id_data,
            total_items=total_items
        )
    
    @staticmethod
    def get_active_session(
        user_id: int,
        learning_mode: Optional[str] = None,
        set_id_data: Optional[int] = None
    ):
        """Get the most recent active session for a user."""
        return LearningSessionService.get_active_session(
            user_id=user_id,
            learning_mode=learning_mode,
            set_id_data=set_id_data
        )
    
    @staticmethod
    def get_active_sessions(user_id: int, learning_mode: Optional[str] = None):
        """Get all active sessions for a user."""
        return LearningSessionService.get_active_sessions(
            user_id=user_id,
            learning_mode=learning_mode
        )
    
    @staticmethod
    def get_any_active_vocabulary_session(user_id: int, set_id_data: int):
        """Get any active vocabulary-type session for a specific set."""
        return LearningSessionService.get_any_active_vocabulary_session(
            user_id=user_id,
            set_id_data=set_id_data
        )
    
    @staticmethod
    def update_progress(
        session_id: int,
        item_id: int,
        result_type: str,
        points: int = 0
    ) -> bool:
        """
        Update session progress.
        
        Args:
            session_id: Session ID
            item_id: Item ID that was processed
            result_type: 'correct', 'incorrect', or 'vague'
            points: Points earned
            
        Returns:
            True on success, False on failure
        """
        return LearningSessionService.update_progress(
            session_id=session_id,
            item_id=item_id,
            result_type=result_type,
            points=points
        )
    
    @staticmethod
    def complete_session(session_id: int) -> bool:
        """Mark a session as completed."""
        return LearningSessionService.complete_session(session_id)
    
    @staticmethod
    def cancel_active_sessions(
        user_id: int,
        learning_mode: Union[str, List[str]],
        set_id_data: Optional[int] = None
    ) -> bool:
        """Cancel active sessions for a user."""
        return LearningSessionService.cancel_active_sessions(
            user_id=user_id,
            learning_mode=learning_mode,
            set_id_data=set_id_data
        )
    
    @staticmethod
    def get_session_by_id(session_id: int):
        """Get a session by its ID."""
        return LearningSessionService.get_session_by_id(session_id)
    
    @staticmethod
    def reset_session_progress(session_id):
        return LearningSessionService.reset_session_progress(session_id)

    @staticmethod
    def get_session_history(user_id: int, limit: int = 50):
        """Get completed/cancelled sessions for a user."""
        return LearningSessionService.get_session_history(user_id, limit)

    @staticmethod
    def set_current_item(session_id: int, item_id: int) -> bool:
        """Update the active item for a session."""
        return LearningSessionService.set_current_item(session_id, item_id)

    @staticmethod
    def start_driven_session(
        user_id: int, 
        container_id: Union[int, str], 
        learning_mode: str, 
        settings: Optional[dict] = None
    ):
        """
        Start a new session using the Driver Pattern.
        Returns (db_session, driver_state).
        """
        return LearningSessionService.start_driven_session(
            user_id=user_id,
            container_id=container_id,
            learning_mode=learning_mode,
            settings=settings
        )

    @staticmethod
    def get_driver_state(session_id: int):
        """Get the current driver state for a session."""
        return LearningSessionService.get_driver_state(session_id)
