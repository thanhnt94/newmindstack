# File: vocabulary/stats/container_stats.py
# Vocabulary Container Statistics Service
# Provides comprehensive learning statistics for vocabulary sets

from datetime import datetime, timezone
from sqlalchemy import func
from mindstack_app.models import LearningItem, LearningContainer
from mindstack_app.modules.fsrs.models import ItemMemoryState
from mindstack_app.modules.learning_history.models import StudyLog
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsService


class VocabularyContainerStats:
    """
    Centralized service for vocabulary container-level statistics.
    Provides comprehensive methods to get progress counts, overview stats, etc.
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
        
        # 2. Total Cards
        total_cards = LearningItem.query.join(
            LearningContainer, LearningItem.container_id == LearningContainer.container_id
        ).filter(
            LearningContainer.creator_user_id == user_id,
            LearningContainer.container_type == 'FLASHCARD_SET',
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        ).count()
        
        # 3. Mastered & Due (from ItemMemoryState)
        now = datetime.now(timezone.utc)
        
        # Mastered: stability >= 21.0
        mastered = ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.stability >= 21.0
        ).count()
        
        due = ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.due_date <= now
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
        """
        items = LearningItem.query.filter(
            LearningItem.container_id == container_id,
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        ).all()
        
        item_ids = [item.item_id for item in items]
        total = len(item_ids)
        
        if not item_ids:
            return VocabularyContainerStats._empty_stats()
        
        # Get progress records
        progress_records = ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.item_id.in_(item_ids)
        ).all()
        
        progress_map = {p.item_id: p for p in progress_records}
        now = datetime.now(timezone.utc)
        
        # Calculate counts
        new_count = 0
        learning_count = 0
        mastered_count = 0
        due_count = 0
        
        total_retrievability = 0.0
        total_correct = 0
        total_incorrect = 0
        total_reviews = 0
        last_reviewed = None
        
        for item_id in item_ids:
            progress = progress_map.get(item_id)
            if not progress:
                new_count += 1
            else:
                stability = progress.stability or 0.0
                retrievability = FsrsService.get_retrievability(progress)
                total_retrievability += retrievability
                
                if stability >= 21.0:
                    mastered_count += 1
                else:
                    learning_count += 1
                
                if progress.due_date:
                    # Ensure progress.due_date is aware for comparison
                    due_val = progress.due_date
                    if due_val.tzinfo is None:
                        due_val = due_val.replace(tzinfo=timezone.utc)
                    if due_val <= now:
                        due_count += 1
                
                total_correct += progress.times_correct or 0
                total_incorrect += progress.times_incorrect or 0
                total_reviews += (progress.times_correct or 0) + (progress.times_incorrect or 0)
                
                if progress.last_review:
                    if not last_reviewed or progress.last_review > last_reviewed:
                        last_reviewed = progress.last_review
        
        learned_count = len(progress_records)
        completion_pct = (learned_count / total * 100) if total > 0 else 0
        retrievability_avg = (total_retrievability / learned_count) if learned_count > 0 else 0
        accuracy_pct = (total_correct / (total_correct + total_incorrect) * 100) if (total_correct + total_incorrect) > 0 else 0
        
        from mindstack_app.modules.fsrs.services.hard_item_service import FSRSHardItemService as HardItemService
        hard_count = HardItemService.get_hard_count(user_id, container_id)
        
        return {
            'total': total,
            'new': new_count,
            'learning': learning_count,
            'mastered': mastered_count,
            'due': due_count,
            'hard': hard_count,
            'learned': learned_count,
            'completion_pct': round(completion_pct, 1),
            'retrievability_avg': round(retrievability_avg, 2),
            'mastery_avg': round(retrievability_avg, 2),
            'accuracy_pct': round(accuracy_pct, 1),
            'total_reviews': total_reviews,
            'total_correct': total_correct,
            'total_incorrect': total_incorrect,
            'last_reviewed': last_reviewed.isoformat() if last_reviewed else None
        }
    
    @staticmethod
    def _empty_stats() -> dict:
        return {
            'total': 0, 'new': 0, 'learning': 0, 'mastered': 0,
            'due': 0, 'hard': 0, 'learned': 0,
            'completion_pct': 0, 'retrievability_avg': 0, 'mastery_avg': 0, 'accuracy_pct': 0,
            'total_reviews': 0, 'total_correct': 0, 'total_incorrect': 0,
            'last_reviewed': None
        }
    
    @staticmethod
    def get_mode_counts(user_id: int, container_id: int) -> dict:
        stats = VocabularyContainerStats.get_full_stats(user_id, container_id)
        return {
            'new': stats['new'],
            'due': stats['due'],
            'review': stats['due'],
            'learned': stats['learned'],
            'hard': stats['hard'],
            'total': stats['total'],
            'random': stats['total']
        }
    
    
    @staticmethod
    def get_chart_data(user_id: int, container_id: int) -> dict:
        from datetime import timedelta
        from collections import defaultdict
        
        items = LearningItem.query.filter(
            LearningItem.container_id == container_id,
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        ).all()
        
        item_ids = [item.item_id for item in items]
        if not item_ids:
            return {'distribution': {'weak': 0, 'medium': 0, 'strong': 0}, 'timeline': {'dates': [], 'values': []}}
        
        progress_records = ItemMemoryState.query.filter(
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.item_id.in_(item_ids)
        ).all()
        
        weak_count = medium_count = strong_count = 0
        for progress in progress_records:
            retrievability = FsrsService.get_retrievability(progress)
            if retrievability < 0.7: weak_count += 1
            elif retrievability < 0.9: medium_count += 1
            else: strong_count += 1
        
        now = datetime.now(timezone.utc)
        timeline_data = defaultdict(list)
        start_date = now - timedelta(days=30)
        
        logs = StudyLog.query.filter(
            StudyLog.user_id == user_id,
            StudyLog.item_id.in_(item_ids),
            StudyLog.timestamp >= start_date
        ).order_by(StudyLog.timestamp).all()
        
        for log in logs:
            date_key = log.timestamp.strftime('%d/%m')
            fsrs = log.fsrs_snapshot or {}
            stability = fsrs.get('stability')
            if stability is not None:
                timeline_data[date_key].append(min((stability)/21.0, 1.0) * 100)
        
        dates = []
        values = []
        for i in range(29, -1, -1):
            date = now - timedelta(days=i)
            date_key = date.strftime('%d/%m')
            dates.append(date_key)
            if date_key in timeline_data and timeline_data[date_key]:
                values.append(round(sum(timeline_data[date_key]) / len(timeline_data[date_key]), 1))
            else:
                values.append(None)
        
        return {
            'distribution': {'weak': weak_count, 'medium': medium_count, 'strong': strong_count},
            'timeline': {'dates': dates, 'values': values}
        }
    
    @staticmethod
    def get_hard_count(user_id: int, container_id: int) -> int:
        stats = VocabularyContainerStats.get_full_stats(user_id, container_id)
        return stats['hard']

VocabularyStatsService = VocabularyContainerStats