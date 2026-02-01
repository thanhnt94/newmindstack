from ..models import Streak

class StreakService:
    @staticmethod
    def get_user_streak(user_id: int):
        """Get the streak record for a user."""
        return Streak.query.get(user_id)
