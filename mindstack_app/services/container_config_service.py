"""
Container Configuration Service

Handles retrieval of configuration settings for specific LearningContainers.
"""

from typing import Any, Optional
from mindstack_app.models import LearningContainer

class ContainerConfigService:
    """Service for managing container-specific configurations."""

    @staticmethod
    def get_retention(container_id: Optional[int]) -> Optional[float]:
        """
        Get the desired retention for a specific container.
        
        Args:
            container_id: The ID of the container to check.
            
        Returns:
            The desired retention value (0.7 - 0.99) or None if not set.
        """
        if not container_id:
            return None
            
        try:
            container = LearningContainer.query.get(container_id)
            if not container or not container.settings:
                return None
                
            # Expected structure: settings = {"fsrs": {"desired_retention": 0.9}}
            fsrs_settings = container.settings.get('fsrs', {})
            retention = fsrs_settings.get('desired_retention')
            
            if retention is not None:
                try:
                    return float(retention)
                except (ValueError, TypeError):
                    return None
        except Exception:
            # Fallback if DB is not available or query fails
            pass
            
        return None
