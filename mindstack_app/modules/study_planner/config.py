# modules/study_planner/config.py

class StudyPlannerDefaultConfig:
    """Default configuration for the Study Planner module."""
    # Minimum number of days for a plan
    PLANNER_MIN_DAYS = 3
    # Maximum number of days for a plan
    PLANNER_MAX_DAYS = 365
    # Minimum daily target (won't recommend less than this)
    PLANNER_MIN_DAILY_TARGET = 1
