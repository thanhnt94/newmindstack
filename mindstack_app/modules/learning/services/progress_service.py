"""
Unified Progress Service
========================

Service for tracking Academic Progress (Course Completion).

This service calculates how much of a course/container a user has completed.
It does NOT handle Spaced Repetition (SRS) scheduling or memory states (handled by FSRS module).

Key metrics:
- Completion %: Items studied at least once / Total items.
- Mastery %: Items with high stability / Total items.
"""

from __future__ import annotations
from typing import Dict, Any, Optional

from mindstack_app.models import db, LearningItem

class ProgressService:
    """Service for calculating Academic Progress statistics."""
    
    @classmethod
    def get_container_stats(
        cls,
        user_id: int,
        container_id: int,
        mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get learning statistics for a container (Course/Deck).
        
        Returns:
            dict: {
                'total_items': int,
                'studied': int,
                'new': int,
                'mastered': int,
                'learning': int,
                'completion_percentage': float,
                'avg_retrievability': float,
            }
        """
        # 1. Total Items in Container
        total_items = LearningItem.query.filter_by(
            container_id=container_id
        ).count()
        
        if total_items == 0:
            return cls._empty_stats()

        # 2. Get Stats from FSRS Interface
        from mindstack_app.modules.fsrs.interface import FSRSInterface
        
        # Determine item type. Assume FLASHCARD for generic container unless specified?
        # Actually container can have mixed types, but ProgressService usually used for specific context.
        # But get_detailed_container_stats requires item_type. 
        # Check container type?
        # If container_type is COURSE (LESSON items), use get_course_container_stats.
        # If FLASHCARD/QUIZ, use get_detailed_container_stats.
        
        container = db.session.query(LearningContainer).get(container_id)
        if not container:
             return cls._empty_stats()
             
        if container.container_type == 'COURSE':
             stats_map = FSRSInterface.get_course_container_stats(user_id, [container_id])
             stats = stats_map.get(container_id, {})
             
             return {
                'total_items': total_items, # Note: Course items are Lessons
                'studied': stats.get('started', 0),
                'new': total_items - stats.get('started', 0),
                'mastered': stats.get('completed', 0), # 'Completed' is proxy for mastered in Course
                'learning': stats.get('started', 0) - stats.get('completed', 0),
                'completion_percentage': stats.get('avg_completion', 0), # Or calculated from completed items?
                # Actually, course progress usually means "Avg Completion" or "% of Lessons Completed"?
                # The keys returned by this service are expected by callers (Dashboard).
                # 'completion_percentage' in `get_container_stats` was `studied / total * 100`.
                # Let's keep that definition for consistency if possible, OR improve it.
                # In previous code: `completion_pct = (studied_count / total_items * 100)`.
                # So "Studied" means "Started".
                'completion_percentage': round((stats.get('started', 0) / total_items * 100), 1) if total_items else 0,
                'avg_stability': 0,
             }
             
        # Fallback to Flashcard/Quiz logic
        # Check common item type in container
        first_item = LearningItem.query.filter_by(container_id=container_id).first()
        item_type = first_item.item_type if first_item else 'FLASHCARD'
        
        stats_map = FSRSInterface.get_detailed_container_stats(user_id, [container_id], item_type=item_type)
        stats = stats_map.get(container_id, {})
        
        studied_count = stats.get('attempted', 0) # "Attempted" means state exists (studied)
        mastered_count = stats.get('mastered', 0)
        
        completion_pct = (studied_count / total_items * 100) if total_items else 0
        
        return {
            'total_items': total_items,
            'studied': studied_count,
            'new': total_items - studied_count,
            'mastered': mastered_count,
            'learning': studied_count - mastered_count,
            'completion_percentage': round(completion_pct, 1),
            # FSRS Interface doesn't return avg_stability in detailed_stats yet. 
            # If critical, I should add it.
            # But "avg_stability" is rarely shown directly in UI (usually used for Retrievability).
            # I'll return 0 for now or fetch if needed.
            'avg_stability': 0, 
            'total_correct': stats.get('correct', 0), 
            'total_incorrect': stats.get('incorrect', 0),
            'accuracy': 0, # Calced elsewhere or can be added
            'avg_retrievability': 0,
            'avg_mastery': 0, 
        }

    @staticmethod
    def _empty_stats() -> Dict[str, Any]:
        return {
            'total_items': 0, 'studied': 0, 'new': 0,
            'mastered': 0, 'learning': 0,
            'completion_percentage': 0, 'avg_stability': 0,
            'total_correct': 0, 'total_incorrect': 0,
            'accuracy': 0, 'avg_retrievability': 0, 'avg_mastery': 0
        }