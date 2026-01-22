"""
Centralized Default Configuration for MindStack.

This file serves as the "Source of Truth" for all default application settings.
These values are used as fallbacks if a setting is missing from the database (AppSettings).
"""

DEFAULT_APP_CONFIGS = {
    # --- System & AI ---
    'AI_PROVIDER': 'gemini',
    'GEMINI_MODEL': 'gemini-2.0-flash-lite-001',
    'HUGGINGFACE_MODEL': 'google/gemma-7b-it',
    'MAINTENANCE_MODE': False,
    'MAINTENANCE_END_TIME': '',
    
    # --- Gamification: FSRS (Fixed Point Model) ---
    'SCORE_FSRS_AGAIN': 1,
    'SCORE_FSRS_HARD': 5,
    'SCORE_FSRS_GOOD': 10,
    'SCORE_FSRS_EASY': 15,
    
    # --- Gamification: Other Modes ---
    'QUIZ_FIRST_TIME_BONUS': 5,
    'QUIZ_CORRECT_BONUS': 20,
    'COURSE_LESSON_COMPLETION_SCORE': 15,
    'COURSE_COMPLETION_SCORE': 50,
    'VOCAB_TYPING_CORRECT_BONUS': 15,
    'VOCAB_MATCHING_CORRECT_BONUS': 10,
    'VOCAB_LISTENING_CORRECT_BONUS': 12,
    'VOCAB_SPEED_CORRECT_BONUS': 20,
    'VOCAB_MCQ_CORRECT_BONUS': 10,
    'DAILY_LOGIN_SCORE': 10,
    'DAILY_GOAL_SCORE': 50,
    
    # --- Gamification: Bonuses & Streaks ---
    'SCORING_STREAK_BONUS_VALUE': 5,         # Bonus pts awarded at thresholds
    'SCORING_STREAK_BONUS_MODULO': 10,        # Award every N streaks (e.g., 10, 20, 30...)
    'SCORING_STREAK_LVL_1Y': 500,
    'SCORING_STREAK_LVL_100D': 200,
    'SCORING_STREAK_LVL_30D': 100,
    'SCORING_STREAK_LVL_14D': 50,
    'SCORING_STREAK_LVL_7D': 25,
    'SCORING_STREAK_LVL_3D': 10,
    'SCORING_STREAK_LVL_2D': 5,
    'SCORING_PERFECT_BONUS': 5,               # Bonus for quality 4/5
    
    # --- FSRS-5 Parameters ---
    'FSRS_DESIRED_RETENTION': 0.9,
    'FSRS_MAX_INTERVAL': 365,
    'FSRS_GLOBAL_WEIGHTS': [0.4, 0.6, 2.4, 5.8, 4.93, 0.94, 0.86, 0.01, 1.49, 0.14, 0.94, 2.18, 0.05, 0.34, 1.26, 0.29, 2.61],
}
