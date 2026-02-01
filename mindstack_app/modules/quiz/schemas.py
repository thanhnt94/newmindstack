from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class QuizItemDTO:
    id: int
    question: str
    options: Dict[str, str]
    correct_answer: str
    explanation: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None

@dataclass
class QuizSetDTO:
    id: int
    title: str
    description: Optional[str]
    question_count: int
    creator_name: str
