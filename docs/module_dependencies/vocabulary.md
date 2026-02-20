# 📦 Module: `vocabulary`

This document outlines the dependencies and relationships of the `vocabulary` module based on Hexagonal Architecture.

## 🔗 Dependencies (Consumes)
- `AI`
- `audio`
- `content_management`
- `fsrs`
- `gamification`
- `learning`
- `learning_history`
- `media`
- `scoring`
- `session`
- `stats`

## 🚪 Public Interface (Exports)
*These are the endpoints exposed via `interface.py` for other modules to use.*
- Class: `VocabularyInterface` (Methods: get_set_detail, get_global_stats, get_full_stats, get_mode_counts)
- Function: `get_full_stats`
- Function: `get_global_stats`
- Function: `get_mode_counts`
- Function: `get_set_detail`

## 📡 Signals (Defines/Emits)

**Emitted Events:**
- `card_reviewed.send(...)` in `core.py`
- `card_reviewed.send(...)` in `driver.py`
- `card_reviewed.send(...)` in `flashcard_service.py`
- `card_reviewed.send(...)` in `views.py`

## 🎧 Event Listeners
- None.

## 💾 Database Models
- `FlashcardSet`
- `Flashcard`
