# File: mindstack_app/modules/content_management/interface.py
"""
Content Management Interface (Public API)
=========================================
Standard interface for accessing learning content regardless of item type.
Provides absolute URLs for all media resources.
"""

from typing import Dict, List, Optional, Any
from flask import url_for
from mindstack_app.modules.content_management.services.kernel_service import ContentKernelService
from mindstack_app.models import LearningItem, LearningContainer

class ContentInterface:
    """Public API for Content Management module."""
    
    @staticmethod
    def _resolve_media_url(path: str, container: Optional[LearningContainer] = None) -> str:
        """Ensure media path is absolute URL, resolving via container settings if needed."""
        if not path:
            return ""
        if path.startswith('http') or path.startswith('//'):
            return path
            
        # Try to resolve relative to container folders using strict logic
        try:
            from mindstack_app.utils.media_paths import build_relative_media_path
            
            media_folders = {}
            if container:
                # Logic copied from CardPresenter for consistency
                media_folders = dict(getattr(container, 'media_folders', {}) or {})
                if not media_folders:
                    settings_payload = container.ai_settings or {}
                    if isinstance(settings_payload, dict):
                        media_folders = dict(settings_payload.get('media_folders') or {})
            
            # Determine type based on extension or assumption? 
            # build_relative_media_path takes the specific folder.
            # We don't verify type here easily, so we try generic resolution if path is relative.
            
            # Simple heuristic: if likely audio/image, look in respective folders
            folder = None
            lower_path = path.lower()
            if lower_path.endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                folder = media_folders.get('audio')
            elif lower_path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                folder = media_folders.get('image')
                
            relative_path = build_relative_media_path(path, folder)
            
            if relative_path:
                if relative_path.startswith(('http://', 'https://')):
                    return relative_path
                return url_for('media_uploads', filename=relative_path.lstrip('/'), _external=True)
                
        except Exception:
            pass
            
        # Fallback to static if resolution fails but it looks like a path
        if not path.startswith('/'):
            path = '/' + path
        if not path.startswith('/static') and not path.startswith('/media'):
            path = '/static' + path
        return path

    @staticmethod
    def get_items_content(item_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        Get standardized content for a list of item IDs.
        
        Returns:
            Dict mapping item_id -> content_dict
            
        Format:
            {
                101: {
                    "id": 101,
                    "type": "FLASHCARD",
                    "front": "Cà phê",
                    "back": "Coffee",
                    "audio": "/static/audio/cafe.mp3",  # Absolute path
                    "image": "/static/images/cafe.jpg", # Absolute path
                    "custom_data": {...}
                }
            }
        """
        if not item_ids:
            return {}
            
        # Bulk query for efficiency
        items = LearningItem.query.filter(LearningItem.item_id.in_(item_ids)).all()
        result = {}
        
        for item in items:
            raw_content = item.content or {}
            
            # Standardized structure
            standardized = {
                "id": item.item_id,
                "type": item.item_type,
                "custom_data": item.custom_data or {}
            }
            
            # Map item-specific fields
            if item.item_type == 'FLASHCARD':
                standardized.update({
                    "front": raw_content.get('front', ''),
                    "back": raw_content.get('back', ''),
                    "front_audio": ContentInterface._resolve_media_url(raw_content.get('front_audio_url', ''), item.container),
                    "back_audio": ContentInterface._resolve_media_url(raw_content.get('back_audio_url', ''), item.container),
                    "front_image": ContentInterface._resolve_media_url(raw_content.get('front_img', ''), item.container),
                    "back_image": ContentInterface._resolve_media_url(raw_content.get('back_img', ''), item.container),
                    "front_audio_content": raw_content.get('front_audio_content', ''),
                    "back_audio_content": raw_content.get('back_audio_content', ''),
                    "explanation": item.ai_explanation or raw_content.get('explanation', '')
                })
                
            elif item.item_type in ('QUIZ_MCQ', 'QUESTION'):
                # Normalize options (Handle legacy flat structure)
                options = raw_content.get('options') or {}
                if not options:
                    for k, f in [('A', 'option_a'), ('B', 'option_b'), ('C', 'option_c'), ('D', 'option_d')]:
                        val = raw_content.get(f)
                        if val not in (None, ''):
                            options[k] = val

                standardized.update({
                    "question": raw_content.get('question', ''),
                    "options": options,
                    "correct_option": raw_content.get('correct_option', ''),
                    "correct_answer": raw_content.get('correct_answer') or raw_content.get('correct_answer_text') or raw_content.get('correct_option', ''),
                    "explanation": item.ai_explanation or raw_content.get('explanation', ''),
                    "image": ContentInterface._resolve_media_url(raw_content.get('image') or raw_content.get('question_image_file'), item.container),
                    "audio": ContentInterface._resolve_media_url(raw_content.get('audio') or raw_content.get('question_audio_file'), item.container),
                    "audio_transcript": raw_content.get('audio_transcript', ''),
                    "pre_question_text": raw_content.get('pre_question_text', ''),
                    "passage_text": raw_content.get('passage_text', '')
                })
                
            # Default fallback for unknown types
            else:
                standardized.update(raw_content)
                
            result[item.item_id] = standardized
            
        return result

    @staticmethod
    def get_container_metadata(container_id: int) -> Optional[Dict[str, Any]]:
        """Get public metadata for a container."""
        container = ContentKernelService.get_container(container_id)
        if not container:
            return None
            
        return {
            "id": container.container_id,
            "title": container.title,
            "type": container.container_type,
            "description": container.description,
            "is_public": container.is_public,
            "item_count": len(container.items),
            "media_folders": container.media_folders
        }

    @staticmethod
    def verify_content_access(user_id: int, container_id: int) -> bool:
        """
        Check if user has access to this content.
        logic: Public OR Owner OR Shared (TODO)
        """
        container = ContentKernelService.get_container(container_id)
        if not container:
            return False
            
        # 1. Owner access
        if container.creator_user_id == user_id:
            return True
            
        # 2. Public access
        if container.is_public:
            return True
            
        # 3. TODO: Shared/Collaborative access check
        
        # 3. TODO: Shared/Collaborative access check
        
        return False

    @staticmethod
    def get_form_class(container_type: str):
        """
        Get the appropriate form class for a container type.
        Used by Admin module to render forms.
        """
        from .forms import CourseForm, FlashcardSetForm, QuizSetForm
        forms = {
            'COURSE': CourseForm,
            'FLASHCARD_SET': FlashcardSetForm,
            'QUIZ_SET': QuizSetForm
        }
        return forms.get(container_type.upper())

    @staticmethod
    def create_container(creator_id: int, container_type: str, **kwargs):
        """Wrapper for ContentKernelService.create_container."""
        return ContentKernelService.create_container(creator_id, container_type, **kwargs)

    @staticmethod
    def update_container(container_id: int, **kwargs):
        """Wrapper for ContentKernelService.update_container."""
        return ContentKernelService.update_container(container_id, **kwargs)

    @staticmethod
    def delete_container(container_id: int):
        """Wrapper for ContentKernelService.delete_container."""
        return ContentKernelService.delete_container(container_id)
