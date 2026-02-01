from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class ContainerDTO:
    id: int
    type: str
    title: str
    description: Optional[str]
    cover_image: Optional[str]
    tags: Optional[str]
    is_public: bool
    creator_id: int

@dataclass
class ItemDTO:
    id: int
    container_id: int
    type: str
    content: Dict[str, Any]
    order: int
