# mindstack_app/modules/vocabulary/logics/flashcard_modes.py
from mindstack_app.modules.vocab_flashcard.engine.vocab_flashcard_mode import FlashcardMode, register_flashcard_modes

VOCAB_MODES = [
    FlashcardMode(
        id='mixed_srs',
        label='Học tập',
        icon='fa-brain',
        color='emerald',
        filter_method='filter_mixed',
        description='Ưu tiên thẻ cần ôn tập (ngẫu nhiên), sau đó đến thẻ mới.'
    ),
    FlashcardMode(
        id='all_review',
        label='Ôn tập',
        icon='fa-rotate',
        color='blue',
        filter_method='filter_all_review',
        description='Ôn lại tất cả các từ đã học (ngẫu nhiên).'
    )
]

def register_vocabulary_flashcard_modes():
    """Register flashcard modes specific to the Vocabulary module."""
    register_flashcard_modes('vocab', VOCAB_MODES)
