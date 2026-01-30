"""
Goal Orchestrator
Listens to system events and updates goal progress.
"""
from mindstack_app.core.signals import session_completed, goal_completed
from mindstack_app.modules.goals.services.goal_kernel_service import GoalKernelService
from mindstack_app.db_instance import db

def handle_session_completed(sender, **kwargs):
    """
    Listener for session_completed signal.
    """
    user_id = kwargs.get('user_id')
    items_reviewed = kwargs.get('items_reviewed', 0)
    items_correct = kwargs.get('items_correct', 0)
    # Add other metrics as needed
    
    if not user_id:
        return

    # Get active goals for user
    # Ideally filtering by relevant types only, but getting all active for user is fine for now
    user_goals = GoalKernelService.get_user_goals(user_id)
    
    updates_pending = False
    
    for user_goal in user_goals:
        # Metric matching
        # Assuming definition is loaded (lazy load in loop is okay for small N)
        metric = user_goal.definition.metric
        increment = 0
        
        if metric == 'items_reviewed':
            increment = items_reviewed
        elif metric == 'items_correct':
            increment = items_correct
        
        # TODO: Handle 'points' if signal provides it
        
        if increment > 0:
            # We use increment_daily_progress which fetches GoalProgress
            progress, just_completed = GoalKernelService.increment_daily_progress(
                user_goal.user_goal_id, increment
            )
            updates_pending = True
            
            if just_completed:
                # Emit goal completed signal
                goal_completed.send(
                    sender='goal_orchestrator',
                    user_id=user_id,
                    goal_id=user_goal.user_goal_id,
                    goal_title=user_goal.definition.title
                )

    if updates_pending:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # print(f"Error updating goals: {e}")

def init_orchestrator():
    session_completed.connect(handle_session_completed)
