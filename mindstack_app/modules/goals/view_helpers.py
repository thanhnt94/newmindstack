"""Utility functions shared between goal-aware views."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from flask import url_for

from mindstack_app.core.extensions import db
from mindstack_app.models import UserGoal, GoalProgress
from .logics.calculation import calculate_percentage, get_progress_color_class

def build_goal_progress(user_goals: Iterable[UserGoal], metrics: dict[str, object] = None) -> list[dict[str, object]]:
    """Return a serialisable representation of the user's goals.
    
    Uses pre-calculated GoalProgress records updated by the Orchestrator.
    """
    progress_list = []
    
    today = datetime.now(timezone.utc).date()
    start_history = today - timedelta(days=6)
    
    for user_goal in user_goals:
        definition = user_goal.definition
        
        # 1. Get Current Progress
        todays_log = GoalProgress.query.filter_by(
            user_goal_id=user_goal.user_goal_id,
            date=today
        ).first()
        
        current_value = todays_log.current_value if todays_log else 0
        is_met = todays_log.is_met if todays_log else False
        percent = calculate_percentage(current_value, user_goal.target_value)
        
        # 2. Get History (Last 7 Days)
        past_logs = GoalProgress.query.filter(
            GoalProgress.user_goal_id == user_goal.user_goal_id,
            GoalProgress.date >= start_history,
            GoalProgress.date <= today
        ).all()
        
        log_map = {l.date: l.is_met for l in past_logs}
        history_7_days = []
        for i in range(6, -1, -1): # [6, 5... 0]
            d = today - timedelta(days=i)
            history_7_days.append(log_map.get(d, False))

        # 3. Determine UI Properties
        # TODO: Refactor URL logic properly
        final_url = url_for('dashboard.dashboard')
        if definition.domain == 'flashcard':
            final_url = url_for('vocab_flashcard.flashcard_dashboard_internal.dashboard')
        elif definition.domain == 'quiz':
            final_url = url_for('practice.quiz_dashboard')
        
        progress_list.append({
            'id': user_goal.user_goal_id,
            'title': definition.title,
            'description': definition.description,
            'period_label': user_goal.period.capitalize(), # simple formatting
            'current_value': current_value,
            'target_value': user_goal.target_value,
            'unit': 'items' if 'items' in definition.metric else 'points',
            'percent': percent,
            'url': final_url,
            'icon': definition.icon or 'star',
            'start_date': user_goal.start_date,
            'notes': '', 
            'is_active': user_goal.is_active,
            'domain': definition.domain,
            'is_completed': is_met,
            'history_7_days': history_7_days,
            'metric_label': definition.metric.replace('_', ' ').capitalize(),
            'color': get_progress_color_class(percent)
        })

    return progress_list
