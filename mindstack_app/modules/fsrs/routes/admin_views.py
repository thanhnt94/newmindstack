from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from mindstack_app.models import User
from .. import blueprint
from ..services.settings_service import FSRSSettingsService

@blueprint.route('/', methods=['GET'])
@login_required
def config_page():
    """
    Page to configure FSRS parameters.
    Mapped to /admin/fsrs/
    """
    if current_user.user_role != User.ROLE_ADMIN:
        flash('Permission denied', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    current_settings = FSRSSettingsService.get_parameters()
    defaults = FSRSSettingsService.get_defaults()
    
    # We reuse the existing admin template for now, or move it?
    # Let's use the existing one but pointing to new routes?
    # Actually, the template uses url_for('admin.save_fsrs_config') which is old.
    # We need to update the template or pass the save URL dynamically.
    
    return render_template('admin/fsrs_config.html', 
                           settings=current_settings,
                           defaults=defaults,
                           active_page='fsrs_config')

@blueprint.route('/save', methods=['POST'])
@login_required
def save_config():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
        
    try:
        FSRSSettingsService.save_parameters(data)
        return jsonify({'success': True, 'message': 'FSRS parameters saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error saving parameters: {str(e)}'}), 500
