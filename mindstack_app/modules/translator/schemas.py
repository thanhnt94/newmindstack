from dataclasses import dataclass
from typing import Optional

@dataclass
class TranslationRequestDTO:
    text: str
    source: str = 'auto'
    target: str = 'vi'

@dataclass
class TranslationResponseDTO:
    original: str
    translated: str
    source: str
    target: str
    success: bool
    error: Optional[str] = None
