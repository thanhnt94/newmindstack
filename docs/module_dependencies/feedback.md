# 📦 Module: `feedback`

This document outlines the dependencies and relationships of the `feedback` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- None (Independent Module)

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Function: `list_user_feedback`
- Function: `submit_feedback`

## 📡 Signals (Defines/Emits)
- None.

## 🎧 Event Listeners
- None.

## 💾 Database Models
- `FeedbackAttachment`
- `Feedback`
