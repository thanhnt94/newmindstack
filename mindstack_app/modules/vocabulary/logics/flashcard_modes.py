# mindstack_app/modules/vocabulary/logics/flashcard_modes.py
from mindstack_app.modules.vocab_flashcard.engine.vocab_flashcard_mode import FlashcardMode, register_flashcard_modes

VOCAB_MODES = [
    FlashcardMode(
        id='mixed_srs',
        label='Học tập',
        icon='fa-book-reader',
        color='blue',
        filter_method='filter_mixed',
        description='Chế độ học kết hợp từ mới và ôn tập từ cũ.'
    )
]

def register_vocabulary_flashcard_modes():
    """Register flashcard modes specific to the Vocabulary module."""
    register_flashcard_modes('vocab', VOCAB_MODES)
