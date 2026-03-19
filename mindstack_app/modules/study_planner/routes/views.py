"""
Study Planner HTML View Routes
================================
Renders HTML pages for plan management.
"""

from flask import render_template
from flask_login import login_required, current_user
from mindstack_app.utils.template_helpers import render_dynamic_template

from .. import study_planner_bp as blueprint
from ..services.planner_service import PlannerService


@blueprint.route('/manage/<int:container_id>')
@login_required
def manage_plan(container_id):
    """Plan management page for a specific container."""
    plan = PlannerService.get_active_plan(current_user.user_id, container_id)
    status = None
    history = []

    if plan:
        status = PlannerService.get_today_status(current_user.user_id, container_id)
        history = PlannerService.get_plan_history(plan.plan_id)

    from mindstack_app.models import LearningContainer
    container = LearningContainer.query.get_or_404(container_id)

    return render_dynamic_template(
        'modules/study_planner/manage.html',
        container=container,
        plan=plan,
        status=status,
        history=history
    )
