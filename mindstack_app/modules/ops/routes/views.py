from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from mindstack_app.models import User
from .. import blueprint

@blueprint.route('/reset', methods=['GET'])
@login_required
def reset_page():
    """
    Trang quản lý đặt lại hệ thống (System Reset).
    """
    if current_user.user_role != User.ROLE_ADMIN:
        flash('Permission denied', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    return render_template('admin/ops/reset.html', active_page='ops_reset')
