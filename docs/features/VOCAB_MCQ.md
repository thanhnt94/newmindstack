# Vocabulary MCQ (Multiple Choice Quiz) - Documentation

Vocab MCQ is a sub-module of the consolidated `vocabulary` module that provides a gamified multiple-choice learning experience for vocabulary items.

## 🏗️ Architecture

The MCQ mode is built using a clean separation of concerns:
- **Engine**: Pure logic for question generation and grading.
- **Services**: Database orchestration and session management.
- **Interfaces**: Public APIs for internal and cross-module calls.
- **Routes**: API and View endpoints.
- **Logics**: Core algorithms for distractor selection and content parsing.

### 📁 File Structure
```text
mindstack_app/modules/vocabulary/mcq/
├── engine/
│   └── mcq_engine.py      # Core logic for question/choice generation
├── logics/
│   └── algorithms.py      # Distractor selection & shuffling
├── services/
│   ├── mcq_service.py     # Data access and question orchestration
│   └── mcq_session_manager.py # Session state & persistence
├── routes/
│   ├── views.py           # Blueprint routes (Views & APIs)
│   └── __init__.py
├── interface.py           # Public API for the sub-module
└── __init__.py            # Blueprint definition
```

---

## 🚀 Core Features

### 1. Generation Modes
- **Front → Back**: Cards are shown with the 'Front' text as the question and 'Back' text as choices.
- **Back → Front**: Cards are shown with 'Back' as the question and 'Front' as choices.
- **Mixed**: Randomly alternates between Front-Back and Back-Front.
- **Custom Pairs**: Allows users to select specific content fields (e.g., `Synonym` → `Word`) for targeted practice.

### 2. Intelligent Distractors
The system automatically scans the entire container to find suitable distractors:
- Excludes the correct answer.
- Removes duplicate distractor texts.
- Shuffles distractors with the correct answer.
- Supports random choice counts (3, 4, or 6 options).

### 3. FSRS Integration
The MCQ mode is designed for **Review/Retention**:
- Only items that have been **learned/reviewed** at least once (state != 0 in FSRS) are eligible.
- Successful answers update the FSRS memory state with high quality (5), while failures mark it as incorrect (0).

### 4. Session Persistence
Powered by `MCQSessionManager`, the MCQ mode supports:
- **State Saving**: The current question index and item order are saved to the database.
- **Safe Resumption**: Users can leave and return to the same session without losing progress.

---

## 🛠️ Logic Details

### Distractor Selection Algorithm
The system uses `random.sample` to pick unique distractors from the pool of items in the same container. If the pool is smaller than the requested number of choices, it gracefully handles the reduction.

```python
def select_choices(correct_answer, distractor_pool, num_choices=4):
    # Filters out duplicates and the correct answer
    # Picks N-1 distractors
    # Shuffles correctly
```

### Grade & Score
- **Correct**: Quality = 5, Score Change = +10 XP.
- **Incorrect**: Quality = 0, Score Change = 0 XP.

---

## 🌐 API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/mcq/setup/<id>` | GET | Configuration page for the session. |
| `/mcq/session/<id>` | GET | The main learning interface. |
| `/mcq/api/items/<id>` | GET | Starts/Restores a session and returns item data. |
| `/mcq/api/check` | POST | Submits an answer and updates SRS state. |
| `/mcq/api/next/<id>` | POST | Advances the session pointer. |
| `/mcq/api/end_session` | POST | Finalizes the session and marks it complete. |
