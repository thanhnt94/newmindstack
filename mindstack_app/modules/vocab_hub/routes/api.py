# mindstack_app/modules/vocab_hub/routes/api.py
from flask import jsonify, request
from flask_login import login_required, current_user
from ..services.hub_service import HubService
from .. import vocab_hub_bp

@vocab_hub_bp.route('/api/item/<int:item_id>/insight')
@login_required
def get_item_insight(item_id):
    """API endpoint to get item insights."""
    insight = HubService.get_item_insight(current_user.user_id, item_id)
    return jsonify(success=True, data=insight)
