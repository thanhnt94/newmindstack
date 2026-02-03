"""
Vocab Flashcard Schemas
=======================
DTOs and schemas for strict API contracts.
Uses dataclasses for Python 3.7+ compatibility without external dependencies.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List


# ==============================================================================
# Dataclass DTOs (Internal Use & API Serialization)
# ==============================================================================

@dataclass
class FlashcardSessionSettingsDTO:
    """Settings for a flashcard learning session."""
    autoplay: bool = False
    show_image: bool = True
    button_count: int = 3


@dataclass
class FlashcardContentDTO:
    """
    Schema for flashcard content returned to frontend.
    Provides strict contract between Backend and Frontend.
    """
    front: str = ''
    back: str = ''
    hint: Optional[str] = None
    
    # Media URLs
    front_audio_url: Optional[str] = None
    back_audio_url: Optional[str] = None
    front_img: Optional[str] = None
    back_img: Optional[str] = None
    
    # Additional audio content for TTS
    front_audio_content: Optional[str] = None
    back_audio_content: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class FlashcardItemDTO:
    """Internal DTO for flashcard item data."""
    item_id: int
    front: str
    back: str
    front_img: Optional[str] = None
    back_img: Optional[str] = None
    front_audio_url: Optional[str] = None
    back_audio_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass 
class FlashcardResponseDTO:
    """
    Full flashcard response for API endpoints.
    Used by CardPresenter to serialize card data.
    """
    item_id: int
    container_id: Optional[int] = None
    content: Optional[FlashcardContentDTO] = None
    ai_explanation: Optional[str] = None
    initial_stats: Optional[Dict[str, Any]] = None
    session_status: Optional[Dict[str, Any]] = None
    can_edit: bool = False
    edit_url: str = ''
    is_first_time_card: bool = True
    initial_streak: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        if self.content:
            result['content'] = self.content.to_dict()
        return result


@dataclass
class FlashcardBatchResponseDTO:
    """DTO for batch endpoint response."""
    items: List[FlashcardResponseDTO] = field(default_factory=list)
    session_correct_answers: int = 0
    session_incorrect_answers: int = 0
    session_vague_answers: int = 0
    session_total_answered: int = 0
    session_points: int = 0
    session_total_items: int = 0
    session_processed_count: int = 0
    container_name: str = ''
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result['items'] = [item.to_dict() for item in self.items]
        return result


# Backward compatibility aliases
FlashcardContentSchema = FlashcardContentDTO
FlashcardResponseSchema = FlashcardResponseDTO
