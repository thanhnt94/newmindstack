from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class FlashcardSessionSettingsDTO:
    autoplay: bool = False
    show_image: bool = True
    button_count: int = 3

@dataclass
class FlashcardItemDTO:
    item_id: int
    front: str
    back: str
    front_img: Optional[str] = None
    back_img: Optional[str] = None
    front_audio_url: Optional[str] = None
    back_audio_url: Optional[str] = None

@dataclass
class FlashcardItemDTO:
    item_id: int
    front: str
    back: str
    front_img: Optional[str] = None
    back_img: Optional[str] = None
    front_audio_url: Optional[str] = None
    back_audio_url: Optional[str] = None
