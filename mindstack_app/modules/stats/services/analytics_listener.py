"""
Analytics Listener
Listens to system signals and updates statistical models (UserMetric, DailyStat).
This is the 'Writer' component of the Analytics system.
"""
from datetime import datetime, timezone
from mindstack_app.core.signals import session_completed, user_logged_in, score_awarded
from mindstack_app.modules.stats.services.metrics_kernel import MetricsKernel
from flask import current_app

def init_analytics_listener():
    """Register signal subscriptions."""
    session_completed.connect(on_session_completed)
    user_logged_in.connect(on_user_logged_in)
    score_awarded.connect(on_score_awarded)

def on_session_completed(sender, **kwargs):
    """
    Handle session completion.
    Payload: user_id, items_reviewed, items_correct, session_duration_minutes
    """
    user_id = kwargs.get('user_id')
    duration_mins = kwargs.get('session_duration_minutes', 0)
    items_count = kwargs.get('items_reviewed', 0)
    
    if not user_id:
        return

    try:
        # Total Global Metrics
        MetricsKernel.increment_user_metric(user_id, 'total_sessions', 1)
        MetricsKernel.increment_user_metric(user_id, 'total_study_minutes', duration_mins)
        MetricsKernel.increment_user_metric(user_id, 'total_items_reviewed', items_count)
        
        # Daily Stats
        today = datetime.now(timezone.utc).date()
        MetricsKernel.increment_daily_stat(user_id, 'sessions_count', 1, date_obj=today)
        MetricsKernel.increment_daily_stat(user_id, 'minutes_learned', duration_mins, date_obj=today)
        MetricsKernel.increment_daily_stat(user_id, 'items_reviewed', items_count, date_obj=today)
        
    except Exception as e:
        current_app.logger.error(f"Error updating analytics for session: {e}")

def on_user_logged_in(sender, **kwargs):
    """
    Handle user login.
    Payload: user (User object)
    """
    user = kwargs.get('user')
    if not user:
        return

    try:
        # Update login count
        MetricsKernel.increment_user_metric(user.user_id, 'total_logins', 1)
        # Streak logic could go here or remain queried from history
        
    except Exception as e:
        current_app.logger.error(f"Error updating analytics for login: {e}")

def on_score_awarded(sender, **kwargs):
    """
    Handle score updates.
    Payload: user_id, amount
    """
    user_id = kwargs.get('user_id')
    amount = kwargs.get('amount', 0)
    
    if not user_id or amount == 0:
        return
        
    try:
        today = datetime.now(timezone.utc).date()
        MetricsKernel.increment_daily_stat(user_id, 'score_earned', amount, date_obj=today)
        MetricsKernel.increment_user_metric(user_id, 'total_lifetime_score', amount)
    except Exception as e:
        current_app.logger.error(f"Error updating analytics for score: {e}")
