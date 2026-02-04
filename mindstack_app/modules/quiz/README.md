# Quiz Module

## Purpose
Provides quiz-based learning functionality with multiple choice questions.
This module handles individual quiz sessions. Multiplayer battles are in `collab` module.

## Architecture

```
quiz/
├── routes/
│   ├── api.py              # JSON endpoints
│   ├── individual_api.py   # Individual quiz session API
│   └── views.py            # HTML rendering
├── services/
│   └── quiz_config_service.py  # Configuration management
├── models.py               # QuizSet, QuizMCQ only
└── __init__.py             # Blueprint registration
```

## Models

| Model | Purpose |
|-------|---------|
| `QuizSet` | Container for quiz questions (extends LearningContainer) |
| `QuizMCQ` | Multiple choice question (extends LearningItem) |

> **Note**: Battle models (`QuizBattleRoom`, etc.) have been extracted to `modules/collab/`.

## Dependencies
- **learning** - Base container/item models
- **fsrs** - Spaced repetition for quiz items
- **collab** - Multiplayer quiz battles (extracted)

## Events (Signals)
- Listens: None
- Emits: None
