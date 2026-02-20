# 📦 Module: `fsrs`

This document outlines the dependencies and relationships of the `fsrs` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- `learning_history`

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Class: `FSRSInterface` (Methods: process_review, process_interaction, get_retrievability, predict_next_intervals, train_user_parameters, get_config, get_due_counts, get_item_state, get_memory_state, batch_get_memory_states, get_memory_states, get_due_items, update_item_state, get_preview_intervals, get_global_stats, get_container_stats, get_learned_item_ids_for_container, get_learned_item_ids, get_learned_item_ids_for_container, get_learned_item_ids, save_item_note, toggle_item_marker, get_memory_stats_by_type, get_course_memory_stats, get_started_container_count, get_activity_counts_by_type, get_items_for_practice, get_hard_items, get_review_aggregated_stats, get_daily_new_items_count, get_daily_reviewed_items_count, apply_memory_filter, get_hard_count, get_leaderboard_mastery, apply_ordering, get_learned_count, get_initial_state, get_detailed_container_stats, get_course_container_stats, get_daily_reviews_map, get_daily_reviews_map, get_daily_new_items_map, get_all_memory_states_query, get_parameters, save_lesson_progress, get_batch_memory_states, get_upcoming_reviews, get_memory_state_distribution, calculate_retrievability_for_record, apply_due_exclusion_filter)
- Function: `apply_due_exclusion_filter`
- Function: `apply_memory_filter`
- Function: `apply_ordering`
- Function: `batch_get_memory_states`
- Function: `calculate_retrievability_for_record`
- Function: `get_activity_counts_by_type`
- Function: `get_all_memory_states_query`
- Function: `get_batch_memory_states`
- Function: `get_config`
- Function: `get_container_stats`
- Function: `get_course_container_stats`
- Function: `get_course_memory_stats`
- Function: `get_daily_new_items_count`
- Function: `get_daily_new_items_map`
- Function: `get_daily_reviewed_items_count`
- Function: `get_daily_reviews_map`
- Function: `get_daily_reviews_map`
- Function: `get_detailed_container_stats`
- Function: `get_due_counts`
- Function: `get_due_counts`
- Function: `get_due_items`
- Function: `get_global_stats`
- Function: `get_hard_count`
- Function: `get_hard_items`
- Function: `get_initial_state`
- Function: `get_item_state`
- Function: `get_items_for_practice`
- Function: `get_leaderboard_mastery`
- Function: `get_learned_count`
- Function: `get_learned_item_ids_for_container`
- Function: `get_learned_item_ids_for_container`
- Function: `get_learned_item_ids`
- Function: `get_learned_item_ids`
- Function: `get_memory_state_distribution`
- Function: `get_memory_state`
- Function: `get_memory_states`
- Function: `get_memory_stats_by_type`
- Function: `get_parameters`
- Function: `get_preview_intervals`
- Function: `get_retrievability`
- Function: `get_review_aggregated_stats`
- Function: `get_started_container_count`
- Function: `get_upcoming_reviews`
- Function: `predict_next_intervals`
- Function: `process_interaction`
- Function: `process_review`
- Function: `save_item_note`
- Function: `save_lesson_progress`
- Function: `toggle_item_marker`
- Function: `train_user_parameters`
- Function: `update_item_state`

## 📡 Signals (Defines/Emits)
**Defined Signals:**
- `_signals`
- `card_reviewed`
- `parameters_updated`

**Emitted Events:**
- `card_reviewed.send(...)` in `scheduler_service.py`

## 🎧 Event Listeners
- None.

## 💾 Database Models
- `ItemMemoryState`
