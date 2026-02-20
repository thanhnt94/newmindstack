# 📦 Module: `admin`

This document outlines the dependencies and relationships of the `admin` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- `AI`
- `content_management`
- `fsrs`
- `gamification`
- `learning_history`
- `quiz`
- `vocabulary`

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Class: `AdminInterface` (Methods: get_setting, set_setting)
- Function: `get_setting`
- Function: `set_setting`

## 📡 Signals (Defines/Emits)
- None.

## 🎧 Event Listeners
- None.

## 💾 Database Models
- No dedicated models found.
