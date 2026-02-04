# File: mindstack_app/modules/media/schemas.py
"""DTOs for media module."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class MediaRequestDTO:
    """Request DTO for image search/download."""
    text: str
    max_results: int = 8


@dataclass
class MediaResponseDTO:
    """Response DTO for image operations."""
    status: str  # 'success', 'cached', 'error'
    file_path: Optional[str] = None  # Absolute path
    relative_path: Optional[str] = None  # Relative to UPLOAD_FOLDER
    error: Optional[str] = None
