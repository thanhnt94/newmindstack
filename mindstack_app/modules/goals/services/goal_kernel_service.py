"""
Goal Kernel Service
Low-level CRUD operations for Goal Management System.
Connects with 'goals', 'user_goals', 'goal_progress_logs' tables.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List

from mindstack_app.core.extensions import db
from ..models import Goal, UserGoal, GoalProgress
from sqlalchemy.dialects.postgresql import insert

class GoalKernelService:

    @staticmethod
    def create_goal_definition(
        code: str,
        title: str,
        metric: str,
        description: str = None,
        domain: str = 'general',
        default_period: str = 'daily',
        default_target: int = 10,
        icon: str = 'star'
    ) -> Goal:
        """Create or update a system goal definition."""
        existing = Goal.query.get(code)
        if existing:
            existing.title = title
            existing.metric = metric
            existing.description = description
            existing.domain = domain
            existing.default_period = default_period
            existing.default_target = default_target
            existing.icon = icon
            db.session.add(existing)
            return existing
        
        goal = Goal(
            goal_code=code,
            title=title,
            metric=metric,
            description=description,
            domain=domain,
            default_period=default_period,
            default_target=default_target,
            icon=icon
        )
        db.session.add(goal)
        # Note: caller must commit
        return goal

    @staticmethod
    def ensure_user_goal(
        user_id: int,
        goal_code: str,
        target_override: Optional[int] = None,
        scope: str = 'global',
        reference_id: Optional[int] = None
    ) -> UserGoal:
        """Assign a goal to a user if not already assigned."""
        existing = UserGoal.query.filter_by(
            user_id=user_id,
            goal_code=goal_code,
            scope=scope,
            reference_id=reference_id
        ).first()

        if existing:
            if not existing.is_active:
                existing.is_active = True
                db.session.add(existing)
            return existing

        # Fetch template for defaults
        template = Goal.query.get(goal_code)
        if not template:
            raise ValueError(f"Goal template '{goal_code}' not found")

        new_goal = UserGoal(
            user_id=user_id,
            goal_code=goal_code,
            target_value=target_override if target_override is not None else template.default_target,
            period=template.default_period,
            scope=scope,
            reference_id=reference_id,
            is_active=True
        )
        db.session.add(new_goal)
        return new_goal

    @staticmethod
    def get_user_goals(user_id: int, active_only: bool = True) -> List[UserGoal]:
        query = UserGoal.query.filter_by(user_id=user_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()

    @staticmethod
    def update_progress(
        user_goal_id: int, 
        current_value: int, 
        date_obj: Optional[datetime.date] = None
    ) -> tuple[GoalProgress, bool]:
        """
        Update progress for a specific date. 
        Returns (progress_record, is_just_completed).
        """
        if not date_obj:
            date_obj = datetime.now(timezone.utc).date()

        user_goal = UserGoal.query.get(user_goal_id)
        if not user_goal:
            raise ValueError("UserGoal not found")

        # Find or Create progress log
        progress = GoalProgress.query.filter_by(
            user_goal_id=user_goal_id,
            date=date_obj
        ).first()

        newly_met = False
        was_met = False
        if progress:
            was_met = progress.is_met
            progress.current_value = current_value
            progress.target_snapshot = user_goal.target_value
            # Check completion
            is_met = current_value >= user_goal.target_value
            progress.is_met = is_met
            progress.last_updated = datetime.now(timezone.utc)
            
            if not was_met and is_met:
                newly_met = True
        else:
            is_met = current_value >= user_goal.target_value
            progress = GoalProgress(
                user_goal_id=user_goal_id,
                date=date_obj,
                current_value=current_value,
                target_snapshot=user_goal.target_value,
                is_met=is_met
            )
            if is_met:
                newly_met = True
            db.session.add(progress)

        return progress, newly_met

    @staticmethod
    def increment_daily_progress(
        user_goal_id: int, 
        amount: int, 
        date_obj: Optional[datetime.date] = None
    ) -> tuple[GoalProgress, bool]:
        """
        Increment the progress value for the day by a specific amount.
        Returns (progress_record, is_just_completed).
        """
        if not date_obj:
            date_obj = datetime.now(timezone.utc).date()
            
        user_goal = UserGoal.query.get(user_goal_id)
        if not user_goal:
            raise ValueError("UserGoal not found")

        progress = GoalProgress.query.filter_by(
            user_goal_id=user_goal_id,
            date=date_obj
        ).first()
        
        current_value = amount
        if progress:
            current_value += progress.current_value
            
        return GoalKernelService.update_progress(user_goal_id, current_value, date_obj)
