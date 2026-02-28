# mindstack_app/modules/vocab_hub/interface.py
from .services.hub_service import HubService

class VocabHubInterface:
    """Public interface for other modules to interact with Vocab Hub."""
    
    @staticmethod
    def get_item_insight(user_id, item_id):
        """Get aggregated insights for a vocabulary item."""
        return HubService.get_item_insight(user_id, item_id)
