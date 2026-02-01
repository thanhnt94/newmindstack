from typing import List, Optional
from .schemas import BadgeDTO, StreakDTO
from .services.scoring_service import ScoreService
from .services.badge_service import BadgeService
from .services.streak_service import StreakService

def award_points(user_id: int, amount: int, reason: str, item_id: Optional[int] = None, item_type: Optional[str] = None):
    """Public API to award points."""
    return ScoreService.award_points(user_id, amount, reason, item_id, item_type)

def get_user_badges(user_id: int) -> List[BadgeDTO]:
    """Get earned badges for a user."""
    # Mapping logic needed or service returns DTOs.
    # For now, placeholder.
    return []

def get_streak(user_id: int) -> StreakDTO:
    """Get user streak."""
    # Mapping logic needed
    streak = StreakService.get_user_streak(user_id)
    if not streak:
        return StreakDTO(user_id, 0, 0, None)
    return StreakDTO(
        user_id, 
        streak.current_streak, 
        streak.longest_streak, 
        streak.last_activity_date.isoformat() if streak.last_activity_date else None
    )
