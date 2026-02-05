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

from mindstack_app.models import db, ItemMemoryState, LearningItem

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

        # 2. User's Memory States for items in this container
        # Join LearningItem to filter by container
        query = db.session.query(ItemMemoryState).join(LearningItem).filter(
            ItemMemoryState.user_id == user_id,
            LearningItem.container_id == container_id
        )
        
        progress_records = query.all()
        studied_count = len(progress_records)
        
        # 3. Calculate Derived Metrics
        # Mastered: Arbitrary threshold, e.g., stability > 21 days
        mastered_count = sum(1 for p in progress_records if (p.stability or 0) >= 21.0)
        
        # Learning: Currently explicitly in learning/relearning steps (state 1 or 3)
        # OR just not mastered yet but studied
        learning_count = sum(1 for p in progress_records if p.state in (1, 3))

        # Average Retrievability (if available via FSRS Helper, else estimate)
        # For simple stats, we might skip complex R calculation or use stability
        avg_stability = sum(p.stability or 0 for p in progress_records) / studied_count if studied_count else 0
        
        completion_pct = (studied_count / total_items * 100)
        
        return {
            'total_items': total_items,
            'studied': studied_count,
            'new': total_items - studied_count,
            'mastered': mastered_count,
            'learning': learning_count,
            'completion_percentage': round(completion_pct, 1),
            'avg_stability': round(avg_stability, 1),
            # Legacy/Compatibility fields
            'total_correct': 0, 
            'total_incorrect': 0,
            'accuracy': 0,
            'avg_retrievability': 0, # Placeholder
            'avg_mastery': 0, # Placeholder
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