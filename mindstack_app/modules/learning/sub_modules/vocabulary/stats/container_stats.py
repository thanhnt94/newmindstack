# File: vocabulary/stats/container_stats.py
# Vocabulary Container Statistics Service
# Provides comprehensive learning statistics for vocabulary sets

from datetime import datetime
from sqlalchemy import func
from mindstack_app.models import LearningItem, ReviewLog
from mindstack_app.models.learning_progress import LearningProgress


class VocabularyContainerStats:
    """
    Centralized service for vocabulary container-level statistics.
    Provides comprehensive methods to get progress counts, overview stats, etc.
    
    MIGRATED: Uses LearningProgress instead of FlashcardProgress.
    """
    
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
                mastery = progress.mastery or 0.0
                total_mastery += mastery
                
                # Categorize by mastery level
                if mastery >= 0.8:
                    mastered_count += 1
                else:
                    learning_count += 1
                
                # Check if due
                if progress.due_time and progress.due_time <= now:
                    due_count += 1
                
                # Check if hard
                if mastery < 0.5 or (progress.incorrect_streak or 0) >= 2:
                    hard_count += 1
                
                # Accumulate totals
                total_correct += progress.times_correct or 0
                total_incorrect += progress.times_incorrect or 0
                total_reviews += (progress.times_correct or 0) + (progress.times_incorrect or 0) + (progress.times_vague or 0)
                
                # Track last reviewed
                if progress.last_reviewed:
                    if not last_reviewed or progress.last_reviewed > last_reviewed:
                        last_reviewed = progress.last_reviewed
        
        # Calculate percentages
        learned_count = len(progress_records)
        completion_pct = (learned_count / total * 100) if total > 0 else 0
        mastery_avg = (total_mastery / learned_count) if learned_count > 0 else 0
        accuracy_pct = (total_correct / (total_correct + total_incorrect) * 100) if (total_correct + total_incorrect) > 0 else 0
        
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
            mastery = progress.mastery or 0.0
            if mastery < 0.5:
                weak_count += 1
            elif mastery < 0.8:
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
            ReviewLog.mastery_snapshot.isnot(None)
        ).order_by(ReviewLog.timestamp).all()
        
        # Group by date and calculate average mastery per day
        for log in logs:
            date_key = log.timestamp.strftime('%d/%m')
            if log.mastery_snapshot is not None:
                timeline_data[date_key].append(log.mastery_snapshot * 100)
        
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
