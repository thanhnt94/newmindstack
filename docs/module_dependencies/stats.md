# 📦 Module: `stats`

This document outlines the dependencies and relationships of the `stats` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- `fsrs`
- `gamification`
- `learning`
- `learning_history`

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Class: `StatsInterface` (Methods: record_activity, get_user_summary, get_leaderboard, get_dashboard_activity, get_vocab_item_stats, get_vocab_set_overview_stats, get_global_stats, get_full_stats, get_chart_data)
- Function: `get_chart_data`
- Function: `get_dashboard_activity`
- Function: `get_dashboard_activity`
- Function: `get_full_stats`
- Function: `get_global_stats`
- Function: `get_leaderboard`
- Function: `get_leaderboard`
- Function: `get_user_summary`
- Function: `get_user_summary`
- Function: `get_vocab_item_stats`
- Function: `get_vocab_set_overview_stats`
- Function: `record_activity`
- Function: `record_activity`

## 📡 Signals (Defines/Emits)
- None.

## 🎧 Event Listeners
- None.

## 💾 Database Models
- `Achievement`
- `DailyStat`
- `UserMetric`
