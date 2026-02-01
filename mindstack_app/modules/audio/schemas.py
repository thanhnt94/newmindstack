# File: mindstack_app/modules/audio/schemas.py
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class AudioRequestDTO:
    text: str
    engine: str = 'edge'
    voice: Optional[str] = None
    target_dir: Optional[str] = None
    custom_filename: Optional[str] = None
    is_manual: bool = False
    auto_voice_parsing: bool = False

@dataclass
class AudioResponseDTO:
    status: str
    url: Optional[str] = None
    physical_path: Optional[str] = None
    error: Optional[str] = None

@dataclass
class AudioSettingsDTO:
    default_engine: str
    default_voice_edge: str
    default_voice_gtts: str
    voice_mapping: Dict[str, str] = field(default_factory=dict)
