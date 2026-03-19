"""
StudyPlannerInterface - Public API (Gatekeeper)
================================================
Other modules MUST use this interface to interact with the Study Planner.
"""

from __future__ import annotations

from datetime import date
from typing import Optional


class StudyPlannerInterface:
    """Public API for the Study Planner module."""

    @staticmethod
    def has_active_plan(user_id: int, container_id: int) -> bool:
        """Check if a user has an active plan for a container."""
        from .services.planner_service import PlannerService
        return PlannerService.get_active_plan(user_id, container_id) is not None

    @staticmethod
    def get_plan_summary(user_id: int, container_id: int) -> Optional[dict]:
        """
        Get a summary of the active plan for display in dashboards.
        
        Returns None if no active plan, otherwise returns dict with:
        - plan: plan details
        - today: today's target/actual/progress
        - overall: overall progress
        - prediction: predicted end date
        - motivation: motivational message
        """
        from .services.planner_service import PlannerService
        return PlannerService.get_today_status(user_id, container_id)

    @staticmethod
    def create_plan(user_id: int, container_id: int, target_end_date: date, title: Optional[str] = None):
        """Create a new study plan."""
        from .services.planner_service import PlannerService
        return PlannerService.create_plan(user_id, container_id, target_end_date, title)

    @staticmethod
    def update_plan_date(plan_id: int, new_end_date: date):
        """Update the target end date of a plan."""
        from .services.planner_service import PlannerService
        return PlannerService.update_target_date(plan_id, new_end_date)

    @staticmethod
    def cancel_plan(plan_id: int):
        """Cancel an active plan."""
        from .services.planner_service import PlannerService
        return PlannerService.cancel_plan(plan_id)

    @staticmethod
    def get_plan_history(plan_id: int) -> list[dict]:
        """Get daily log history for a plan."""
        from .services.planner_service import PlannerService
        return PlannerService.get_plan_history(plan_id)
