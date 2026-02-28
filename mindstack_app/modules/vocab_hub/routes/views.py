from flask import render_template, request, abort
from flask_login import login_required, current_user
from mindstack_app.utils.template_helpers import render_dynamic_template
from ..services.hub_service import HubService
from .. import vocab_hub_bp
from mindstack_app.modules.learning.interface import LearningInterface

@vocab_hub_bp.route('/')
@login_required
def hub_index():
    """Universal Vocabulary Hub Index."""
    data = HubService.get_global_hub_data(current_user.user_id)
    score_data = LearningInterface.get_score_breakdown(current_user.user_id)
    
    return render_dynamic_template('modules/vocab_hub/index.html', 
                                  hub_data=data,
                                  score_overview=score_data)

@vocab_hub_bp.route('/item/<int:item_id>')
@login_required
def item_hub_page(item_id):
    """Full page view for vocabulary item insights."""
    insight = HubService.get_item_insight(current_user.user_id, item_id)
    if not insight:
        abort(404, description="Item insights not found")
        
    # Note: We now use the dedicated hub template in the theme
    return render_dynamic_template('modules/vocab_hub/item_detail.html', 
                                  stats=insight, 
                                  item_id=item_id)
