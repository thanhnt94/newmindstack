# Vocab Flashcard Module

## Purpose
Provides flashcard-based vocabulary learning functionality.  
This module is a **Presentation Layer** that delegates business logic to external modules.

## Architecture

```
vocab_flashcard/
├── routes/
│   ├── api.py              # JSON endpoints for flashcard sessions
│   └── views.py            # HTML rendering for web UI
├── services/               # DB Access Layer (only layer allowed to query DB)
│   ├── flashcard_service.py # High-level orchestration facade (NEW)
│   ├── query_builder.py    # SQLAlchemy query builder pattern
│   ├── permission_service.py # Access control & container permissions
│   ├── item_service.py     # Item retrieval by learning criteria
│   ├── card_presenter.py   # Assembles card data from multiple sources
│   └── flashcard_config_service.py  # Configuration management
├── engine/                 # Pure Business Logic (NO DB access)
│   ├── core.py             # FlashcardEngine - answer processing
│   ├── algorithms.py       # High-level algorithms for set selection
│   ├── config.py           # Default configuration values
│   └── vocab_flashcard_mode.py  # Mode definitions & registry
├── schemas.py              # DTOs and Marshmallow schemas
├── interface.py            # Public API for other modules (Gatekeeper)
├── signals.py              # Module-specific signals (NEW)
├── events.py               # Event listeners placeholder (NEW)
└── models.py               # Database models (FlashcardSet, Flashcard only)
```

## Layer Rules (per MODULE_STRUCTURE.md)

| Layer | Can Access DB? | Purpose |
|-------|---------------|---------|
| `routes/` | No | HTTP handling, delegates to services |
| `services/` | **Yes** | Only layer that queries database |
| `engine/` | **No** | Pure logic, no Flask/DB knowledge |

> **Note**: Collab models (`FlashcardCollabRoom`, etc.) have been extracted to `modules/collab/`.

## Dependencies
- **fsrs** - Spaced repetition calculations via `FSRSInterface`
- **session** - Session tracking via `SessionInterface`
- **audio** - TTS generation via `AudioInterface.generate_audio()`
- **learning** - Settings service
- **learning_history** - Interaction recording via `HistoryRecorder`
- **collab** - Collaborative flashcard rooms (extracted)
- **content_management** - Container metadata

## Key Design Decisions

1. **FlashcardService Pattern**: New orchestration facade (`services/flashcard_service.py`) coordinates the answer submission workflow:
   - Schedules via `FSRSInterface.process_review()`
   - Tracks via `SessionInterface.update_progress()`
   - Records via `HistoryRecorder.record_interaction()`
   - Signals via `card_reviewed` (for gamification)

2. **CardPresenter Pattern**: All card data assembly goes through `CardPresenter.build_card()` which resolves media URLs without implementing generation logic.

3. **External Audio Interface**: Audio regeneration endpoint (`/regenerate-audio-from-content`) delegates TTS to `audio.interface.AudioInterface.generate_audio()`.

4. **Services in services/**: All DB-accessing code lives in `services/`, NOT in `engine/`. This follows Hexagonal Architecture principles.

5. **Collab Extraction**: All multiplayer/collaborative models have been moved to `modules/collab/` for better separation of concerns.

## Signals

### Emitted by this module
| Signal | Description |
|--------|-------------|
| `flashcard_session_started` | Emitted when a session begins |
| `flashcard_session_completed` | Emitted when a session ends (not cancelled) |
| `flashcard_batch_loaded` | Emitted when a batch of cards is loaded |

### Used from core
| Signal | Description |
|--------|-------------|
| `card_reviewed` (from `core.signals`) | Emitted after each answer for gamification |

## API Endpoints

### Session Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sets` | List flashcard sets |
| GET | `/api/modes/<set_id>` | Get mode counts for a set |
| GET | `/get_flashcard_batch` | Get next batch of cards |
| POST | `/submit_flashcard_answer` | Submit answer and update progress |
| POST | `/end_session_flashcard` | End current session |

### Media & Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/regenerate-audio-from-content` | Regenerate audio for a card |
| POST | `/generate-image-from-content` | Find and attach image |
| POST | `/save_flashcard_settings` | Save user preferences |
| POST | `/api/preview_fsrs` | Get FSRS preview intervals |

## Configuration
| Key | Default | Description |
|-----|---------|-------------|
| `flashcard_button_count` | 4 | Number of rating buttons (3 or 4) |
| `flashcard_autoplay_audio` | false | Auto-play audio on card flip |
| `flashcard_show_image` | true | Display images on cards |
