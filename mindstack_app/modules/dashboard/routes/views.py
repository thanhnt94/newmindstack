from flask_login import login_required, current_user
from mindstack_app.utils.template_helpers import render_dynamic_template
from .. import blueprint
from ..services.dashboard_service import DashboardService

@blueprint.route('/')
@blueprint.route('/dashboard')
@login_required
def dashboard():
    """Trang dashboard tổng quan của người dùng."""
    data = DashboardService.get_dashboard_data(current_user.user_id)
    return render_dynamic_template('modules/dashboard/index.html', **data)
