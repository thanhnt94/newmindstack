"""
CardPresenter - The Assembler Service
======================================
Acts as a thin presentation layer that builds flashcard data for the frontend.
It does NOT implement business logic - it only fetches and assembles data from
other modules/services.

Design Principle:
- Does NOT implement TTS/audio generation logic
- Does NOT implement image search/download logic  
- Delegates to audio.interface and content_management.interface
- Returns data matching FlashcardContentSchema contract
"""

from typing import Optional, Dict, Any, List
from flask import url_for, current_app
from flask_login import current_user

from mindstack_app.models import LearningItem, LearningContainer
from mindstack_app.modules.fsrs.models import ItemMemoryState
from mindstack_app.utils.content_renderer import render_content_dict
from mindstack_app.utils.media_paths import build_relative_media_path

# Import for async-to-sync wrapping
import asyncio
from mindstack_app.modules.audio.interface import AudioInterface


class CardPresenter:
    """
    Assembles flashcard data from multiple sources.
    This is the single point for building card payloads for the frontend.
    """

    @staticmethod
    def build_card(
        item_id: int,
        user_id: int,
        include_stats: bool = True,
        include_edit_url: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Build a complete flashcard data payload.
        
        Args:
            item_id: The learning item ID
            user_id: Current user ID for permission checks
            include_stats: Whether to include FSRS statistics
            include_edit_url: Whether to include edit URL (requires permission check)
            
        Returns:
            Dictionary matching FlashcardResponseSchema structure, or None if not found.
        """
        item = LearningItem.query.get(item_id)
        if not item:
            return None
            
        container = item.container
        
        # Build content with resolved media URLs
        content = CardPresenter._build_content(item, container)
        
        # Permission check for editing
        can_edit = False
        edit_url = ''
        if include_edit_url and container:
            can_edit = CardPresenter._can_user_edit(user_id, container)
            if can_edit:
                edit_url = url_for(
                    'content_management.edit_flashcard_item',
                    set_id=container.container_id,
                    item_id=item_id
                )
        
        # Get initial stats
        initial_stats = {}
        is_first_time_card = True
        if include_stats:
            from ..engine.core import FlashcardEngine
            initial_stats = FlashcardEngine.get_item_statistics(user_id, item_id)
            
            progress = ItemMemoryState.query.filter_by(
                user_id=user_id, item_id=item_id
            ).first()
            is_first_time_card = (progress is None or progress.state == 0)
        
        return {
            'item_id': item.item_id,
            'container_id': item.container_id,
            'content': content,
            'ai_explanation': item.ai_explanation,
            'can_edit': can_edit,
            'edit_url': edit_url,
            'initial_stats': initial_stats,
            'initial_streak': initial_stats.get('current_streak', 0),
            'is_first_time_card': is_first_time_card
        }

    @staticmethod
    def build_cards_batch(
        item_ids: List[int],
        user_id: int,
        include_stats: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Build multiple flashcard payloads efficiently.
        
        Args:
            item_ids: List of item IDs to build
            user_id: Current user ID
            include_stats: Whether to include FSRS statistics
            
        Returns:
            List of card dictionaries
        """
        # Batch fetch items
        items = LearningItem.query.filter(LearningItem.item_id.in_(item_ids)).all()
        items_by_id = {item.item_id: item for item in items}
        
        result = []
        for item_id in item_ids:
            item = items_by_id.get(item_id)
            if item:
                card = CardPresenter.build_card(item_id, user_id, include_stats)
                if card:
                    result.append(card)
        
        return result

    @staticmethod
    def _build_content(item: LearningItem, container: Optional[LearningContainer]) -> Dict[str, Any]:
        """
        Build the content dictionary with resolved media URLs.
        
        Delegates media path resolution to utility functions.
        Does NOT implement any media generation logic.
        """
        # Get media folders from container settings
        media_folders = {}
        if container:
            media_folders = dict(getattr(container, 'media_folders', {}) or {})
            if not media_folders:
                settings_payload = container.ai_settings or {}
                if isinstance(settings_payload, dict):
                    media_folders = dict(settings_payload.get('media_folders') or {})
        
        # Render content (handles markdown, etc.)
        rendered_content = render_content_dict(item.content) if item.content else {}
        
        # Resolve media URLs
        def resolve_url(file_path: Optional[str], media_type: Optional[str] = None) -> Optional[str]:
            if not file_path:
                return None
            try:
                relative_path = build_relative_media_path(
                    file_path, 
                    media_folders.get(media_type) if media_type else None
                )
                if not relative_path:
                    return None
                if relative_path.startswith(('http://', 'https://')):
                    return relative_path
                return url_for('media_uploads', filename=relative_path.lstrip('/'), _external=True)
            except Exception:
                return None
        
        raw_content = item.content or {}
        
        front_text = raw_content.get('front_audio_content') or rendered_content.get('front', '')
        back_text = raw_content.get('back_audio_content') or rendered_content.get('back', '')
        
        front_url = resolve_url(raw_content.get('front_audio_url'), 'audio')
        back_url = resolve_url(raw_content.get('back_audio_url'), 'audio')
        
        # --- Pre-generate Audio if missing ---
        def ensure_audio_synced(text, current_url):
            if not text or current_url:
                return current_url
            
            try:
                # Sync wrapper for centralized AudioInterface
                # If we're already in a loop, this might need a different approach, 
                # but for standard Flask it's fine.
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(AudioInterface.generate_audio(text=text))
                loop.close()
                return result.url if result and result.url else None
            except Exception as e:
                current_app.logger.warning(f"Failed to pre-generate audio for card: {e}")
                return None

        # Only pre-generate if we have actual text beyond just HTML tags
        from mindstack_app.modules.audio.logics.voice_parser import VoiceParser
        if front_text and not front_url and VoiceParser.strip_prompts(front_text).strip():
            front_url = ensure_audio_synced(front_text, None)
            
        if back_text and not back_url and VoiceParser.strip_prompts(back_text).strip():
            back_url = ensure_audio_synced(back_text, None)

        return {
            'front': rendered_content.get('front', ''),
            'back': rendered_content.get('back', ''),
            'front_audio_content': front_text,
            'front_audio_url': front_url,
            'back_audio_content': back_text,
            'back_audio_url': back_url,
            'front_img': resolve_url(raw_content.get('front_img'), 'image'),
            'back_img': resolve_url(raw_content.get('back_img'), 'image'),
        }

    @staticmethod
    def _can_user_edit(user_id: int, container: LearningContainer) -> bool:
        """Check if user has permission to edit items in this container."""
        from mindstack_app.models import User, ContainerContributor
        
        # Admin can edit everything
        if hasattr(current_user, 'user_role') and current_user.user_role == User.ROLE_ADMIN:
            return True
        
        # Owner can edit
        if container.creator_user_id == user_id:
            return True
        
        # Check contributor status
        contributor = ContainerContributor.query.filter_by(
            container_id=container.container_id,
            user_id=user_id,
            permission_level='editor'
        ).first()
        
        return contributor is not None


# =============================================================================
# Utility Functions for Media Resolution
# =============================================================================

def get_audio_url_for_item(item: LearningItem, side: str = 'front') -> Optional[str]:
    """
    Get the audio URL for a specific side of a flashcard.
    
    This function does NOT generate audio - it only resolves existing URLs.
    For audio generation, use audio.interface.AudioInterface.generate_audio()
    
    Args:
        item: The learning item
        side: 'front' or 'back'
        
    Returns:
        Resolved audio URL or None
    """
    content = item.content or {}
    audio_path = content.get(f'{side}_audio_url')
    
    if not audio_path:
        return None
    
    container = item.container
    media_folders = {}
    if container:
        media_folders = dict(getattr(container, 'media_folders', {}) or {})
    
    try:
        relative_path = build_relative_media_path(audio_path, media_folders.get('audio'))
        if relative_path and not relative_path.startswith(('http://', 'https://')):
            return url_for('media_uploads', filename=relative_path.lstrip('/'), _external=True)
        return relative_path
    except Exception:
        return None


def get_image_url_for_item(item: LearningItem, side: str = 'front') -> Optional[str]:
    """
    Get the image URL for a specific side of a flashcard.
    
    This function does NOT download/generate images - it only resolves existing URLs.
    
    Args:
        item: The learning item
        side: 'front' or 'back'
        
    Returns:
        Resolved image URL or None
    """
    content = item.content or {}
    image_path = content.get(f'{side}_img')
    
    if not image_path:
        return None
    
    container = item.container
    media_folders = {}
    if container:
        media_folders = dict(getattr(container, 'media_folders', {}) or {})
    
    try:
        relative_path = build_relative_media_path(image_path, media_folders.get('image'))
        if relative_path and not relative_path.startswith(('http://', 'https://')):
            return url_for('media_uploads', filename=relative_path.lstrip('/'), _external=True)
        return relative_path
    except Exception:
        return None
