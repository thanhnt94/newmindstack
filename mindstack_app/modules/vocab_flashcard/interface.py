"""Public interface for the vocab_flashcard module."""

from .engine.algorithms import (
    get_accessible_flashcard_set_ids,
    get_flashcard_mode_counts
)


class FlashcardInterface:
    @staticmethod
    def has_active_session(user_id: int) -> bool:
        """Check if the user has an active flashcard session."""
        from mindstack_app.modules.session.interface import SessionInterface
        session = SessionInterface.get_active_session(user_id, learning_mode='flashcard')
        return session is not None

    @staticmethod
    def get_flashcard_mode_counts(user_id: int, set_id: any, context: str = 'vocab') -> dict:
        """Get counts for different flashcard modes."""
        from .engine.algorithms import get_flashcard_mode_counts
        return get_flashcard_mode_counts(user_id, set_id, context=context)

    @staticmethod
    def get_audio_service_instance():
        """Get the AudioService instance (for admin tasks)."""
        from .services.audio_service import AudioService
        return AudioService()

    @staticmethod
    def get_image_service_instance():
        """Get the ImageService instance (for admin tasks)."""
        from .services.image_service import ImageService
        return ImageService()

    @staticmethod
    def get_all_configs():
        """Get all flashcard configuration options."""
        from .services.flashcard_config_service import FlashcardConfigService
        return FlashcardConfigService.get_all()

    @staticmethod
    def get_config_service():
        """Get the FlashcardConfigService class."""
        from .services.flashcard_config_service import FlashcardConfigService
        return FlashcardConfigService

    @staticmethod
    def get_session_completed_signal():
        """Get the flashcard_session_completed signal."""
        from .signals import flashcard_session_completed
        return flashcard_session_completed

    @staticmethod
    def register_flashcard_modes(module_name: str, modes: list):
        """Register flashcard modes."""
        from .engine.vocab_flashcard_mode import register_flashcard_modes
        register_flashcard_modes(module_name, modes)
    
    @staticmethod
    def get_flashcard_mode_class():
        """Get the FlashcardMode class for defining modes."""
        from .engine.vocab_flashcard_mode import FlashcardMode
        return FlashcardMode
