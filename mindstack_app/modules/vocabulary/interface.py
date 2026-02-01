# File: mindstack_app/modules/vocabulary/interface.py
from typing import List, Optional, Dict, Any
from .schemas import VocabItemDTO, VocabSetDTO
from .services.vocabulary_service import VocabularyService
from mindstack_app.models import AppSettings

class VocabularyInterface:
    @staticmethod
    def get_set_details(set_id: int) -> Optional[VocabSetDTO]:
        """Public API to get vocabulary set details."""
        from mindstack_app.models import LearningContainer, LearningItem
        container = LearningContainer.query.get(set_id)
        if not container or container.container_type != 'FLASHCARD_SET':
            return None
            
        count = LearningItem.query.filter_by(container_id=set_id).count()
        return VocabSetDTO(
            id=container.container_id,
            title=container.title,
            description=container.description,
            item_count=count,
            creator_name=container.creator.username if container.creator else "Unknown"
        )

    @staticmethod
    def get_config(key: str, default: Any = None) -> Any:
        """Get module configuration with proper fallback."""
        return AppSettings.get(key, default)

    @staticmethod
    def get_vocabulary_sets(user_id: int, **kwargs):
        return VocabularyService.get_vocabulary_sets(user_id, **kwargs)

    @staticmethod
    def get_set_detail(user_id: int, set_id: int, **kwargs):
        return VocabularyService.get_set_detail(user_id, set_id, **kwargs)

    @staticmethod
    def get_item_stats(user_id: int, item_id: int):
        """Public API to get detailed item statistics."""
        return VocabularyService.get_item_stats(user_id, item_id)
