# File: mindstack_app/modules/collab/config.py
"""Default configuration for Collab module."""


class DefaultConfig:
    """Default configuration values for collaborative learning."""
    
    # Flashcard Collab Scoring
    FLASHCARD_COLLAB_CORRECT = 10
    FLASHCARD_COLLAB_VAGUE = 5
    FLASHCARD_COLLAB_INCORRECT = 0
    
    # Quiz Battle Scoring  
    QUIZ_BATTLE_CORRECT = 10
    QUIZ_BATTLE_INCORRECT = 0
    QUIZ_BATTLE_SPEED_BONUS_MAX = 5
    
    # Room Settings
    MAX_ROOM_PARTICIPANTS = 10
    ROOM_CODE_LENGTH = 6
    ROOM_IDLE_TIMEOUT_MINUTES = 30
