from typing import Optional, List, Dict, Any
from .schemas import NoteDTO
from .services.note_manager import NoteManager

def get_note(user_id: int, reference_type: str, reference_id: int) -> Dict[str, Any]:
    """Get a note for UI."""
    return NoteManager.get_note_for_ui(user_id, reference_type, reference_id)

def save_note(user_id: int, reference_type: str, reference_id: int, content: str, title: Optional[str] = None) -> Dict[str, Any]:
    """Save a note."""
    return NoteManager.save_note(user_id, reference_type, reference_id, content, title)

def list_notes(user_id: int) -> List[Dict[str, Any]]:
    """List all notes for management UI."""
    return NoteManager.get_manage_notes_data(user_id)
