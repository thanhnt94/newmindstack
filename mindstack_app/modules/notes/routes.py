from flask import request, jsonify
from flask_login import login_required, current_user
from . import notes_bp
from .orchestrator import NoteOrchestrator
from mindstack_app.utils.template_helpers import render_dynamic_template

@notes_bp.route('/notes/get/<string:reference_type>/<int:reference_id>', methods=['GET'])
@login_required
def get_note(reference_type, reference_id):
    """API: Get note for any entity type."""
    result = NoteOrchestrator.get_note_for_ui(current_user.user_id, reference_type, reference_id)
    return jsonify(result)

@notes_bp.route('/notes/save/<string:reference_type>/<int:reference_id>', methods=['POST'])
@login_required
def save_note(reference_type, reference_id):
    """API: Save/Update note for any entity type."""
    data = request.get_json()
    content = data.get('content', '')
    title = data.get('title')
    
    result = NoteOrchestrator.save_note(current_user.user_id, reference_type, reference_id, content, title=title)
    return jsonify(result)

@notes_bp.route('/notes')
@login_required
def manage_notes():
    """HTML: Render notes management page."""
    notes_data = NoteOrchestrator.get_manage_notes_data(current_user.user_id)
    return render_dynamic_template('pages/notes/manage_notes.html', notes_data=notes_data)

# Compatibility routes for old 'item' only calls
@notes_bp.route('/notes/get/<int:item_id>', methods=['GET'])
@login_required
def get_note_legacy(item_id):
    return get_note('item', item_id)

@notes_bp.route('/notes/save/<int:item_id>', methods=['POST'])
@login_required
def save_note_legacy(item_id):
    return save_note('item', item_id)
