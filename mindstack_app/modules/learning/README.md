# Learning Module

This module handles **Academic Evaluation** (Grading) and **Progress Tracking** (Course Completion).

It answers two core questions:
1. "Did the user answer this correctly?" (Evaluation)
2. "How much of the course has the user finished?" (Progress)

> [!WARNING]
> This module NO LONGER handles Experience Points (XP), Badges, or Streaks. Those are handled by the `gamification` module.

## Architecture

| Component | Responsibility |
| :--- | :--- |
| `logics/marker.py` | **Pure Logic**. Compares text submissions against solutions. Handles fuzzy matching and normalization. |
| `services/progress_service.py` | **Service**. Calculates course completion stats (e.g. 50% completed). |
| `interface.py` | **Public API**. Main entry point for other modules (`quiz`, `typing`, etc). |
| `models.py` | **Database Models**. Stores `LearningContainer`, `LearningItem`, etc. |

## Deprecated Components

> These files are stuck in the past. Do not use them for new code.

- `services/score_service.py`: Use `gamification.services` instead.
- `logics/scoring_engine.py`: Logic moved to `gamification`.

## Usage

### Evaluating an Answer

```python
from mindstack_app.modules.learning.interface import LearningInterface

# Text Answer
result = LearningInterface.evaluate_text_submission(
    submission="hello world", 
    solution="Hello, World!", 
    tolerance=0.1
)
print(result['is_correct']) # True

# MCQ Answer
result = LearningInterface.evaluate_mcq_submission("A", "A")
```

### Checking Progress

```python
from mindstack_app.modules.learning.interface import LearningInterface

stats = LearningInterface.get_course_progress(user_id=1, container_id=101)
print(f"Completed: {stats['completion_percentage']}%")
```
