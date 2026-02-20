# 📦 Module: `quiz`

This document outlines the dependencies and relationships of the `quiz` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- `AI`
- `audio`
- `content_management`
- `fsrs`
- `learning`
- `learning_history`
- `session`
- `vocabulary`

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Function: `get_all_quiz_configs`
- Function: `get_quiz_set_details`
- Function: `transcribe_quiz_audio`

## 📡 Signals (Defines/Emits)
- None.

## 🎧 Event Listeners
- None.

## 💾 Database Models
- `QuizMCQ`
- `QuizSet`
