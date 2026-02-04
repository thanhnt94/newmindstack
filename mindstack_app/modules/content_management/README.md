# Content Management Module

## Purpose
Acts as the central **Content Library** for the entire application.
Responsible for storing, retrieving, and organizing learning content (flashcards, quizzes, etc.).
Provides a standardized Interface for other modules to access content without direct database queries.

## Architecture

```
content_management/
├── interface.py            # Public API (get_items_content, etc.)
├── signals.py              # Event signals (created, updated, deleted)
├── services/
│   ├── kernel_service.py   # Low-level CRUD & Signal emission
│   └── management_service.py # Higher-level logic
├── routes/
│   ├── api.py              # REST API
│   └── views.py            # UI Views
└── models.py               # (Uses core models from mindstack_app.models)
```

## Public Interface

**Access content via `interface.py` ONLY:**

```python
from mindstack_app.modules.content_management.interface import ContentInterface

# Get standardized content for items
# Returns dict with absolute media URLs
items = ContentInterface.get_items_content([101, 102])

# Get container metadata
meta = ContentInterface.get_container_metadata(50)
```

## Signals

Other modules (FSRS, Stats) should listen to these signals to react to content changes:

| Signal | Arguments | Description |
|--------|-----------|-------------|
| `content_created` | `item_id`, `item_type`, `container_id` | New content added |
| `content_updated` | `item_id`, `item_type`, `changes` | Content modified |
| `content_deleted` | `item_id`, `item_type` | Content removed |

## Zero Coupling Rules

1. **No Logic Leak:** This module does NOT calculate progress, retention, or gamification points.
2. **Absolute URLs:** All media paths returned by `interface` are absolute strings.
3. **Standardized Dict:** `get_items_content` returns a consistent dictionary format regardless of item type.
