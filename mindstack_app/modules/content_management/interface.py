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
    def _resolve_media_url(path: str) -> str:
        """Ensure media path is absolute URL."""
        if not path:
            return ""
        if path.startswith('http') or path.startswith('//'):
            return path
        if not path.startswith('/'):
            path = '/' + path
        if not path.startswith('/static'):
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
                    "audio": ContentInterface._resolve_media_url(raw_content.get('audio', '')),
                    "image": ContentInterface._resolve_media_url(raw_content.get('image', '')),
                    "explanation": item.ai_explanation or raw_content.get('explanation', '')
                })
                
            elif item.item_type == 'QUIZ_MCQ':
                standardized.update({
                    "question": raw_content.get('question', ''),
                    "options": raw_content.get('options', {}),
                    "correct_option": raw_content.get('correct_option', ''),
                    "explanation": item.ai_explanation or raw_content.get('explanation', ''),
                    "image": ContentInterface._resolve_media_url(raw_content.get('image', ''))
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
        
        return False
