from flask import request, jsonify
from flask_login import login_required, current_user
from .. import blueprint
from ..services.note_manager import NoteManager

@blueprint.route('/notes/get/<string:reference_type>/<int:reference_id>', methods=['GET'])
@login_required
def get_note(reference_type, reference_id):
    """API: Get note for any entity type."""
    result = NoteManager.get_note_for_ui(current_user.user_id, reference_type, reference_id)
    return jsonify(result)

@blueprint.route('/notes/save/<string:reference_type>/<int:reference_id>', methods=['POST'])
@login_required
def save_note(reference_type, reference_id):
    """API: Save/Update note for any entity type."""
    data = request.get_json()
    content = data.get('content', '')
    title = data.get('title')
    
    result = NoteManager.save_note(current_user.user_id, reference_type, reference_id, content, title=title)
    return jsonify(result)

@blueprint.route('/notes/get/<int:item_id>', methods=['GET'])
@login_required
def get_note_legacy(item_id):
    return get_note('item', item_id)

@blueprint.route('/notes/save/<int:item_id>', methods=['POST'])
@login_required
def save_note_legacy(item_id):
    return save_note('item', item_id)
