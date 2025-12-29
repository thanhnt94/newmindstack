"""
Learning Settings Service
=========================
Centralizes management of user settings for different learning modules.
Handles persistence, deep merging, and session configuration resolution.
"""

from typing import Any, Dict, Optional
from mindstack_app.models import db, UserContainerState, User
from mindstack_app.modules.shared.utils.db_session import safe_commit

class LearningSettingsService:
    @staticmethod
    def get_container_settings(user_id: int, container_id: int) -> Dict[str, Any]:
        """Fetch all settings for a specific container and user."""
        uc_state = UserContainerState.query.filter_by(
            user_id=user_id,
            container_id=container_id
        ).first()
        return uc_state.settings if uc_state and uc_state.settings else {}

    @staticmethod
    def update_container_settings(user_id: int, container_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update settings with deep merge protection for module-specific keys.
        payload can contain: auto_save, last_mode, flashcard {}, quiz {}, etc.
        """
        uc_state = UserContainerState.query.filter_by(
            user_id=user_id,
            container_id=container_id
        ).first()
        
        if not uc_state:
            uc_state = UserContainerState(
                user_id=user_id,
                container_id=container_id,
                is_archived=False,
                is_favorite=False,
                settings={}
            )
            db.session.add(uc_state)
            
        current_settings = dict(uc_state.settings or {})
        
        # 1. Update Global Auto-Save
        if 'auto_save' in payload:
            current_settings['auto_save'] = bool(payload['auto_save'])
            
        # 2. Update Last Mode
        if 'last_mode' in payload:
            current_settings['last_mode'] = str(payload['last_mode'])

        # 3. Deep Merge Module Settings (Flashcard, Quiz, etc.)
        for key, value in payload.items():
            if key in ['flashcard', 'quiz', 'listening', 'typing', 'memrise'] and isinstance(value, dict):
                if key not in current_settings or not isinstance(current_settings[key], dict):
                    current_settings[key] = {}
                # Update sub-keys
                for sub_key, sub_value in value.items():
                    current_settings[key][sub_key] = sub_value
        
        uc_state.settings = current_settings
        db.session.add(uc_state)
        safe_commit(db.session)
        return uc_state.settings

    @staticmethod
    def resolve_flashcard_session_config(user: User, container_id: int, url_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates the final configuration for a flashcard session and 
        handles auto-save persistence if enabled.
        
        Priority: URL Param > Persistent Setting > Global Pref > Default
        """
        uc_state = UserContainerState.query.filter_by(user_id=user.user_id, container_id=container_id).first()
        db_settings = uc_state.settings if uc_state and uc_state.settings else {}
        fc_persisted = db_settings.get('flashcard', {})
        global_prefs = user.last_preferences or {}
        
        # 1. Extract URL Parameters
        url_rating = url_params.get('rating_levels')
        url_autoplay = url_params.get('autoplay') == 'true' if 'autoplay' in url_params else None
        url_show_image = url_params.get('show_image') == 'true' if 'show_image' in url_params else None
        url_show_stats = url_params.get('show_stats') == 'true' if 'show_stats' in url_params else None

        # 2. Auto-Save Logic (Update DB if ON)
        auto_save_on = db_settings.get('auto_save', True)
        if auto_save_on and (url_rating or url_autoplay is not None or url_show_image is not None or url_show_stats is not None):
            update_payload = {'flashcard': {}}
            if url_rating: update_payload['flashcard']['button_count'] = url_rating
            if url_autoplay is not None: update_payload['flashcard']['autoplay'] = url_autoplay
            if url_show_image is not None: update_payload['flashcard']['show_image'] = url_show_image
            if url_show_stats is not None: update_payload['flashcard']['show_stats'] = url_show_stats
            
            # Persist
            LearningSettingsService.update_container_settings(user.user_id, container_id, update_payload)
            # Re-fetch persisted after update for final consolidation
            return LearningSettingsService.resolve_flashcard_session_config(user, container_id, {})

        # 3. Consolidate Final Config
        final_button_count = url_rating or fc_persisted.get('button_count') or global_prefs.get('flashcard_button_count') or 4
        
        visual_settings = {
            'autoplay': fc_persisted.get('autoplay', global_prefs.get('flashcard_autoplay_audio', False)),
            'show_image': fc_persisted.get('show_image', global_prefs.get('flashcard_show_image', True)),
            'show_stats': fc_persisted.get('show_stats', global_prefs.get('flashcard_show_stats', True))
        }
        
        # Apply URL transient overrides (if auto-save was OFF)
        if url_autoplay is not None: visual_settings['autoplay'] = url_autoplay
        if url_show_image is not None: visual_settings['show_image'] = url_show_image
        if url_show_stats is not None: visual_settings['show_stats'] = url_show_stats
        
        return {
            'button_count': final_button_count,
            'visual_settings': visual_settings,
            'auto_save': auto_save_on
        }
