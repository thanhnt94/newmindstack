from typing import List, Optional
from .schemas import GoalDTO
from .services.goal_kernel_service import GoalKernelService

def get_user_goals(user_id: int) -> List[GoalDTO]:
    """Get active goals for a user."""
    # This requires mapping from DB model to DTO.
    # For now, just a placeholder.
    # Ideally GoalKernelService should return DTOs or we map here.
    return []

def create_user_goal(user_id: int, goal_code: str, target: int, period: str = 'daily'):
    """Create a new goal for user."""
    return GoalKernelService.ensure_user_goal(user_id, goal_code, target_override=target)
