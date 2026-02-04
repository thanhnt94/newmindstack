# File: mindstack_app/modules/stats/services/stats_aggregator.py
"""
Stats Aggregator Service
========================
Aggregates statistics from multiple modules via their public interfaces.

This service follows the Data Aggregator pattern:
- DOES NOT import models from other modules
- ONLY calls module interfaces
- Handles errors gracefully with fallback values
"""

from typing import Dict, Any, Optional
from flask import current_app


class StatsAggregator:
    """
    Aggregates statistics from multiple modules.
    
    This is the single entry point for getting unified dashboard stats.
    All data is fetched via module interfaces, ensuring loose coupling.
    """
    
    @staticmethod
    def get_user_dashboard_stats(user_id: int) -> Dict[str, Any]:
        """
        Get unified dashboard statistics from all modules.
        
        Aggregates data from:
        - fsrs.interface: FSRS/SRS stats
        - gamification.interface: XP, streak, level
        - learning_history.interface: Activity heatmap (if available)
        
        Returns:
            Merged dict with all stats, using default values on errors
        """
        result = {
            'user_id': user_id,
            'fsrs': StatsAggregator._get_fsrs_stats(user_id),
            'gamification': StatsAggregator._get_gamification_stats(user_id),
            'activity': StatsAggregator._get_activity_stats(user_id),
        }
        
        return result
    
    @staticmethod
    def _get_fsrs_stats(user_id: int) -> Dict[str, Any]:
        """Get FSRS stats via interface with error handling."""
        try:
            from mindstack_app.modules.fsrs.interface import FSRSInterface
            return FSRSInterface.get_global_stats(user_id)
        except Exception as e:
            current_app.logger.error(f"[StatsAggregator] FSRS stats error: {e}")
            return {
                'total_cards': 0,
                'due_count': 0,
                'mastered_count': 0,
                'average_retention': 0.0,
                'average_stability': 0.0,
            }
    
    @staticmethod
    def _get_gamification_stats(user_id: int) -> Dict[str, Any]:
        """Get gamification stats via interface with error handling."""
        try:
            from mindstack_app.modules.gamification import interface as gamification_interface
            return gamification_interface.get_user_progress(user_id)
        except Exception as e:
            current_app.logger.error(f"[StatsAggregator] Gamification stats error: {e}")
            return {
                'current_streak': 0,
                'longest_streak': 0,
                'total_xp': 0,
                'level': 1,
            }
    
    @staticmethod
    def _get_activity_stats(user_id: int) -> Dict[str, Any]:
        """Get activity/heatmap stats via interface with error handling."""
        try:
            # Try to get heatmap data from learning_history if available
            from mindstack_app.modules.learning_history.interface import LearningHistoryInterface
            heatmap = LearningHistoryInterface.get_activity_heatmap(user_id, days=90)
            
            # Calculate summary stats from heatmap
            total_sessions = sum(day.get('count', 0) for day in heatmap)
            active_days = len([d for d in heatmap if d.get('count', 0) > 0])
            
            return {
                'heatmap': heatmap,
                'total_sessions_90d': total_sessions,
                'active_days_90d': active_days,
            }
        except ImportError:
            # learning_history module may not have this interface yet
            return {
                'heatmap': [],
                'total_sessions_90d': 0,
                'active_days_90d': 0,
            }
        except Exception as e:
            current_app.logger.error(f"[StatsAggregator] Activity stats error: {e}")
            return {
                'heatmap': [],
                'total_sessions_90d': 0,
                'active_days_90d': 0,
            }
    
    @staticmethod
    def get_container_summary(user_id: int, container_id: int) -> Dict[str, Any]:
        """
        Get stats summary for a specific container.
        
        Returns:
            dict with FSRS stats for the container
        """
        try:
            from mindstack_app.modules.fsrs.interface import FSRSInterface
            return FSRSInterface.get_container_stats(user_id, container_id)
        except Exception as e:
            current_app.logger.error(f"[StatsAggregator] Container stats error: {e}")
            return {
                'total': 0,
                'learned': 0,
                'due': 0,
                'mastered': 0,
                'avg_stability': 0.0
            }
