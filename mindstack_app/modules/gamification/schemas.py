from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class BadgeDTO:
    id: int
    name: str
    description: Optional[str]
    icon_class: str
    earned_at: Optional[datetime]

@dataclass
class StreakDTO:
    user_id: int
    current_streak: int
    longest_streak: int
    last_activity_date: Optional[str]
