# File: mindstack_app/modules/fsrs/routes/admin_views.py
from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from mindstack_app.models import User
from .. import fsrs_bp as blueprint
from ..services.settings_service import FSRSSettingsService

@blueprint.route('/', methods=['GET'])
@login_required
def config_page():
    if current_user.user_role != User.ROLE_ADMIN:
        flash('Permission denied', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    current_settings = FSRSSettingsService.get_parameters()
    # We take defaults from Service which has them correctly mapped
    defaults = FSRSSettingsService.DEFAULTS 
    
    return render_template('admin/modules/fsrs/fsrs_config.html', 
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
        FSRSSettingsService.save_parameters(data, user_id=current_user.user_id)
        return jsonify({'success': True, 'message': 'Cấu hình FSRS đã được lưu thành công.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi khi lưu tham số: {str(e)}'}), 500
