"""
Analytics Service - Consolidated service for dashboard data.

Provides a single entry point for all dashboard metrics,
reducing the complexity in routes.
"""
from datetime import date, timedelta
from typing import Dict, Any, Optional

from flask import current_app

from mindstack_app.models import db
from mindstack_app.models.learning_progress import LearningProgress

from .metrics import (
    get_user_container_options,
    get_activity_breakdown,
    get_score_trend_series,
    ITEM_TYPE_LABELS,
)
from ..logics.chart_utils import resolve_timeframe_dates


class AnalyticsService:
    """
    Consolidated analytics service for dashboard.
    
    Wraps multiple service calls into clean, high-level methods
    that return complete data for templates.
    """
    
    @staticmethod
    def get_dashboard_overview(
        user_id: int, 
        timeframe: str = 'all_time',
        sort_by: str = 'total_score',
        viewer_user = None
    ) -> Dict[str, Any]:
        """
        Get all dashboard data in a single call.
        
        Returns:
            Complete dict with all data needed for dashboard template:
            - dashboard_data: Aggregated metrics dict
            - daily_summary: Today/week stats from DailyStatsService
            - leaderboard_data: Sorted leaderboard
            - flashcard_sets, quiz_sets, course_sets: Container options
            - recent_activity, recent_sessions: Activity lists
        """
        from mindstack_app.modules.learning.services.learning_metrics_service import LearningMetricsService
        from mindstack_app.modules.learning.services.daily_stats_service import DailyStatsService
        
        # 1. Get leaderboard
        leaderboard_data = LearningMetricsService.get_leaderboard(
            sort_by=sort_by,
            timeframe=timeframe or 'all_time',
            viewer_user=viewer_user
        )
        
        # 2. Get learning summary
        summary = LearningMetricsService.get_user_learning_summary(user_id)
        
        # 3. Get container options
        containers = AnalyticsService.get_all_container_options(user_id)
        
        # 4. Build dashboard_data dict
        dashboard_data = AnalyticsService._build_dashboard_data(
            user_id, summary, containers['flashcard_sets']
        )
        
        # 5. Get daily summary
        try:
            daily_summary = DailyStatsService.get_summary(user_id)
            if daily_summary and 'streak' in daily_summary:
                dashboard_data['current_learning_streak'] = daily_summary['streak']['current_streak']
                dashboard_data['longest_learning_streak'] = daily_summary['streak']['longest_streak']
        except Exception as e:
            current_app.logger.error(f"Error fetching daily stats: {e}")
            daily_summary = AnalyticsService._get_fallback_daily_summary()
        
        # 6. Get recent activity
        recent_activity = LearningMetricsService.get_recent_activity(user_id)
        recent_sessions = LearningMetricsService.get_recent_sessions(user_id)
        
        return {
            'leaderboard_data': leaderboard_data,
            'dashboard_data': dashboard_data,
            'daily_summary': daily_summary,
            'current_sort_by': sort_by,
            'current_timeframe': timeframe,
            'flashcard_sets': containers['flashcard_sets'],
            'quiz_sets': containers['quiz_sets'],
            'course_sets': containers['course_sets'],
            'recent_activity': recent_activity,
            'recent_sessions': recent_sessions,
        }
    
    @staticmethod
    def get_all_container_options(user_id: int) -> Dict[str, list]:
        """
        Get all container options in one call.
        
        Returns:
            Dict with keys: flashcard_sets, quiz_sets, course_sets
        """
        return {
            'flashcard_sets': get_user_container_options(
                user_id,
                'FLASHCARD_SET',
                LearningProgress.MODE_FLASHCARD,
                'last_reviewed',
                item_type='FLASHCARD',
            ),
            'quiz_sets': get_user_container_options(
                user_id,
                'QUIZ_SET',
                LearningProgress.MODE_QUIZ,
                'last_reviewed',
                item_type='QUIZ_MCQ',
            ),
            'course_sets': get_user_container_options(
                user_id,
                'COURSE',
                LearningProgress.MODE_COURSE,
                'last_reviewed',
                item_type='LESSON',
            ),
        }
    
    @staticmethod
    def get_score_by_type(user_id: int, timeframe: str = 'all') -> Dict[str, int]:
        """
        Get score breakdown by item type.
        
        Returns:
            Dict with keys: flashcard_score, quiz_score, course_score, other_score
        """
        breakdown = get_activity_breakdown(user_id, timeframe)
        
        result = {
            'flashcard_score': 0,
            'quiz_score': 0,
            'course_score': 0,
            'other_score': 0,
            'total_score': breakdown.get('total_score', 0),
        }
        
        for bucket in breakdown.get('buckets', []):
            item_type = bucket.get('item_type', '')
            score = bucket.get('score', 0)
            
            if item_type == 'FLASHCARD':
                result['flashcard_score'] = score
            elif item_type == 'QUIZ_MCQ':
                result['quiz_score'] = score
            elif item_type in ['LESSON', 'COURSE']:
                result['course_score'] += score
            else:
                result['other_score'] += score
        
        return result
    
    @staticmethod
    def _build_dashboard_data(
        user_id: int, 
        summary: Dict[str, Any],
        flashcard_sets: list
    ) -> Dict[str, Any]:
        """Build the dashboard_data dict from summary data."""
        fc = summary.get('flashcard', {})
        qz = summary.get('quiz', {})
        co = summary.get('course', {})
        
        # Get score breakdown
        scores_all = AnalyticsService.get_score_by_type(user_id, 'all')
        scores_30d = AnalyticsService.get_score_by_type(user_id, '30d')
        
        active_days = summary.get('active_days', 0)
        total_score = summary.get('total_score', 0)
        
        return {
            # Flashcard metrics
            'flashcard_score': scores_all.get('flashcard_score', 0),
            'learned_distinct_overall': fc.get('total', 0),
            'learned_sets_count': len(flashcard_sets),
            'flashcard_accuracy_percent': fc.get('accuracy_percent', 0),
            'flashcard_attempt_total': fc.get('attempt_total', 0),
            'flashcard_correct_total': fc.get('correct_total', 0),
            'flashcard_incorrect_total': fc.get('incorrect_total', 0),
            'flashcard_mastered_count': fc.get('mastered', 0),
            'flashcard_avg_streak_overall': fc.get('avg_streak', 0),
            'flashcard_best_streak_overall': fc.get('best_streak', 0),
            
            # Quiz metrics
            'quiz_score': scores_all.get('quiz_score', 0),
            'questions_answered_count': qz.get('total_questions_encountered', 0),
            'quiz_sets_started_count': qz.get('sets_started', 0),
            'quiz_accuracy_percent': qz.get('accuracy_percent', 0),
            'quiz_attempt_total': qz.get('attempt_total', 0),
            'quiz_correct_total': qz.get('correct_total', 0),
            'quiz_incorrect_total': qz.get('incorrect_total', 0),
            'quiz_mastered_count': qz.get('mastered', 0),
            'quiz_avg_streak_overall': qz.get('avg_streak', 0),
            'quiz_best_streak_overall': qz.get('best_streak', 0),
            
            # Course metrics
            'courses_started_count': co.get('courses_started', 0),
            'lessons_completed_count': co.get('completed_lessons', 0),
            'courses_in_progress_count': co.get('in_progress_lessons', 0),
            'course_avg_completion_percent': co.get('avg_completion', 0),
            'course_last_progress': co.get('last_progress').isoformat() if co.get('last_progress') else None,
            
            # Overall metrics
            'total_score_all_time': total_score,
            'total_activity_entries': summary.get('total_entries', 0),
            'active_days': active_days,
            'average_daily_score': round(total_score / active_days, 1) if active_days else 0,
            
            # Recent metrics
            'total_score_last_30_days': scores_30d.get('total_score', 0),
            'average_daily_score_recent': round(scores_30d.get('total_score', 0) / 30, 1),
            'last_activity': summary.get('last_activity').isoformat() if summary.get('last_activity') else None,
            'current_learning_streak': summary.get('current_streak', 0),
            'longest_learning_streak': summary.get('longest_streak', 0),
        }
    
    @staticmethod
    def _get_fallback_daily_summary() -> Dict[str, Any]:
        """Return fallback daily summary when service fails."""
        today = date.today()
        return {
            'today': {
                'sessions': 0, 'items_studied': 0, 'new_items': 0,
                'reviewed_items': 0, 'accuracy': 0, 'correct': 0,
                'incorrect': 0, 'points': 0, 'by_mode': {}
            },
            'week': {
                'daily': [
                    {
                        'date': (today - timedelta(days=i)).isoformat(),
                        'sessions': 0, 'items_studied': 0, 'points': 0, 'by_mode': {}
                    }
                    for i in range(7)
                ],
                'totals': {
                    'sessions': 0, 'items_studied': 0, 'new_items': 0,
                    'correct': 0, 'incorrect': 0, 'accuracy': 0
                }
            },
            'streak': {'current_streak': 0, 'longest_streak': 0}
        }
