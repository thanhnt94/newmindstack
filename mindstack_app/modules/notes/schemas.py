from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class NoteDTO:
    id: int
    user_id: int
    reference_type: str
    reference_id: Optional[int]
    title: Optional[str]
    content: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
