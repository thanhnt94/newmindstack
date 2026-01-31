from flask import render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from mindstack_app.models import User, AppSettings
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

    active_version = TemplateService.get_active_version()
    available_versions = TemplateService.get_available_versions()

    return render_template('admin/manage_templates.html', 
                           active_version=active_version, 
                           versions=available_versions,
                           active_page='templates')

@blueprint.route('/templates/activate', methods=['POST'])
@login_required
def activate_template():
    """
    Activate a specific template version.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        return redirect(url_for('admin.admin_dashboard'))
        
    version = request.form.get('version')
    if version:
        try:
            TemplateService.set_active_version(version)
            flash(f'Activated template version: {version}', 'success')
        except Exception as e:
            flash(f'Error activating template: {e}', 'danger')
            
    return redirect(url_for('admin.manage_templates'))
