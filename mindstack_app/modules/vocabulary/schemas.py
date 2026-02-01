from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class VocabItemDTO:
    """Represents a vocabulary item."""
    id: int
    front: str
    back: str
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
    ai_explanation: Optional[str] = None

@dataclass
class VocabSetDTO:
    """Represents a vocabulary set/container."""
    id: int
    title: str
    description: Optional[str]
    item_count: int
    creator_name: str
