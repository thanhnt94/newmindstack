# 📦 Module: `session`

This document outlines the dependencies and relationships of the `session` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- `learning_history`

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Class: `SessionInterface` (Methods: create_session, get_active_session, get_active_sessions, get_any_active_vocabulary_session, update_progress, complete_session, cancel_active_sessions, get_session_by_id, reset_session_progress, get_session_history, set_current_item, start_driven_session, get_driver_state)
- Function: `cancel_active_sessions`
- Function: `complete_session`
- Function: `create_session`
- Function: `get_active_session`
- Function: `get_active_sessions`
- Function: `get_any_active_vocabulary_session`
- Function: `get_driver_state`
- Function: `get_session_by_id`
- Function: `get_session_history`
- Function: `reset_session_progress`
- Function: `set_current_item`
- Function: `start_driven_session`
- Function: `update_progress`

## 📡 Signals (Defines/Emits)
- None.

## 🎧 Event Listeners
- None.

## 💾 Database Models
- No dedicated models found.
