from typing import Optional
from .schemas import TranslationResponseDTO
from .services import TranslatorService

def translate_text(text: str, source: str = 'auto', target: str = 'vi', user_id: Optional[int] = None) -> TranslationResponseDTO:
    """
    Public API to translate text.
    """
    result_data = TranslatorService.translate_text(text, source, target, user_id)
    
    if result_data:
        return TranslationResponseDTO(
            original=text,
            translated=result_data.get('translated', ""),
            source=source,
            target=target,
            success=True,
            kanji_details=result_data.get('kanji_details', [])
        )
    return TranslationResponseDTO(
        original=text,
        translated="",
        source=source,
        target=target,
        success=False,
        error="Translation failed"
    )
