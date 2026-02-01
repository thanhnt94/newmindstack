from dataclasses import dataclass
from typing import Optional, Any

@dataclass
class AIRequestDTO:
    """Standard request object for AI generation."""
    prompt: str
    feature: str = "general"
    context_ref: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None

@dataclass
class AIResponseDTO:
    """Standard response object from AI."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None
