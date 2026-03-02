# modules/scoring/config.py

class ScoringDefaultConfig:
    """
    Default configuration for Scoring Module.
    Acts as a fallback if Database settings are missing.
    """
    
    # --- Flashcard & SRS ---
    SCORE_FSRS_AGAIN = 1
    SCORE_FSRS_HARD = 2
    SCORE_FSRS_GOOD = 4
    SCORE_FSRS_EASY = 7
    
    # --- Quiz ---
    QUIZ_CORRECT_BONUS = 5
    QUIZ_FIRST_TIME_BONUS = 3
    
    # --- Vocabulary Games ---
    VOCAB_MCQ_CORRECT_BONUS = 3
    VOCAB_TYPING_CORRECT_BONUS = 5
    VOCAB_MATCHING_CORRECT_BONUS = 1
    VOCAB_LISTENING_CORRECT_BONUS = 4
    VOCAB_SPEED_CORRECT_BONUS = 2
    
    # --- Engagement ---
    DAILY_LOGIN_SCORE = 5
    DAILY_GOAL_SCORE = 20
    SCORING_STREAK_BONUS_VALUE = 2
    SCORING_STREAK_BONUS_MODULO = 20
    
    # --- Multipliers & Bonuses ---
    SCORING_DIFFICULTY_WEIGHT = 20  # Formula: 1 + difficulty / weight
    SCORING_STREAK_THRESHOLD = 10  # Higher threshold
    SCORING_STREAK_CAP = 10         # Lower cap
    
    # --- Course ---
    COURSE_LESSON_COMPLETION_SCORE = 15
    COURSE_COMPLETION_SCORE = 50
