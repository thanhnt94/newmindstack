from typing import List, Optional, Dict, Any
from .schemas import BadgeDTO, StreakDTO
from .services.scoring_service import ScoreService
from .services.badges_service import BadgeService
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

def get_user_progress(user_id: int) -> Dict[str, Any]:
    """
    Get gamification progress for a user.
    Used by stats module for aggregated dashboard data.
    
    Returns:
        dict with: current_streak, longest_streak, total_xp, level
    """
    from mindstack_app.models import User
    
    user = User.query.get(user_id)
    streak = StreakService.get_user_streak(user_id)
    
    total_xp = user.total_score if user else 0
    
    # Calculate level from XP (simple formula: level = floor(sqrt(xp / 100)))
    import math
    level = int(math.sqrt(total_xp / 100)) if total_xp > 0 else 1
    
    return {
        'current_streak': streak.current_streak if streak else 0,
        'longest_streak': streak.longest_streak if streak else 0,
        'total_xp': total_xp or 0,
        'level': max(1, level),
    }

def get_leaderboard(limit: int = 10, period: str = 'all_time') -> List[Dict[str, Any]]:
    """
    Get leaderboard data.
    Delegates to ScoreService.
    """
    return ScoreService.get_leaderboard(limit, period)


def get_user_score(user_id: int) -> int:
    """Get total score for a user."""
    from mindstack_app.models import User
    user = User.query.get(user_id)
    return user.total_score if user else 0



def record_daily_login(user_id: int):
    """Record daily login for points/streaks."""
    return ScoreService.record_daily_login(user_id)


def sync_all_users_scores() -> Dict[str, Any]:
    """Sync all users' total scores from ScoreLogs."""
    return ScoreService.sync_all_users_scores()


def delete_user_gamification_data(user_id: int) -> bool:
    """
    Delete all gamification data for a user.
    Used by Ops/Reset service.
    """
    return ScoreService.delete_user_data(user_id)

def delete_items_gamification_data(user_id: int, item_ids: List[int]) -> bool:
    """
    Delete gamification data for specific items.
    Used by Ops/Reset service.
    """
    return ScoreService.delete_items_data(user_id, item_ids)

