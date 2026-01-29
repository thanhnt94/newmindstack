"""Business logic validators for Content Management."""
from flask_login import current_user
from mindstack_app.models import User, ContainerContributor, LearningContainer

def has_container_access(container_id: int, level: str = 'editor') -> bool:
    """
    Check if the current user has access to a container.
    level can be 'viewer' or 'editor'.
    """
    if not current_user.is_authenticated:
        return False
        
    if current_user.user_role == User.ROLE_ADMIN:
        return True
        
    container = LearningContainer.query.get(container_id)
    if not container:
        return False
        
    if container.creator_user_id == current_user.user_id:
        return True
        
    # Free users can only access their own content
    if current_user.user_role == User.ROLE_FREE:
        return False
        
    # Check contributors
    contributor = ContainerContributor.query.filter_by(
        container_id=container_id,
        user_id=current_user.user_id
    ).first()
    
    if not contributor:
        return False
        
    if level == 'editor':
        return contributor.permission_level == 'editor'
    
    return True

def can_create_public_content() -> bool:
    """Only non-free users can create public content."""
    return current_user.is_authenticated and current_user.user_role != User.ROLE_FREE
