"""
Auth Service - Core authentication logic.

Handles user registration and authentication details.
Decouples DB logic from Routes.
"""
from flask import current_app
from mindstack_app.core.extensions import db
from mindstack_app.models import AppSettings
from ..models import User, UserSession
from ..config import AuthModuleDefaultConfig
from mindstack_app.core.signals import user_registered

class AuthService:
    """Service for Authentication related operations."""

    @staticmethod
    def get_config(key: str, default=None):
        """Get config with fallback: Database -> core/defaults.py -> manual default."""
        return AppSettings.get(key, default)

    @staticmethod
    def register_user(username, email, password):
        """
        Register a new user, create session, and emit signal.
        
        Returns:
            User object if successful
        Raises:
            Exception if validation fails
        """
        # 1. Create User
        user = User(
            username=username,
            email=email,
            user_role=User.ROLE_FREE,
        )
        user.set_password(password)
        db.session.add(user)
        
        # Flush to get ID (needed for session and signals)
        db.session.flush() 

        # 2. Create initial session state (legacy requirement)
        user_session = UserSession(user_id=user.user_id)
        db.session.add(user_session)

        # 3. Commit
        db.session.commit()
        
        current_app.logger.info(f"User registered: {username} ({user.user_id})")

        # 4. Emit Signal (Event Driven)
        try:
            user_registered.send(current_app._get_current_object(), user=user)
        except Exception as e:
            current_app.logger.error(f"Error emitting user_registered signal: {e}")
            
        return user

    @staticmethod
    def authenticate_user(username_or_email, password):
        """
        Verify credentials.
        
        Returns:
            User object if valid, None otherwise.
        """
        user = User.query.filter_by(username=username_or_email).first()
        
        if user and user.check_password(password):
            return user
            
        return None
