from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from mindstack_app.modules.learning.logics.marker_logic import toggle_user_marker, get_user_markers_for_items

markers_bp = Blueprint('markers_api', __name__, url_prefix='/api/v3/learning/markers')

@markers_bp.route('/toggle', methods=['POST'])
@login_required
def api_toggle_marker():
    data = request.get_json()
    item_id = data.get('item_id')
    marker_type = data.get('marker_type')
    
    if not item_id or not marker_type:
        return jsonify({'success': False, 'message': 'Missing item_id or marker_type'}), 400
        
    valid_types = ['difficult', 'ignored', 'favorite']
    if marker_type not in valid_types:
         return jsonify({'success': False, 'message': 'Invalid marker type'}), 400

    is_marked = toggle_user_marker(current_user.user_id, item_id, marker_type)
    
    return jsonify({
        'success': True, 
        'item_id': item_id, 
        'marker_type': marker_type, 
        'is_marked': is_marked
    })

@markers_bp.route('/batch', methods=['POST'])
@login_required
def api_get_batch_markers():
    """Get markers for a list of item IDs."""
    data = request.get_json()
    item_ids = data.get('item_ids', [])
    
    if not item_ids:
        return jsonify({'success': True, 'markers': {}})
        
    markers_map = get_user_markers_for_items(current_user.user_id, item_ids)
    return jsonify({'success': True, 'markers': markers_map})
