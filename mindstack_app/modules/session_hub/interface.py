# mindstack_app/modules/session_hub/interface.py
from .services.hub_service import SessionHubService


class SessionHubInterface:
    """Public interface for other modules to interact with Session Hub."""

    @staticmethod
    def get_summary(user_id, session_id, page=1):
        """Get aggregated session summary data."""
        return SessionHubService.get_summary_data(user_id, session_id, page=page)
