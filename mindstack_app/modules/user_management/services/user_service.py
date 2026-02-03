from typing import Optional, List, Dict, Any
from mindstack_app.core.extensions import db
from mindstack_app.modules.auth.models import User
from sqlalchemy import or_

class UserService:
    """Service layer for user management operations."""

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Fetch user by ID."""
        return User.query.get(user_id)

    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Fetch user by username."""
        return User.query.filter_by(username=username).first()

    @staticmethod
    def get_all_users(page: int = 1, per_page: int = 20) -> Any:
        """Fetch all users with pagination."""
        return User.query.order_by(User.user_id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

    @staticmethod
    def search_users(query: str, limit: int = 50) -> List[User]:
        """Search users by username or email."""
        if not query:
            return []
        search = f"%{query}%"
        return User.query.filter(
            or_(User.username.ilike(search), User.email.ilike(search))
        ).limit(limit).all()

    @staticmethod
    def update_user_profile(user_id: int, data: Dict[str, Any]) -> bool:
        """Update user profile data."""
        user = User.query.get(user_id)
        if not user:
            return False
        
        # Allowed fields to update
        allowed_fields = ['email', 'timezone', 'avatar_url']
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])
        
        if 'password' in data and data['password']:
            user.set_password(data['password'])
            
        db.session.commit()
        return True

    @staticmethod
    def delete_user(user_id: int) -> bool:
        """Delete a user."""
        user = User.query.get(user_id)
        if not user:
            return False
        
        db.session.delete(user)
        db.session.commit()
        return True

    @staticmethod
    def create_user(data: Dict[str, Any]) -> Optional[User]:
        """Create a new user (Admin helper)."""
        try:
            user = User(
                username=data.get('username'),
                email=data.get('email'),
                user_role=data.get('user_role', User.ROLE_FREE)
            )
            if data.get('password'):
                user.set_password(data['password'])
            
            db.session.add(user)
            db.session.commit()
            return user
        except Exception:
            db.session.rollback()
            return None
