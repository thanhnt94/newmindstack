class FSRSError(Exception):
    """Base exception for FSRS module."""
    pass

class CardNotDueError(FSRSError):
    """Raised when attempting to review a card that is not yet due."""
    pass

class InvalidRatingError(FSRSError):
    """Raised when the provided rating is not valid (must be 1-4)."""
    pass

class EngineCalculationError(FSRSError):
    """Raised when FSRS engine fails to calculate next states."""
    pass
