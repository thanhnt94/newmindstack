# FSRS Module (v2.0 Modular Monolith)

## Overview
The **FSRS (Free Spaced Repetition Scheduler)** module is the core scheduling engine of MindStack. It implements the FSRS-5 algorithm to calculate optimal review intervals for learning items, adapting to each user's memory strength.

This module is designed as a strict **Modular Monolith** component, isolating pure logic (`engine`) from database operations (`services`).

## Responsibility
- **Scheduling:** Calculating the next due date and memory state (stability, difficulty) for flashcards.
- **Optimization:** Training personalized parameters based on user's review history.
- **State Management:** Tracking `ItemMemoryState` for every user-item pair.

## Dependencies
- **Auth Module:** Requires `current_user` context (user_id).
- **Learning History Module:** Uses `StudyLog` for optimization training (via `OptimizerService`).
- **Core:** Uses `db` (SQLAlchemy) and `AppSettings`.

## Configuration
The module uses the following configuration keys (managed via `AppSettings`):

| Key | Default | Description |
| :--- | :--- | :--- |
| `FSRS_DESIRED_RETENTION` | `0.9` | Target retention rate (90%). |
| `FSRS_MAX_INTERVAL` | `365` | Maximum interval in days. |
| `FSRS_ENABLE_FUZZING` | `True` | Add random fuzz to intervals to prevent bunching. |
| `FSRS_ROLLING_WINDOW` | `30` | Days to look back for some metrics. |

## Public Interface (`interface.py`)
Other modules **MUST** interact with FSRS via `mindstack_app.modules.fsrs.interface.FSRSInterface`.

### Methods
- `process_review(user_id, item_id, quality, ...)`: Process a review and update state.
- `get_preview_intervals(user_id, item_id)`: Get next intervals for all ratings (1-4).
- `get_retrievability(state)`: Calculate current memory probability.
- `train_user_parameters(user_id)`: Trigger optimization.
- `get_due_items(user_id, limit)`: Get items due for review.

## API Endpoints
Base URL: `/api/fsrs`

### 1. Process Review
**POST** `/review`
- **Input:** `{ "item_id": 123, "rating": 3, "duration_ms": 5000 }`
- **Output:** `{ "data": { "next_review": "...", "interval_minutes": 1440, ... } }`

### 2. Preview Intervals
**GET** `/preview/<item_id>`
- **Output:** `{ "previews": { "1": { "interval": "10m", ... }, "3": { "interval": "4d", ... } } }`

### 3. Train Parameters
**POST** `/train`
- **Output:** `{ "message": "Optimization successful", "parameters": [...] }`

## Signals (`signals.py`)
- `card_reviewed`: Emitted after a review is successfully processed and saved.
  - Args: `user_id`, `item_id`, `rating`, `new_state`
- `parameters_updated`: Emitted after optimization finishes.
  - Args: `user_id`

## Architecture Notes
- **Engine Layer (`engine/core.py`):** Pure Python logic. No DB access.
- **Service Layer (`services/scheduler_service.py`):** Orchestrator. Handles DB and Signals.
- **Models (`models.py`):** `ItemMemoryState` is the source of truth.
