from flask import render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from mindstack_app.models import User, AppSettings
from ..logics.policies import ROLE_POLICIES, ROLE_FREE, ROLE_USER, ROLE_ADMIN, PolicyValues

from . import blueprint

@blueprint.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    """
    Admin Dashboard for Access Control.
    View Permissions Matrix and Edit Quotas.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        flash("Bạn không có quyền truy cập trang này.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        # Handle Quota Updates
        try:
            for key, value in request.form.items():
                if key.startswith('QUOTA_'):
                    AppSettings.set(key, value)
            
            flash("Cập nhật cấu hình thành công!", "success")
        except Exception as e:
            current_app.logger.error(f"Error updating quotas: {e}")
            flash(f"Lỗi khi cập nhật: {e}", "danger")
            
        return redirect(url_for('access_control.admin_dashboard'))

    # Prepare data for rendering
    # Flatten structure for easy rendering in template
    # Structure: {role: {permissions: {...}, limits: {key: {default: x, current: y}}}}
    
    matrix = {}
    
    # We only care about configurable roles
    configurable_roles = [ROLE_FREE, ROLE_USER] 
    
    for role in configurable_roles:
        policy = ROLE_POLICIES.get(role, {})
        limits = policy.get('limits', {})
        
        limit_data = {}
        for limit_key, default_val in limits.items():
            setting_key = f"QUOTA_{limit_key}_{role}".upper()
            current_val = AppSettings.get(setting_key)
            
            limit_data[limit_key] = {
                'setting_key': setting_key,
                'default': default_val,
                'current': current_val if current_val is not None else default_val
            }
            
        matrix[role] = {
            'permissions': policy.get('permissions', {}),
            'limits': limit_data
        }
        
    return render_template(
        'admin/modules/access_control/index.html',
        matrix=matrix,
        PolicyValues=PolicyValues,
        page_title="Quản lý Phân quyền & Giới hạn"
    )
