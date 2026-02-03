# File: mindstack_app/modules/session/routes/admin.py
from flask import render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from mindstack_app.models import LearningSession, User, db
from ..services.session_service import LearningSessionService
from .. import blueprint

def admin_required(f):
    """Decorator to require admin role."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_role != User.ROLE_ADMIN:
            flash('Báo cáo: Bạn không có quyền truy cập trang này.', 'danger')
            return redirect(url_for('core.dashboard')) # Fallback to main dashboard
        return f(*args, **kwargs)
    return decorated_function

@blueprint.route('/admin/manage')
@login_required
@admin_required
def admin_manage_sessions():
    """Admin dashboard to view all active sessions across the platform."""
    # Fetch all active sessions
    active_sessions = LearningSession.query.filter_by(status='active').order_by(LearningSession.start_time.desc()).all()
    
    return render_template('admin/modules/session/admin_manage.html', sessions=active_sessions)

@blueprint.route('/api/admin/clear-session/<int:session_id>', methods=['POST'])
@login_required
@admin_required
def api_clear_session(session_id):
    """API for admins to force-clear a session."""
    success = LearningSessionService.cancel_session(session_id)
    if success:
        return jsonify({'success': True, 'message': f'Phiên học {session_id} đã được đóng thành công.'})
    else:
        return jsonify({'success': False, 'message': f'Không thể đóng phiên học {session_id}.'})
