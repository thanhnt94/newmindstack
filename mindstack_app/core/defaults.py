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
    'FSRS_ENABLE_FUZZ': False,
    'FSRS_GLOBAL_WEIGHTS': [0.40255, 1.18385, 3.173, 15.691, 7.1509, 0.5477, 1.4633, 0.0035, 1.5457, 0.1192, 1.0192, 1.9395, 0.11, 0.296, 2.2698, 0.2315, 2.9898, 0.51655, 0.6621],
    
    # --- Audio Service Defaults ---
    'AUDIO_DEFAULT_ENGINE': 'edge',
    'AUDIO_DEFAULT_VOICE_EDGE': 'vi-VN-HoaiMyNeural', # Default favorable for native users
    'AUDIO_DEFAULT_VOICE_GTTS': 'vi',
    
    # --- Advanced Audio: Global Voice Mappings (Format: 'key': 'engine:voice_id') ---
    'AUDIO_VOICE_MAPPING_GLOBAL': {
        # Preferred Defaults
        'vi': 'edge:vi-VN-HoaiMyNeural',
        'en': 'gtts:en',
        'ja': 'edge:ja-JP-NanamiNeural',
        
        # Gender Specifics (Edge)
        'vi-f': 'edge:vi-VN-HoaiMyNeural',
        'vi-m': 'edge:vi-VN-NamMinhNeural',
        'en-f': 'edge:en-US-AriaNeural',
        'en-m': 'edge:en-US-ChristopherNeural',
        'ja-f': 'edge:ja-JP-NanamiNeural',
        'ja-m': 'edge:ja-JP-KeitaNeural',
    }
}
