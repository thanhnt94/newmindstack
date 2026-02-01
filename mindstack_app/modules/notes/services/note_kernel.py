from datetime import datetime, timezone
from typing import Optional, List
from mindstack_app.models import db, Note

class NoteKernelService:
    @staticmethod
    def get_note_by_id(note_id: int) -> Optional[Note]:
        return Note.query.get(note_id)

    @staticmethod
    def get_user_note_for_entity(user_id: int, reference_type: str, reference_id: int) -> Optional[Note]:
        return Note.query.filter_by(
            user_id=user_id,
            reference_type=reference_type,
            reference_id=reference_id
        ).first()

    @staticmethod
    def create_note(user_id: int, reference_type: str, reference_id: int, content: str, title: Optional[str] = None, tags: Optional[str] = None) -> Note:
        note = Note(
            user_id=user_id,
            reference_type=reference_type,
            reference_id=reference_id,
            content=content,
            title=title,
            tags=tags
        )
        db.session.add(note)
        # Flush to get ID if needed, but usually commit is at higher level
        return note

    @staticmethod
    def update_note(note: Note, content: Optional[str] = None, title: Optional[str] = None, tags: Optional[str] = None, is_archived: Optional[bool] = None) -> Note:
        if content is not None:
            note.content = content
        if title is not None:
            note.title = title
        if tags is not None:
            note.tags = tags
        if is_archived is not None:
            note.is_archived = is_archived
        
        # updated_at is handled by the model
        return note

    @staticmethod
    def delete_note(note: Note):
        db.session.delete(note)

    @staticmethod
    def list_user_notes(user_id: int, reference_type: Optional[str] = None, is_archived: bool = False) -> List[Note]:
        query = Note.query.filter_by(user_id=user_id, is_archived=is_archived)
        if reference_type:
            query = query.filter_by(reference_type=reference_type)
        return query.order_by(Note.updated_at.desc()).all()

    @staticmethod
    def bulk_delete_notes_for_entity(reference_type: str, reference_id: int):
        Note.query.filter_by(reference_type=reference_type, reference_id=reference_id).delete(synchronize_session=False)
