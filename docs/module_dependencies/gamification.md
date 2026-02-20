# 📦 Module: `gamification`

This document outlines the dependencies and relationships of the `gamification` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- `auth`
- `scoring`
- `vocabulary`

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Function: `award_points`
- Function: `delete_items_gamification_data`
- Function: `delete_user_gamification_data`
- Function: `get_leaderboard`
- Function: `get_streak`
- Function: `get_user_badges`
- Function: `get_user_progress`
- Function: `get_user_score`
- Function: `record_daily_login`
- Function: `sync_all_users_scores`

## 📡 Signals (Defines/Emits)

**Emitted Events:**
- `score_awarded.send(...)` in `scoring_service.py`

## 🎧 Event Listeners
- None.

## 💾 Database Models
- `Badge`
- `ScoreLog`
- `Streak`
- `UserBadge`
