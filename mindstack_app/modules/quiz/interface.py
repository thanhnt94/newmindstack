from typing import List, Optional
from .schemas import QuizItemDTO, QuizSetDTO
from mindstack_app.models import LearningContainer, LearningItem

def get_quiz_set_details(set_id: int) -> Optional[QuizSetDTO]:
    """Public API to get quiz set details."""
    container = LearningContainer.query.get(set_id)
    if not container or container.container_type != 'QUIZ_SET':
        return None
        
    count = LearningItem.query.filter(
        LearningItem.container_id == set_id,
        LearningItem.item_type.in_(['QUESTION', 'QUIZ_MCQ'])
    ).count()
    
    return QuizSetDTO(
        id=container.container_id,
        title=container.title,
        description=container.description,
        question_count=count,
        creator_name=container.host.username if hasattr(container, 'host') and container.host else "Unknown"
    )

def transcribe_quiz_audio(task):
    """
    Trigger transcription of audio for quiz items.
    Delegates to QuizAudioService.
    """
    from .services.audio_service import QuizAudioService
    service = QuizAudioService()
    return service.transcribe_quiz_audio(task)

def get_all_quiz_configs():
    """
    Get all quiz configuration settings.
    Delegates to QuizConfigService.
    """
    from .services.quiz_config_service import QuizConfigService
    return QuizConfigService.get_all()
