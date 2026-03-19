"""
PlannerEngine - Pure Logic Layer
=================================
Contains all calculation logic for the Study Planner.
NO database access, NO Flask imports. Pure Python only.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Optional


class PlannerEngine:
    """Pure calculation engine for study planning."""

    @staticmethod
    def calculate_daily_target(remaining_items: int, days_left: int) -> int:
        """
        Calculate how many new cards to learn today.
        
        Args:
            remaining_items: Number of items still to learn.
            days_left: Number of days remaining until target_end_date (inclusive of today).
            
        Returns:
            Daily target (minimum 1 if items remain, 0 if done).
        """
        if remaining_items <= 0:
            return 0
        if days_left <= 0:
            # Past deadline — all remaining items should be done ASAP
            return remaining_items
        return math.ceil(remaining_items / days_left)

    @staticmethod
    def predict_completion_date(
        remaining_items: int,
        avg_daily_pace: float,
        from_date: Optional[date] = None
    ) -> Optional[date]:
        """
        Predict when the user will finish based on their average pace.
        
        Args:
            remaining_items: Items still to learn.
            avg_daily_pace: Average new cards learned per day (calculated from history).
            from_date: Starting point for prediction (default: today).
            
        Returns:
            Predicted completion date, or None if pace is 0.
        """
        if remaining_items <= 0:
            return from_date or date.today()
        if avg_daily_pace <= 0:
            return None  # Cannot predict, no learning activity

        days_needed = math.ceil(remaining_items / avg_daily_pace)
        start = from_date or date.today()
        return start + timedelta(days=days_needed)

    @staticmethod
    def calculate_avg_pace(daily_logs: list[dict]) -> float:
        """
        Calculate average daily pace from historical logs.
        
        Args:
            daily_logs: List of dicts with 'actual_new_cards' key.
                        Only considers logs with actual > 0 (active days).
            
        Returns:
            Average cards per day (float). Returns 0.0 if no active days.
        """
        active_days = [log['actual_new_cards'] for log in daily_logs if log.get('actual_new_cards', 0) > 0]
        if not active_days:
            return 0.0
        return sum(active_days) / len(active_days)

    @staticmethod
    def get_progress_percentage(actual: int, target: int) -> float:
        """Calculate progress percentage for today."""
        if target <= 0:
            return 100.0 if actual > 0 else 0.0
        return min(round((actual / target) * 100, 1), 999.9)

    @staticmethod
    def get_overall_progress(learned_since_start: int, items_to_learn: int) -> float:
        """Calculate overall plan progress percentage."""
        if items_to_learn <= 0:
            return 100.0
        return min(round((learned_since_start / items_to_learn) * 100, 1), 100.0)

    @staticmethod
    def get_motivation_message(today_pct: float, overall_pct: float) -> dict:
        """
        Generate a motivation message based on today's progress.
        
        Returns:
            dict with 'message', 'emoji', 'tone' keys.
        """
        if overall_pct >= 100.0:
            return {
                'message': 'Chúc mừng! Bạn đã hoàn thành toàn bộ kế hoạch học tập! 🎉',
                'emoji': '🎉',
                'tone': 'celebration'
            }

        if today_pct >= 150:
            return {
                'message': 'Hỏa tốc! Bạn đang bứt phá lộ trình, tuyệt vời lắm!',
                'emoji': '🔥',
                'tone': 'excellent'
            }
        if today_pct >= 100:
            return {
                'message': 'Hoàn hảo! Mục tiêu hôm nay đã xong, nghỉ ngơi thôi nào!',
                'emoji': '✅',
                'tone': 'perfect'
            }
        if today_pct >= 70:
            return {
                'message': 'Sắp tới nơi rồi! Chỉ một chút nỗ lực nữa thôi!',
                'emoji': '💪',
                'tone': 'almost'
            }
        if today_pct >= 30:
            return {
                'message': 'Đang tiến triển tốt, tiếp tục phát huy nhé!',
                'emoji': '📈',
                'tone': 'progress'
            }
        if today_pct > 0:
            return {
                'message': 'Khởi đầu tốt lắm! Hãy tiếp tục nhé.',
                'emoji': '🌱',
                'tone': 'started'
            }
        return {
            'message': 'Hôm nay chưa bắt đầu, hãy mở bộ thẻ ra học nào!',
            'emoji': '📚',
            'tone': 'not_started'
        }

    @staticmethod
    def calculate_days_ahead_or_behind(
        actual_cumulative: int,
        expected_cumulative: int,
        daily_target: int
    ) -> int:
        """
        Calculate how many days ahead/behind schedule.
        
        Returns:
            Positive = ahead, Negative = behind, 0 = on track.
        """
        if daily_target <= 0:
            return 0
        diff = actual_cumulative - expected_cumulative
        return round(diff / daily_target)
