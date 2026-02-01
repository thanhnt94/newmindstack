from dataclasses import dataclass, field

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
    card_count: int
    creator_name: str
    cover_image: Optional[str] = None
    is_public: bool = False
    ai_capabilities: List[str] = field(default_factory=list)


    @property
    def container_id(self):
        """Property alias for backward compatibility with older templates."""
        return self.id



@dataclass
class VocabDashboardStatsDTO:
    """Global stats for the vocabulary dashboard."""
    total_items: int
    learned_items: int
    mastery_score: float
    active_days: int
    streak: int

@dataclass
class VocabSetDetailDTO:
    """Detailed information for a vocabulary set view."""
    set_info: VocabSetDTO
    stats: Dict[str, Any]
    capabilities: List[str]
    can_edit: bool

