"""
Ops Module Interface
====================
Public API for system operations, maintenance, and data management.
"""

from .services.reset_service import ResetService

class OpsInterface:
    @staticmethod
    def reset_user_progress_for_container(user_id: int, container_id: int):
        """
        Resets all learning data (FSRS, History, Scores, Sessions) 
        for a specific user and container.
        """
        return ResetService.reset_user_container_progress(user_id, container_id)

    @staticmethod
    def reset_entire_learning_progress(user_id: int = None):
        """
        Resets learning progress for a user or globally.
        """
        return ResetService.reset_learning_progress(user_id)
