"""
Auth Service - Core Local Authentication logic.
Handles user registration, login, and password management for the local database.
"""
from flask import current_app
from mindstack_app.core.extensions import db
from mindstack_app.models import AppSettings
from ..models import User, UserSession
from mindstack_app.core.signals import user_registered

class AuthService:
    """Service for Local Authentication related operations."""

    @staticmethod
    def get_config(key: str, default=None):
        """Get config with fail-safe fallback."""
        try:
            return AppSettings.get(key, default)
        except:
            return default

    @staticmethod
    def register_user(username, email, password, full_name=None):
        """Register a new user in the local database."""
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            user_role=User.ROLE_FREE,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush() 

        user_session = UserSession(user_id=user.user_id)
        db.session.add(user_session)
        db.session.commit()
        
        current_app.logger.info(f"Local user registered: {username} ({user.user_id})")

        try:
            user_registered.send(current_app._get_current_object(), user=user)
        except Exception as e:
            current_app.logger.error(f"Error emitting user_registered signal: {e}")
            
        return user

    @staticmethod
    def authenticate_user(username_or_email, password):
        """
        Verify credentials strictly against the local database.
        """
        user = User.query.filter_by(username=username_or_email).first()
        if not user:
            user = User.query.filter_by(email=username_or_email).first()
            
        if user and user.check_password(password):
            return user
        return None
