from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class DashboardDataDTO:
    flashcard_summary: Dict[str, Any]
    quiz_summary: Dict[str, Any]
    course_summary: Dict[str, Any]
    score_overview: Dict[str, Any]
    motivation_message: str
    shortcut_actions: List[Dict[str, str]]
    goal_progress: Any
