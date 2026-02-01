from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from mindstack_app.models import User
from .. import blueprint
from ..services.scoring_config_service import ScoringConfigService

@blueprint.route('/', methods=['GET'])
@login_required
def dashboard():
    """
    Scoring Management Dashboard View.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        flash('Permission denied', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    scoring_groups = ScoringConfigService.get_all_configs()

    return render_template('admin/scoring/index.html', groups=scoring_groups, active_page='scoring')
