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
- **audio** - TTS generation via `AudioInterface.generate_audio()`
- **fsrs** - Spaced repetition calculations via `FSRSEngine`
- **learning** - Settings service
- **collab** - Collaborative flashcard rooms (extracted)
- **content_management** - Container metadata

## Key Design Decisions

1. **CardPresenter Pattern**: All card data assembly goes through `CardPresenter.build_card()` which resolves media URLs without implementing generation logic.

2. **External Audio Interface**: Audio regeneration endpoint (`/regenerate-audio-from-content`) delegates TTS to `audio.interface.AudioInterface.generate_audio()`.

3. **Services in services/**: All DB-accessing code lives in `services/`, NOT in `engine/`. This follows Hexagonal Architecture principles.

4. **Collab Extraction**: All multiplayer/collaborative models have been moved to `modules/collab/` for better separation of concerns.

## Events (Signals)
- Listens: None
- Emits: `card_reviewed` (via `core.signals`)

## Configuration
| Key | Default | Description |
|-----|---------|-------------|
| `flashcard_button_count` | 4 | Number of rating buttons (3 or 4) |
| `flashcard_autoplay_audio` | false | Auto-play audio on card flip |
| `flashcard_show_image` | true | Display images on cards |

