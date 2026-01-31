from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from mindstack_app.models import User
from mindstack_app.services.template_service import TemplateService
from .. import blueprint

@blueprint.route('/templates', methods=['GET'])
@login_required
def manage_templates():
    """
    Page to manage system themes and templates.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        flash('Permission denied', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    # Fetch structured settings compatible with the template
    template_settings = TemplateService.get_all_template_settings()

    return render_template('admin/manage_templates.html', 
                           template_settings=template_settings,
                           active_page='templates')

@blueprint.route('/templates/update', methods=['POST'])
@login_required
def update_template_settings():
    """
    API endpoint to update template settings via JSON.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
    data = request.get_json()
    updates = data.get('updates', {})
    
    if not updates:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    try:
        # Currently the UI sends 'global_system' -> version
        if 'global_system' in updates:
            version = updates['global_system']
            TemplateService.set_active_global_version(version)
            return jsonify({'success': True, 'message': f'Đã kích hoạt giao diện: {version}'})
            
        return jsonify({'success': True, 'message': 'Settings saved (no changes detected).'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'}), 500