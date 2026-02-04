# Collab Module

## Purpose
Provides room-based collaborative learning functionality for multiplayer quiz battles and flashcard sessions.

## Architecture

```
collab/
├── routes/
│   └── views.py            # Dashboard and room views
├── models.py               # All collaboration models
├── config.py               # Default scoring and room settings
├── interface.py            # Public API (Gatekeeper)
└── __init__.py             # Blueprint registration
```

## Models

### Flashcard Collaboration
| Model | Purpose |
|-------|---------|
| `FlashcardCollabRoom` | Room metadata and state |
| `FlashcardCollabParticipant` | User participation tracking |
| `FlashcardCollabRound` | Current study round |
| `FlashcardCollabAnswer` | User answers per round |
| `FlashcardCollabMessage` | In-room chat messages |
| `FlashcardRoomProgress` | Per-item progress in room |

### Quiz Battle
| Model | Purpose |
|-------|---------|
| `QuizBattleRoom` | Battle room metadata |
| `QuizBattleParticipant` | Player tracking and scores |
| `QuizBattleRound` | Question rounds |
| `QuizBattleAnswer` | Player answers |
| `QuizBattleMessage` | Chat messages |

## Dependencies
- **learning** - `LearningContainer`, `LearningItem` for content
- **auth** - `User` for participants
- **chat** - Chat API integration

## Configuration (config.py)
| Key | Default | Description |
|-----|---------|-------------|
| `FLASHCARD_COLLAB_CORRECT` | 10 | Points for correct answer |
| `FLASHCARD_COLLAB_VAGUE` | 5 | Points for partial answer |
| `QUIZ_BATTLE_CORRECT` | 100 | Base points for correct quiz answer |
| `QUIZ_BATTLE_SPEED_BONUS` | 50 | Max speed bonus |
| `DEFAULT_ROOM_MAX_PLAYERS` | 10 | Default max players per room |

## Usage (via interface.py)

```python
from mindstack_app.modules.collab.interface import (
    FlashcardCollabRoom,
    QuizBattleRoom,
    get_collab_config,
)

# Create a flashcard collab room
room = FlashcardCollabRoom(
    room_code='ABC123',
    title='Study Session',
    host_user_id=user.user_id,
    container_id=flashcard_set.container_id,
    mode='mixed_srs'
)

# Access configuration
correct_points = get_collab_config('FLASHCARD_COLLAB_CORRECT')
```

## Events (Signals)
- Listens: None (yet)
- Emits: None (yet)

> **Note**: This module was extracted from `vocab_flashcard` and `quiz` modules to consolidate all collaborative learning models following Domain-Driven Design principles.
