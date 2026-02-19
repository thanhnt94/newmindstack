# modules/scoring/config.py

class ScoringDefaultConfig:
    """
    Default configuration for Scoring Module.
    Acts as a fallback if Database settings are missing.
    """
    
    # --- Flashcard & SRS ---
    SCORE_FSRS_AGAIN = 1
    SCORE_FSRS_HARD = 5
    SCORE_FSRS_GOOD = 10
    SCORE_FSRS_EASY = 15
    
    # --- Quiz ---
    QUIZ_CORRECT_BONUS = 20
    QUIZ_FIRST_TIME_BONUS = 5
    
    # --- Vocabulary Games ---
    VOCAB_MCQ_CORRECT_BONUS = 10
    VOCAB_TYPING_CORRECT_BONUS = 15
    VOCAB_MATCHING_CORRECT_BONUS = 10
    VOCAB_LISTENING_CORRECT_BONUS = 12
    VOCAB_SPEED_CORRECT_BONUS = 20
    
    # --- Engagement ---
    DAILY_LOGIN_SCORE = 10
    DAILY_GOAL_SCORE = 50
    SCORING_STREAK_BONUS_VALUE = 5
    SCORING_STREAK_BONUS_MODULO = 10
    
    # --- Multipliers & Bonuses ---
    SCORING_DIFFICULTY_WEIGHT = 20  # Lower is stronger (formula: 1 + difficulty / weight)
    SCORING_STREAK_THRESHOLD = 5   # Min streak for bonus
    SCORING_STREAK_CAP = 100       # Max flat points from streak
    
    # --- Course ---
    COURSE_LESSON_COMPLETION_SCORE = 15
    COURSE_COMPLETION_SCORE = 50
