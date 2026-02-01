from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass
class GoalDTO:
    id: int
    user_id: int
    goal_code: str
    target_value: int
    period: str
    current_value: Optional[int] = 0
    is_met: bool = False
    start_date: Optional[date] = None
    end_date: Optional[date] = None
