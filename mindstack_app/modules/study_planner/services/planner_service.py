"""
PlannerService - Orchestration Layer
======================================
Handles all DB interactions for Study Plans.
Coordinates between models, engine, and external modules.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timezone, timedelta
from typing import Optional

from flask import current_app
from sqlalchemy import func as sa_func

from mindstack_app.core.extensions import db
from mindstack_app.models import LearningItem, ItemMemoryState

from ..models import StudyPlan, StudyPlanDailyLog
from ..engine.core import PlannerEngine


class PlannerService:
    """Orchestrates study plan operations."""

    # ──────────────────────────────────────────
    # Plan Lifecycle
    # ──────────────────────────────────────────

    @classmethod
    def create_plan(
        cls,
        user_id: int,
        container_id: int,
        target_end_date: date,
        title: Optional[str] = None
    ) -> StudyPlan:
        """
        Create a new study plan for a container.
        
        Raises ValueError if:
        - An active plan already exists for this user+container.
        - target_end_date is in the past or today.
        """
        # Check for existing active plan
        existing = cls.get_active_plan(user_id, container_id)
        if existing:
            raise ValueError("Bạn đã có một kế hoạch đang hoạt động cho bộ thẻ này. Hãy hủy kế hoạch cũ trước.")

        today = date.today()
        if target_end_date <= today:
            raise ValueError("Ngày mục tiêu phải nằm sau ngày hôm nay.")

        # Snapshot current state
        total_items = LearningItem.query.filter(
            LearningItem.container_id == container_id,
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        ).count()

        if total_items == 0:
            raise ValueError("Bộ thẻ này không có thẻ nào để học.")

        learned_count = db.session.query(sa_func.count(ItemMemoryState.state_id)).join(
            LearningItem, LearningItem.item_id == ItemMemoryState.item_id
        ).filter(
            LearningItem.container_id == container_id,
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.state != 0  # Not New
        ).scalar() or 0

        if learned_count >= total_items:
            raise ValueError("Bạn đã học hết tất cả thẻ trong bộ này rồi!")

        # Set title
        if not title:
            from mindstack_app.models import LearningContainer
            container = LearningContainer.query.get(container_id)
            title = f"Hoàn thành: {container.title}" if container else "Kế hoạch học tập"

        plan = StudyPlan(
            user_id=user_id,
            container_id=container_id,
            title=title,
            start_date=today,
            target_end_date=target_end_date,
            total_items=total_items,
            initial_learned=learned_count,
            status='active'
        )
        db.session.add(plan)
        db.session.flush()  # Get plan_id

        # Create today's daily log entry
        remaining = total_items - learned_count
        days_left = (target_end_date - today).days + 1  # inclusive
        daily_target = PlannerEngine.calculate_daily_target(remaining, days_left)

        today_log = StudyPlanDailyLog(
            plan_id=plan.plan_id,
            date=today,
            target_new_cards=daily_target,
            actual_new_cards=0,
            cumulative_learned=learned_count
        )
        db.session.add(today_log)
        db.session.commit()

        current_app.logger.info(
            f"[PLANNER] Created plan {plan.plan_id} for user {user_id}, "
            f"container {container_id}: {remaining} items in {days_left} days "
            f"(daily target: {daily_target})"
        )
        return plan

    @classmethod
    def get_active_plan(cls, user_id: int, container_id: int) -> Optional[StudyPlan]:
        """Get the active plan for a user+container, if any."""
        return StudyPlan.query.filter_by(
            user_id=user_id,
            container_id=container_id,
            status='active'
        ).first()

    @classmethod
    def get_plan_by_id(cls, plan_id: int) -> Optional[StudyPlan]:
        """Get a plan by ID."""
        return StudyPlan.query.get(plan_id)

    # ──────────────────────────────────────────
    # Daily Status
    # ──────────────────────────────────────────

    @classmethod
    def get_today_status(cls, user_id: int, container_id: int) -> Optional[dict]:
        """
        Get comprehensive status for today's plan progress.
        
        Returns None if no active plan exists.
        """
        plan = cls.get_active_plan(user_id, container_id)
        if not plan:
            return None

        today = date.today()
        today_log = cls._ensure_today_log(plan, today)

        # Current actual learned count (live from DB, not cached)
        current_learned = cls._get_current_learned_count(user_id, container_id)
        
        # Items learned since plan start
        learned_since_start = current_learned - plan.initial_learned
        items_to_learn = plan.items_to_learn
        remaining = max(0, items_to_learn - learned_since_start)

        # Days info
        days_total = (plan.target_end_date - plan.start_date).days + 1
        days_elapsed = (today - plan.start_date).days + 1
        days_left = max(0, (plan.target_end_date - today).days + 1)

        # Today's progress
        today_pct = PlannerEngine.get_progress_percentage(
            today_log.actual_new_cards, today_log.target_new_cards
        )
        overall_pct = PlannerEngine.get_overall_progress(learned_since_start, items_to_learn)

        # Prediction
        logs_data = [log.to_dict() for log in plan.daily_logs.all()]
        avg_pace = PlannerEngine.calculate_avg_pace(logs_data)
        predicted_end = PlannerEngine.predict_completion_date(remaining, avg_pace, today)

        # Motivation
        motivation = PlannerEngine.get_motivation_message(today_pct, overall_pct)

        # Check if plan should be auto-completed
        if remaining <= 0 and plan.status == 'active':
            plan.status = 'completed'
            plan.completed_at = datetime.now(timezone.utc)
            db.session.commit()

        return {
            'plan': plan.to_dict(),
            'today': {
                'date': today.isoformat(),
                'target': today_log.target_new_cards,
                'actual': today_log.actual_new_cards,
                'progress_pct': today_pct,
                'is_met': today_log.is_met,
            },
            'overall': {
                'items_to_learn': items_to_learn,
                'learned_since_start': learned_since_start,
                'remaining': remaining,
                'progress_pct': overall_pct,
                'days_total': days_total,
                'days_elapsed': days_elapsed,
                'days_left': days_left,
            },
            'prediction': {
                'avg_pace': round(avg_pace, 1),
                'predicted_end': predicted_end.isoformat() if predicted_end else None,
                'days_difference': (predicted_end - plan.target_end_date).days if predicted_end else None,
            },
            'motivation': motivation,
        }

    # ──────────────────────────────────────────
    # Progress Recording (called by events.py)
    # ──────────────────────────────────────────

    @classmethod
    def record_new_card_learned(cls, user_id: int, container_id: int) -> None:
        """
        Record that a new card was learned for the first time.
        Called by the card_reviewed signal handler.
        """
        plan = cls.get_active_plan(user_id, container_id)
        if not plan:
            return  # No active plan, nothing to do

        today = date.today()
        today_log = cls._ensure_today_log(plan, today)

        # Increment actual count
        today_log.actual_new_cards += 1

        # Update cumulative
        current_learned = cls._get_current_learned_count(user_id, container_id)
        today_log.cumulative_learned = current_learned

        # Check if met
        today_log.is_met = today_log.actual_new_cards >= today_log.target_new_cards

        # Check if plan is complete
        items_to_learn = plan.items_to_learn
        learned_since_start = current_learned - plan.initial_learned
        if learned_since_start >= items_to_learn:
            plan.status = 'completed'
            plan.completed_at = datetime.now(timezone.utc)
            current_app.logger.info(f"[PLANNER] Plan {plan.plan_id} completed! 🎉")

        db.session.commit()

    # ──────────────────────────────────────────
    # Plan Modifications
    # ──────────────────────────────────────────

    @classmethod
    def update_target_date(cls, plan_id: int, new_end_date: date) -> StudyPlan:
        """Update the plan's target end date and recalculate today's target."""
        plan = StudyPlan.query.get(plan_id)
        if not plan:
            raise ValueError("Kế hoạch không tồn tại.")
        if plan.status != 'active':
            raise ValueError("Chỉ có thể chỉnh sửa kế hoạch đang hoạt động.")

        today = date.today()
        if new_end_date <= today:
            raise ValueError("Ngày mục tiêu phải nằm sau ngày hôm nay.")

        plan.target_end_date = new_end_date

        # Recalculate today's target
        current_learned = cls._get_current_learned_count(plan.user_id, plan.container_id)
        remaining = max(0, plan.items_to_learn - (current_learned - plan.initial_learned))
        days_left = (new_end_date - today).days + 1
        new_target = PlannerEngine.calculate_daily_target(remaining, days_left)

        today_log = cls._ensure_today_log(plan, today)
        today_log.target_new_cards = new_target

        db.session.commit()
        current_app.logger.info(f"[PLANNER] Plan {plan_id} updated: new end={new_end_date}, daily target={new_target}")
        return plan

    @classmethod
    def cancel_plan(cls, plan_id: int) -> StudyPlan:
        """Cancel an active plan."""
        plan = StudyPlan.query.get(plan_id)
        if not plan:
            raise ValueError("Kế hoạch không tồn tại.")
        if plan.status != 'active':
            raise ValueError("Kế hoạch này đã kết thúc hoặc đã bị hủy.")

        plan.status = 'cancelled'
        db.session.commit()
        current_app.logger.info(f"[PLANNER] Plan {plan_id} cancelled.")
        return plan

    @classmethod
    def get_plan_history(cls, plan_id: int) -> list[dict]:
        """Get all daily logs for a plan."""
        plan = StudyPlan.query.get(plan_id)
        if not plan:
            return []
        return [log.to_dict() for log in plan.daily_logs.order_by(StudyPlanDailyLog.date.asc()).all()]

    # ──────────────────────────────────────────
    # Private Helpers
    # ──────────────────────────────────────────

    @classmethod
    def _ensure_today_log(cls, plan: StudyPlan, today: date) -> StudyPlanDailyLog:
        """Get or create today's daily log entry, recalculating target if new."""
        log = StudyPlanDailyLog.query.filter_by(plan_id=plan.plan_id, date=today).first()
        if log:
            return log

        # Calculate fresh target
        current_learned = cls._get_current_learned_count(plan.user_id, plan.container_id)
        remaining = max(0, plan.items_to_learn - (current_learned - plan.initial_learned))
        days_left = max(1, (plan.target_end_date - today).days + 1)
        daily_target = PlannerEngine.calculate_daily_target(remaining, days_left)

        log = StudyPlanDailyLog(
            plan_id=plan.plan_id,
            date=today,
            target_new_cards=daily_target,
            actual_new_cards=0,
            cumulative_learned=current_learned
        )
        db.session.add(log)
        db.session.flush()
        return log

    @classmethod
    def _get_current_learned_count(cls, user_id: int, container_id: int) -> int:
        """Get the number of items learned (state != 0) in a container."""
        return db.session.query(sa_func.count(ItemMemoryState.state_id)).join(
            LearningItem, LearningItem.item_id == ItemMemoryState.item_id
        ).filter(
            LearningItem.container_id == container_id,
            ItemMemoryState.user_id == user_id,
            ItemMemoryState.state != 0
        ).scalar() or 0
