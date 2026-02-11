# File: mindstack_app/modules/vocab_flashcard/services/__init__.py
"""
Vocab Flashcard Services
========================
Service layer for flashcard functionality (only layer that can access DB).

Contains:
- FlashcardService: High-level orchestration facade
- FlashcardQueryBuilder: Query construction
- FlashcardPermissionService: Access control
- FlashcardItemService: Item retrieval
- FlashcardConfigService: Configuration management
- CardPresenter: Card presentation logic
"""

from .query_builder import FlashcardQueryBuilder
from .permission_service import FlashcardPermissionService, get_accessible_flashcard_set_ids
from .item_service import FlashcardItemService
from .flashcard_config_service import FlashcardConfigService
from .card_presenter import CardPresenter
from .flashcard_service import FlashcardService

__all__ = [
    # Orchestration
    'FlashcardService',
    # Query/DB services
    'FlashcardQueryBuilder',
    'FlashcardPermissionService',
    'FlashcardItemService',
    'get_accessible_flashcard_set_ids',
    # Config/Presentation
    'FlashcardConfigService',
    'CardPresenter',
]

