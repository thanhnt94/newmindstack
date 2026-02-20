# 📦 Module: `goals`

This document outlines the dependencies and relationships of the `goals` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- None (Independent Module)

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Function: `create_user_goal`
- Function: `get_goal_progress`
- Function: `get_user_goals`

## 📡 Signals (Defines/Emits)

**Emitted Events:**
- `goal_completed.send(...)` in `goal_orchestrator.py`

## 🎧 Event Listeners
- None.

## 💾 Database Models
- `GoalProgress`
- `Goal`
- `UserGoal`
