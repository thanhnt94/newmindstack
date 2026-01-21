# File: vocabulary/stats/container_stats.py
# Vocabulary Container Statistics Service
# Provides comprehensive learning statistics for vocabulary sets

from datetime import datetime
from sqlalchemy import func
from mindstack_app.models import LearningItem, ReviewLog, LearningContainer
from mindstack_app.models.learning_progress import LearningProgress


class VocabularyContainerStats:
    """
    Centralized service for vocabulary container-level statistics.
    Provides comprehensive methods to get progress counts, overview stats, etc.
    
    MIGRATED: Uses LearningProgress instead of FlashcardProgress.
    """
    
    @staticmethod
    def get_global_stats(user_id: int) -> dict:
        """
        Get global vocabulary statistics for a user.
        Calculates total sets, total cards, mastered items, and due items across all sets.
        """
        # 1. Total Sets created by user
        total_sets = LearningContainer.query.filter(
            LearningContainer.creator_user_id == user_id,
            LearningContainer.container_type == 'FLASHCARD_SET'
        ).count()
        
        # 2. Total Cards (Total items in all FLASHCARD_SET containers of the user)
        total_cards = LearningItem.query.join(
            LearningContainer, LearningItem.container_id == LearningContainer.container_id
        ).filter(
            LearningContainer.creator_user_id == user_id,
            LearningContainer.container_type == 'FLASHCARD_SET',
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        ).count()
        
        # 3. Mastered & Due (from LearningProgress)
        now = datetime.utcnow()
        
        # Mastered: fsrs_stability >= 21.0
        mastered = LearningProgress.query.filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD,
            LearningProgress.fsrs_stability >= 21.0
        ).count()
        
        due = LearningProgress.query.filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD,
            LearningProgress.fsrs_due <= now
        ).count()
        
        return {
            'total_sets': total_sets,
            'total_cards': total_cards,
            'mastered': mastered,
            'due': due
        }
    
    @staticmethod
    def get_full_stats(user_id: int, container_id: int) -> dict:
        """
        Get comprehensive statistics for a vocabulary container.
        
        Args:
            user_id: The user's ID
            container_id: The vocabulary container ID
            
        Returns:
            dict with all available statistics
        """
        items = LearningItem.query.filter(
            LearningItem.container_id == container_id,
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        ).all()
        
        item_ids = [item.item_id for item in items]
        total = len(item_ids)
        
        if not item_ids:
            return VocabularyContainerStats._empty_stats()
        
        # Get progress records - MIGRATED to LearningProgress
        progress_records = LearningProgress.query.filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD,
            LearningProgress.item_id.in_(item_ids)
        ).all()
        
        progress_map = {p.item_id: p for p in progress_records}
        now = datetime.utcnow()
        
        # Calculate counts
        new_count = 0
        learning_count = 0
        mastered_count = 0
        due_count = 0
        hard_count = 0
        
        total_mastery = 0.0
        total_correct = 0
        total_incorrect = 0
        total_reviews = 0
        last_reviewed = None
        
        for item_id in item_ids:
            progress = progress_map.get(item_id)
            if not progress:
                new_count += 1
            else:
                stability = progress.fsrs_stability or 0.0
                mastery = min(stability / 21.0, 1.0)
                total_mastery += mastery
                
                # Categorize by mastery level (using stability proxy)
                if stability >= 21.0:
                    mastered_count += 1
                else:
                    learning_count += 1
                
                # Check if due
                if progress.fsrs_due and progress.fsrs_due <= now:
                    due_count += 1
                
                # Note: hard_count is calculated separately using HardItemService
                
                # Accumulate totals
                total_correct += progress.times_correct or 0
                total_incorrect += progress.times_incorrect or 0
                total_reviews += (progress.times_correct or 0) + (progress.times_incorrect or 0)
                
                # Track last reviewed
                if progress.fsrs_last_review:
                    if not last_reviewed or progress.fsrs_last_review > last_reviewed:
                        last_reviewed = progress.fsrs_last_review
        
        # Calculate percentages
        learned_count = len(progress_records)
        completion_pct = (learned_count / total * 100) if total > 0 else 0
        mastery_avg = (total_mastery / learned_count) if learned_count > 0 else 0
        accuracy_pct = (total_correct / (total_correct + total_incorrect) * 100) if (total_correct + total_incorrect) > 0 else 0
        
        # Calculate hard count using centralized HardItemService
        from mindstack_app.modules.learning.services.hard_item_service import HardItemService
        hard_count = HardItemService.get_hard_count(user_id, container_id)
        
        return {
            # Counts
            'total': total,
            'new': new_count,
            'learning': learning_count,
            'mastered': mastered_count,
            'due': due_count,
            'hard': hard_count,
            'learned': learned_count,
            
            # Progress metrics
            'completion_pct': round(completion_pct, 1),
            'mastery_avg': round(mastery_avg, 2),
            'accuracy_pct': round(accuracy_pct, 1),
            
            # Review metrics
            'total_reviews': total_reviews,
            'total_correct': total_correct,
            'total_incorrect': total_incorrect,
            
            # Time-based
            'last_reviewed': last_reviewed.isoformat() if last_reviewed else None
        }
    
    @staticmethod
    def _empty_stats() -> dict:
        """Return empty stats dict."""
        return {
            'total': 0, 'new': 0, 'learning': 0, 'mastered': 0,
            'due': 0, 'hard': 0, 'learned': 0,
            'completion_pct': 0, 'mastery_avg': 0, 'accuracy_pct': 0,
            'total_reviews': 0, 'total_correct': 0, 'total_incorrect': 0,
            'last_reviewed': None
        }
    
    @staticmethod
    def get_mode_counts(user_id: int, container_id: int) -> dict:
        """
        Get learning mode counts for a vocabulary set.
        Simplified version of get_full_stats for mode selection.
        
        Returns:
            dict with keys: new, due, learned, total
        """
        stats = VocabularyContainerStats.get_full_stats(user_id, container_id)
        return {
            'new': stats['new'],
            'due': stats['due'],
            'review': stats['due'],     # Added alias
            'learned': stats['learned'],
            'hard': stats['hard'],      # Added
            'total': stats['total'],
            'random': stats['total']    # Added alias
        }
    
    
    @staticmethod
    def get_chart_data(user_id: int, container_id: int) -> dict:
        """
        Generate chart data for container stats modal.
        
        Returns:
            dict with distribution and timeline chart data
        """
        from datetime import timedelta
        from collections import defaultdict
        
        items = LearningItem.query.filter(
            LearningItem.container_id == container_id,
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        ).all()
        
        item_ids = [item.item_id for item in items]
        
        if not item_ids:
            return {
                'distribution': {'weak': 0, 'medium': 0, 'strong': 0},
                'timeline': {'dates': [], 'values': []}
            }
        
        # Get progress records
        progress_records = LearningProgress.query.filter(
            LearningProgress.user_id == user_id,
            LearningProgress.learning_mode == LearningProgress.MODE_FLASHCARD,
            LearningProgress.item_id.in_(item_ids)
        ).all()
        
        # Distribution: categorize by mastery level
        weak_count = 0      # 0-50%
        medium_count = 0    # 50-80%
        strong_count = 0    # 80-100%
        
        for progress in progress_records:
            stability = progress.fsrs_stability or 0.0
            
            # Categories based on stability (days)
            # Weak: < 5 days
            # Medium: 5-15 days
            # Strong: > 15 days
            if stability < 5.0:
                weak_count += 1
            elif stability < 15.0:
                medium_count += 1
            else:
                strong_count += 1
        
        # Timeline: Get average memory power for last 30 days
        now = datetime.utcnow()
        timeline_data = defaultdict(list)  # date -> [mastery values]
        
        # Query review logs for the last 30 days
        start_date = now - timedelta(days=30)
        logs = ReviewLog.query.filter(
            ReviewLog.user_id == user_id,
            ReviewLog.item_id.in_(item_ids),
            ReviewLog.timestamp >= start_date,
            ReviewLog.fsrs_stability.isnot(None)
        ).order_by(ReviewLog.timestamp).all()
        
        # Group by date and calculate average mastery per day
        for log in logs:
            date_key = log.timestamp.strftime('%d/%m')
            if log.fsrs_stability is not None:
                timeline_data[date_key].append(min((log.fsrs_stability or 0)/21.0, 1.0) * 100)
        
        # Generate date labels and values for past 30 days
        dates = []
        values = []
        
        for i in range(29, -1, -1):  # Last 30 days
            date = now - timedelta(days=i)
            date_key = date.strftime('%d/%m')
            dates.append(date_key)
            
            if date_key in timeline_data and timeline_data[date_key]:
                avg_mastery = sum(timeline_data[date_key]) / len(timeline_data[date_key])
                values.append(round(avg_mastery, 1))
            else:
                values.append(None)  # No data for this day
        
        return {
            'distribution': {
                'weak': weak_count,
                'medium': medium_count,
                'strong': strong_count
            },
            'timeline': {
                'dates': dates,
                'values': values
            }
        }
    
    @staticmethod
    def get_hard_count(user_id: int, container_id: int) -> int:
        """Get count of hard items."""
        stats = VocabularyContainerStats.get_full_stats(user_id, container_id)
        return stats['hard']


# Alias for backward compatibility
VocabularyStatsService = VocabularyContainerStats
