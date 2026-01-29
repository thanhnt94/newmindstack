from typing import Optional, Dict, Any, List
from flask import current_app
from mindstack_app.services.note_service import NoteKernelService
from mindstack_app.models import db, Note, LearningItem, LearningContainer
from .logics.content_processor import NoteContentProcessor

class NoteOrchestrator:
    @staticmethod
    def get_note_for_ui(user_id: int, reference_type: str, reference_id: int) -> Dict[str, Any]:
        note = NoteKernelService.get_user_note_for_entity(user_id, reference_type, reference_id)
        if not note:
            return {'success': True, 'content': '', 'exists': False}
        
        return {
            'success': True,
            'note_id': note.note_id,
            'content': note.content,
            'title': note.title,
            'updated_at': note.updated_at.isoformat() if note.updated_at else None,
            'exists': True
        }

    @staticmethod
    def save_note(user_id: int, reference_type: str, reference_id: int, content: str, title: Optional[str] = None) -> Dict[str, Any]:
        # 1. Permission check
        if not NoteOrchestrator._can_user_note_entity(user_id, reference_type, reference_id):
            return {'success': False, 'message': 'Permission denied'}
        
        # 2. Sanitize content
        clean_content = NoteContentProcessor.sanitize(content)
        
        # 3. Save via kernel
        note = NoteKernelService.get_user_note_for_entity(user_id, reference_type, reference_id)
        if note:
            NoteKernelService.update_note(note, content=clean_content, title=title)
        else:
            # Auto-title if none provided
            if not title:
                title = NoteOrchestrator._generate_default_title(reference_type, reference_id)
            
            note = NoteKernelService.create_note(user_id, reference_type, reference_id, clean_content, title=title)
            
        try:
            db.session.commit()
            return {
                'success': True, 
                'message': 'Saved successfully', 
                'note_id': note.note_id,
                'content': note.content
            }
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving note: {e}")
            return {'success': False, 'message': 'Internal server error'}

    @staticmethod
    def _can_user_note_entity(user_id: int, reference_type: str, reference_id: int) -> bool:
        """Centralized permission check for creating/editing notes."""
        # For now, allow all authenticated users but could add specific checks
        # e.g. check if item belongs to a set the user has access to
        if reference_type == 'item':
            item = LearningItem.query.get(reference_id)
            return item is not None
        elif reference_type == 'container':
            container = LearningContainer.query.get(reference_id)
            return container is not None
        
        return True

    @staticmethod
    def _generate_default_title(reference_type: str, reference_id: int) -> str:
        if reference_type == 'item':
            item = LearningItem.query.get(reference_id)
            if item:
                return f"Note: {item.term or 'Item ' + str(reference_id)}"
        elif reference_type == 'container':
            container = LearningContainer.query.get(reference_id)
            if container:
                return f"Ghi chú cho bộ: {container.title}"
        
        return f"Ghi chú {reference_type} #{reference_id}"

    @staticmethod
    def get_manage_notes_data(user_id: int) -> List[Dict[str, Any]]:
        notes = NoteKernelService.list_user_notes(user_id)
        result = []
        
        # Batch fetch items and containers to avoid N+1
        item_ids = [n.reference_id for n in notes if n.reference_type == 'item']
        container_ids = [n.reference_id for n in notes if n.reference_type == 'container']
        
        item_map = {i.item_id: i for i in LearningItem.query.filter(LearningItem.item_id.in_(item_ids)).all()}
        container_map = {c.container_id: c for c in LearningContainer.query.filter(LearningContainer.container_id.in_(container_ids)).all()}
        
        for n in notes:
            ref_obj = None
            if n.reference_type == 'item':
                ref_obj = item_map.get(n.reference_id)
            elif n.reference_type == 'container':
                ref_obj = container_map.get(n.reference_id)
            
            result.append({
                'note': n,
                'reference_object': ref_obj,
                'summary': NoteContentProcessor.format_summary(n.content)
            })
            
        return result
