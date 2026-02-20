# mindstack_app/modules/vocabulary/logics/flashcard_modes.py
from mindstack_app.modules.vocabulary.flashcard.interface import FlashcardInterface

FlashcardMode = FlashcardInterface.get_flashcard_mode_class()

VOCAB_MODES = [
    FlashcardMode(
        id='srs',
        label='Học tập (SRS)',
        icon='fa-brain',
        color='emerald',
        filter_method='filter_srs',
        description='Học tập theo thuật toán FSRS: Ưu tiên thẻ đến hạn, sau đó đến thẻ mới.'
    ),
    FlashcardMode(
        id='cram',
        label='Cram Mode (Ôn tập)',
        icon='fa-random',
        color='amber',
        filter_method='filter_cram',
        description='Ôn tập ngẫu nhiên các thẻ đã học. Có tính vào tiến độ SRS.'
    )
]

def register_vocabulary_flashcard_modes():
    """Register flashcard modes specific to the Vocabulary module."""
    FlashcardInterface.register_flashcard_modes('vocab', VOCAB_MODES)
