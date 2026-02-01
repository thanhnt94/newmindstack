from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class FeedbackDTO:
    id: Optional[int]
    user_id: int
    type: str
    content: str
    status: str
    created_at: Optional[datetime]
    context_url: Optional[str] = None
    attachments: Optional[List[str]] = None
