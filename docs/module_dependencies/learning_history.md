# 📦 Module: `learning_history`

This document outlines the dependencies and relationships of the `learning_history` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- None (Independent Module)

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Class: `LearningHistoryInterface` (Methods: get_log, count_mode_reps, record_log, get_logs_by_user, get_study_stats, delete_user_history, get_item_history, get_model_class, get_recent_containers, get_daily_activity_series, get_item_history, get_study_log_timeline, get_user_history_for_optimization, delete_items_history, get_session_logs, get_first_review_dates)
- Function: `count_mode_reps`
- Function: `delete_items_history`
- Function: `delete_user_history`
- Function: `get_daily_activity_series`
- Function: `get_first_review_dates`
- Function: `get_item_history`
- Function: `get_item_history`
- Function: `get_log`
- Function: `get_logs_by_user`
- Function: `get_model_class`
- Function: `get_recent_containers`
- Function: `get_session_logs`
- Function: `get_study_log_timeline`
- Function: `get_study_stats`
- Function: `get_user_history_for_optimization`
- Function: `record_log`

## 📡 Signals (Defines/Emits)
- None.

## 🎧 Event Listeners
- None.

## 💾 Database Models
- `StudyLog`
