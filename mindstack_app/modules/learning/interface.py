"""
Learning Module Interface
=========================

Public API for accessing Learning capabilities:
- Evaluation (Grading) of submissions
- Progress Tracking (Course completion stats)

This interface decouples consumers (Quiz, Typing, etc.) from the internal logic.
"""

from typing import Any, Dict, Optional
from mindstack_app.modules.learning.logics.marker import compare_text, evaluate_multiple_choice
from mindstack_app.modules.learning.services.progress_service import ProgressService

class LearningInterface:
    """Public Facade for Learning Module."""
    
    # === EVALUATION ===
    
    @staticmethod
    def evaluate_text_submission(submission: str, solution: str, tolerance: float = 0.0) -> Dict[str, Any]:
        """
        Evaluate a text submission against a solution.
        Returns dict with keys: is_correct, score, ratio, diff.
        """
        return compare_text(submission, solution, tolerance)

    @staticmethod
    def evaluate_mcq_submission(submission: str, correct_option: str) -> Dict[str, Any]:
        """
        Evaluate a multiple-choice submission (e.g. 'A' vs 'A').
        Returns dict with keys: is_correct, score.
        """
        return evaluate_multiple_choice(submission, correct_option)

    # === PROGRESS ===

    @staticmethod
    def get_course_progress(user_id: int, container_id: int) -> Dict[str, Any]:
        """
        Get high-level progress statistics for a course/container.
        Delegates to ProgressService to calculate completion rates.
        
        Returns:
            dict: {
                'total_items': int,
                'items_completed': int,
                'completion_percentage': float (0-100),
                'mastery_percentage': float (0-100),
                'status': str ('new', 'in_progress', 'completed')
            }
        """
        return ProgressService.get_container_stats(user_id, container_id)

    @staticmethod
    def mark_course_completed(user_id: int, container_id: int) -> bool:
        """
        Explicitly mark a course as completed (if applicable).
        """
        # Logic to mark completion in UserContainerState?
        # For now, just return False as implementation depends on specific requirements
        return False
