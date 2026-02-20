# 📦 Module: `learning`

This document outlines the dependencies and relationships of the `learning` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- `AI`
- `fsrs`
- `gamification`
- `learning_history`
- `session`
- `stats`

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Class: `LearningInterface` (Methods: get_todays_activity_counts, get_score_breakdown, get_weekly_active_days_count, get_leaderboard, get_user_learning_summary, get_daily_summary, get_recent_activity, get_recent_sessions, get_recent_sessions, get_extended_dashboard_stats, evaluate_text_submission, evaluate_mcq_submission, get_course_progress, mark_course_completed, get_learning_item_by_id, get_container_by_id, update_learning_progress, get_container_settings, update_container_settings, resolve_flashcard_session_config, calculate_answer_points, quality_to_score)
- Function: `calculate_answer_points`
- Function: `evaluate_mcq_submission`
- Function: `evaluate_text_submission`
- Function: `get_container_by_id`
- Function: `get_container_settings`
- Function: `get_course_progress`
- Function: `get_daily_summary`
- Function: `get_extended_dashboard_stats`
- Function: `get_leaderboard`
- Function: `get_learning_item_by_id`
- Function: `get_recent_activity`
- Function: `get_recent_sessions`
- Function: `get_recent_sessions`
- Function: `get_score_breakdown`
- Function: `get_todays_activity_counts`
- Function: `get_user_learning_summary`
- Function: `get_weekly_active_days_count`
- Function: `mark_course_completed`
- Function: `quality_to_score`
- Function: `resolve_flashcard_session_config`
- Function: `update_container_settings`
- Function: `update_learning_progress`

## 📡 Signals (Defines/Emits)
- None.

## 🎧 Event Listeners
- None.

## 💾 Database Models
- `ContainerContributor`
- `LearningContainer`
- `LearningGroup`
- `LearningItem`
- `LearningProgress`
- `LearningSession`
- `UserContainerState`
- `UserItemMarker`
