from flask_login import login_required, current_user
from .. import blueprint
from ..services.note_manager import NoteManager
from mindstack_app.utils.template_helpers import render_dynamic_template

@blueprint.route('/notes')
@login_required
def manage_notes():
    """HTML: Render notes management page."""
    notes_data = NoteManager.get_manage_notes_data(current_user.user_id)
    return render_dynamic_template('modules/notes/manage_notes.html', notes_data=notes_data)
