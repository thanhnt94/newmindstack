# File: mindstack_app/modules/fsrs/schemas.py
import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

# Standard FSRS Rating (1-4)
class Rating:
    Again = 1
    Hard = 2
    Good = 3
    Easy = 4

# FSRS Math State Constants
class CardStateEnum:
    NEW = 0
    LEARNING = 1
    REVIEW = 2
    RELEARNING = 3

@dataclass
class CardStateDTO:
    """DTO bridging Database (LearningProgress) and FSRS Engine."""
    stability: float = 0.0      # FSRS S (days)
    difficulty: float = 0.0     # FSRS D (1-10)
    elapsed_days: float = 0.0
    scheduled_days: float = 0.0 # Interval in days
    reps: int = 0
    lapses: int = 0
    state: int = CardStateEnum.NEW
    last_review: Optional[datetime.datetime] = None
    due: Optional[datetime.datetime] = None

@dataclass
class SrsResultDTO:
    """Result of processing a learning interaction."""
    next_review: datetime.datetime
    interval_minutes: int
    state: int
    stability: float
    difficulty: float
    retrievability: float
    correct_streak: int
    incorrect_streak: int
    score_points: int
    score_breakdown: Dict[str, int]
    repetitions: int
    lapses: int
    mcq_reps: int = 0
