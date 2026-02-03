# File: mindstack_app/modules/vocab_flashcard/services/__init__.py
"""
Vocab Flashcard Services
========================
Orchestration layer for flashcard functionality.
Delegates to external modules for audio (audio), images (media), and sessions (session).
"""

from .flashcard_config_service import FlashcardConfigService
from .card_presenter import CardPresenter, get_audio_url_for_item, get_image_url_for_item

# Legacy imports - redirect to proper modules
# from mindstack_app.modules.audio.interface import AudioInterface
# from mindstack_app.modules.media.interface import MediaInterface
# from mindstack_app.modules.session.interface import SessionInterface

__all__ = [
    'FlashcardConfigService',
    'CardPresenter',
    'get_audio_url_for_item',
    'get_image_url_for_item',
]
