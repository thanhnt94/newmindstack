from typing import Optional
from .schemas import TranslationResponseDTO
from .services import TranslatorService

def translate_text(text: str, source: str = 'auto', target: str = 'vi', user_id: Optional[int] = None) -> TranslationResponseDTO:
    """
    Public API to translate text.
    """
    result = TranslatorService.translate_text(text, source, target, user_id)
    
    if result:
        return TranslationResponseDTO(
            original=text,
            translated=result,
            source=source,
            target=target,
            success=True
        )
    return TranslationResponseDTO(
        original=text,
        translated="",
        source=source,
        target=target,
        success=False,
        error="Translation failed"
    )
