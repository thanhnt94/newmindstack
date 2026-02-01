"""
User Profile Service - Logic for profile management.

Handles avatar uploads, profile updates, and password changes.
"""
import os
from werkzeug.utils import secure_filename
from flask import current_app

from mindstack_app.models import db, User
from mindstack_app.core.signals import profile_updated

class UserProfileService:
    """Service for managing user profiles."""

    @staticmethod
    def update_profile_info(user: User, username=None, email=None, timezone=None):
        """
        Update basic profile information.
        """
        changes = []
        
        if username and user.username != username:
            user.username = username
            changes.append('username')
            
        if email and user.email != email:
            user.email = email
            changes.append('email')
            
        if timezone and user.timezone != timezone:
            user.timezone = timezone
            changes.append('timezone')
            
        if changes:
            db.session.commit()
            # Emit signal
            profile_updated.send(current_app._get_current_object(), user=user, changes=changes)
            
        return changes

    @staticmethod
    def update_avatar(user: User, file_storage):
        """
        Handle avatar upload and file saving.
        """
        if not file_storage:
            return None
            
        # Secure filename
        filename = secure_filename(f"avatar_{user.user_id}_{file_storage.filename}")
        
        # Ensure directory exists
        upload_folder = current_app.config['UPLOAD_FOLDER']
        avatar_dir = os.path.join(upload_folder, 'avatars')
        if not os.path.exists(avatar_dir):
            os.makedirs(avatar_dir)
            
        # Save file
        file_path = os.path.join(avatar_dir, filename)
        file_storage.save(file_path)
        
        # Update User Record (store relative path)
        relative_path = f"avatars/{filename}"
        user.avatar_url = relative_path
        db.session.commit()
        
        current_app.logger.info(f"Avatar updated for user {user.user_id}")
        
        # Emit signal
        profile_updated.send(
            current_app._get_current_object(), 
            user=user, 
            changes=['avatar']
        )
        
        return relative_path

    @staticmethod
    def change_password(user: User, new_password):
        """Change user password."""
        user.set_password(new_password)
        db.session.commit()
        # Security sensitive - maybe email notification listener later?
        return True
