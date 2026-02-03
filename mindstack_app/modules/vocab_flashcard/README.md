# Vocab Flashcard Module

## Purpose
Provides flashcard-based vocabulary learning functionality.  
This module is a **Presentation Layer** that delegates business logic to external modules.

## Architecture

```
vocab_flashcard/
├── routes/
│   ├── api.py          # JSON endpoints for flashcard sessions
│   └── views.py        # HTML rendering for web UI
├── services/
│   ├── card_presenter.py       # [NEW] Assembles card data from multiple sources
│   ├── audio_service.py        # [LEGACY] Batch audio operations (migrate to audio module)
│   ├── image_service.py        # [LEGACY] Image search/download (migrate to content_management)
│   ├── session_service.py      # [LEGACY] Session DB operations
│   └── flashcard_config_service.py  # Configuration management
├── engine/
│   ├── session_manager.py      # In-memory session state management
│   ├── core.py                 # FlashcardEngine - answer processing
│   ├── algorithms.py           # Query building for different modes
│   └── config.py               # Default configuration values
├── schemas.py                  # DTOs and Marshmallow schemas
├── interface.py                # Public API for other modules
└── models.py                   # Database models
```

## Dependencies
- **audio** - TTS generation via `AudioInterface.generate_audio()`
- **fsrs** - Spaced repetition calculations via `FSRSEngine`
- **learning** - Settings service
- **content_management** - Container metadata

## Key Design Decisions

1. **CardPresenter Pattern**: All card data assembly goes through `CardPresenter.build_card()` which resolves media URLs without implementing generation logic.

2. **External Audio Interface**: Audio regeneration endpoint (`/regenerate-audio-from-content`) delegates TTS to `audio.interface.AudioInterface.generate_audio()`.

3. **Legacy Services**: `audio_service.py` and `image_service.py` are kept for batch operations but should be migrated to their respective modules in future refactors.

## Events (Signals)
- Listens: None
- Emits: None (uses direct service calls)

## Configuration
| Key | Default | Description |
|-----|---------|-------------|
| `flashcard_button_count` | 4 | Number of rating buttons (3 or 4) |
| `flashcard_autoplay_audio` | false | Auto-play audio on card flip |
| `flashcard_show_image` | true | Display images on cards |
