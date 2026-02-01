from typing import List, Optional
from .schemas import VocabItemDTO, VocabSetDTO
from mindstack_app.models import LearningContainer, LearningItem

def get_set_details(set_id: int) -> Optional[VocabSetDTO]:
    """Public API to get vocabulary set details."""
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

def get_items(set_id: int) -> List[VocabItemDTO]:
    """Public API to get items in a set."""
    items = LearningItem.query.filter_by(container_id=set_id).all()
    return [
        VocabItemDTO(
            id=item.item_id,
            front=item.content.get('front', ''),
            back=item.content.get('back', ''),
            audio_url=item.content.get('audio_url'),
            image_url=item.content.get('image_url'),
            ai_explanation=item.ai_explanation
        )
        for item in items
    ]
