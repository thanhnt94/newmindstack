# Learning Core - Logics Package (FSRS-5)
# Pure business logic, no database access

from .scoring_engine import ScoringEngine, ScoreResult, LearningMode
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsInterface
FSRSEngine = FsrsInterface.FSRSEngine if hasattr(FsrsInterface, 'FSRSEngine') else None # Optional if needed
CardState = FsrsInterface.CardStateDTO
Rating = FsrsInterface.Rating

__all__ = [
    'ScoringEngine', 'ScoreResult', 'LearningMode',
    'FSRSEngine', 'CardState', 'Rating'
]

