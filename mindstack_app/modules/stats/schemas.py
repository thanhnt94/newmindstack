from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, List, Dict, Any

@dataclass
class MetricDTO:
    """Represents a single statistical metric."""
    user_id: int
    key: str
    value: float
    updated_at: datetime

@dataclass
class DailyStatDTO:
    """Represents a daily aggregate stat."""
    user_id: int
    date: date
    key: str
    value: float

@dataclass
class UserLearningSummaryDTO:
    """Summary of user's learning progress across modes."""
    user_id: int
    total_score: int
    active_days: int
    last_activity: Optional[datetime]
    streak: Dict[str, int] # current, longest
    modes: Dict[str, Dict[str, Any]] # flashcard, quiz, course stats

@dataclass
class LeaderboardEntryDTO:
    """Entry in the leaderboard."""
    user_id: int
    username: str
    avatar_url: Optional[str]
    score: float
    rank: int
    is_viewer: bool = False
