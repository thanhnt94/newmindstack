# File: mindstack_app/modules/admin/schemas.py
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class ModuleStatusDTO:
    key: str
    name: str
    is_active: bool
    is_core: bool
