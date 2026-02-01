from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from mindstack_app.models import User, AppSettings, db
from ..config import MaintenanceDefaultConfig
from .. import blueprint

@blueprint.route('/', methods=['GET'])
@login_required
def admin_dashboard():
    """
    Dedicated admin page to toggle maintenance mode.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        flash('Permission denied', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    settings = {
        'MAINTENANCE_MODE': AppSettings.get('MAINTENANCE_MODE', MaintenanceDefaultConfig.MAINTENANCE_MODE),
        'MAINTENANCE_END_TIME': AppSettings.get('MAINTENANCE_END_TIME', MaintenanceDefaultConfig.MAINTENANCE_END_TIME),
        'MAINTENANCE_MESSAGE': AppSettings.get('MAINTENANCE_MESSAGE', MaintenanceDefaultConfig.MAINTENANCE_MESSAGE),
    }

    return render_template('admin/maintenance/index.html', settings=settings, active_page='maintenance')

@blueprint.route('/update', methods=['POST'])
@login_required
def update_settings():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    mode = request.form.get('MAINTENANCE_MODE') == 'on'
    end_time = request.form.get('MAINTENANCE_END_TIME', '')
    message = request.form.get('MAINTENANCE_MESSAGE', '')

    try:
        AppSettings.set('MAINTENANCE_MODE', mode, category='system', data_type='bool')
        AppSettings.set('MAINTENANCE_END_TIME', end_time, category='system')
        AppSettings.set('MAINTENANCE_MESSAGE', message, category='system')
        db.session.commit()
        
        status_text = "Đã BẬT chế độ bảo trì." if mode else "Đã TẮT chế độ bảo trì."
        flash(status_text, 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi cập nhật: {str(e)}', 'danger')

    return redirect(url_for('.admin_dashboard'))
