# 📦 Module: `ops`

This document outlines the dependencies and relationships of the `ops` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- `gamification`
- `learning_history`

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Class: `OpsInterface` (Methods: reset_user_progress_for_container, reset_entire_learning_progress)
- Function: `reset_entire_learning_progress`
- Function: `reset_user_progress_for_container`

## 📡 Signals (Defines/Emits)
- None.

## 🎧 Event Listeners
- None.

## 💾 Database Models
- `BackgroundTaskLog`
- `BackgroundTask`
