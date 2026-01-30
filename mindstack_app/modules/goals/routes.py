"""Routes that manage personal learning goals."""

from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import current_user, login_required

from mindstack_app.core.extensions import db
from mindstack_app.models import UserGoal, Goal
from mindstack_app.utils.pagination import get_pagination_data
from mindstack_app.modules.goals.services.goal_kernel_service import GoalKernelService
from . import blueprint
from .constants import GOAL_TYPE_CONFIG, PERIOD_LABELS
from .forms import LearningGoalForm
from .view_helpers import build_goal_progress


@blueprint.route('/goals', methods=['GET', 'POST'])
@login_required
def manage_goals():
    """Allow users to review and create their personalised learning goals."""
    from mindstack_app.models import LearningContainer

    form = LearningGoalForm()
    
    if form.validate_on_submit():
        # Create Goal Template (System Definition) dynamically if needed
        # In a strict system, users pick from templates. Here we allow "custom" goals by ensuring a definition exists.
        goal_code = f"{form.domain.data}_{form.metric.data}"
        title_default = f"Mục tiêu {form.metric.data}"
        
        # Ensure 'Goal' definition exists
        GoalKernelService.create_goal_definition(
            code=goal_code,
            title=title_default, # This title is for the TEMPLATE
            metric=form.metric.data,
            domain=form.domain.data,
            default_period=form.period.data,
            default_target=form.target_value.data,
            icon='star' # Default
        )
        db.session.commit() # Commit definition first

        # Create/Update UserGoal Instance
        ref_id = int(form.reference_id.data) if form.reference_id.data else None
        
        user_goal = GoalKernelService.ensure_user_goal(
            user_id=current_user.user_id,
            goal_code=goal_code,
            target_override=form.target_value.data,
            scope=form.scope.data,
            reference_id=ref_id
        )
        # Check if ensure returned an existing one, update it if customized
        if user_goal:
             user_goal.period = form.period.data
             user_goal.target_value = form.target_value.data
             user_goal.start_date = form.start_date.data
             user_goal.end_date = form.due_date.data
             user_goal.is_active = True
             db.session.add(user_goal)
             
        db.session.commit()
        flash('Đã lưu mục tiêu học tập mới!', 'success')
        return redirect(url_for('goals.manage_goals'))

    goals_query = (
        UserGoal.query.filter(
            UserGoal.user_id == current_user.user_id,
        )
        .order_by(UserGoal.created_at.desc())
    )

    pagination = get_pagination_data(
        goals_query,
        request.args.get('page', type=int, default=1),
        per_page=6,
    )
    
    # [REFACTORED] Pass simplified metrics or none, since view_helpers now uses DB Progres
    # However, existing summary metrics might be used for other UI parts?
    # view_helpers implementation reads directly from DB, so 'metrics' arg is optional/unused now?
    # Checking view_helpers: build_goal_progress(user_goals, metrics=None).
    # It does NOT use metrics anymore.
    
    goal_progress = build_goal_progress(pagination.items)
    
    # Fetch containers for selector (Only those learned/accessed by user)
    from mindstack_app.models import UserContainerState
    
    def get_user_sets(ctype):
        return (
            LearningContainer.query
            .join(UserContainerState, LearningContainer.container_id == UserContainerState.container_id)
            .filter(
                UserContainerState.user_id == current_user.user_id,
                LearningContainer.container_type == ctype
            )
            .order_by(UserContainerState.last_accessed.desc())
            .all()
        )

    flashcard_sets = get_user_sets('FLASHCARD_SET')
    quiz_sets = get_user_sets('QUIZ_SET')

    return render_dynamic_template('pages/goals/manage.html',
        form=form,
        pagination=pagination,
        goal_progress=goal_progress,
        period_labels=PERIOD_LABELS,
        config=GOAL_TYPE_CONFIG,
        flashcard_sets=flashcard_sets,
        quiz_sets=quiz_sets
    )


@blueprint.route('/goals/<int:goal_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_goal(goal_id: int):
    # goal_id here is UserGoal ID
    user_goal = UserGoal.query.filter_by(user_id=current_user.user_id, user_goal_id=goal_id).first_or_404()

    # Need to map UserGoal back to form
    # Form expects: goal_type, period, target_value...
    # Mapping back is tricky if form relies on "Legacy" goal_type.
    # We will just fill common fields.
    
    # Create object with attributes matching form
    form_obj = type('obj', (object,), {
        'goal_type': user_goal.goal_code, # Or definition.metric
        'domain': user_goal.definition.domain,
        'scope': user_goal.scope,
        'metric': user_goal.definition.metric,
        'period': user_goal.period,
        'target_value': user_goal.target_value,
        'title': user_goal.definition.title,
        'description': user_goal.definition.description,
        'start_date': user_goal.start_date,
        'due_date': user_goal.end_date,
        'notes': '', 
        'reference_id': user_goal.reference_id
    })

    form = LearningGoalForm(obj=form_obj)
    # form.goal_type.choices = ... (Legacy)

    if form.validate_on_submit():
        user_goal.period = form.period.data
        user_goal.target_value = form.target_value.data
        user_goal.start_date = form.start_date.data
        user_goal.end_date = form.due_date.data
        # Updating Definition Title? Probably not unique to user.
        # If user changes title, it's problematic if titles are on Goal template.
        # Ignoring title update for now or creating new template?
        # UserGoal doesn't have title field.
        
        db.session.commit()
        flash('Đã cập nhật mục tiêu học tập.', 'success')
        return redirect(url_for('goals.manage_goals'))

    return render_dynamic_template('pages/goals/edit.html',
        form=form,
        goal=user_goal,
        period_labels=PERIOD_LABELS,
        config=GOAL_TYPE_CONFIG,
    )


@blueprint.route('/goals/<int:goal_id>/toggle', methods=['POST'])
@login_required
def toggle_goal(goal_id: int):
    user_goal = UserGoal.query.filter_by(user_id=current_user.user_id, user_goal_id=goal_id).first_or_404()
    user_goal.is_active = not user_goal.is_active
    db.session.commit()
    flash('Đã cập nhật trạng thái mục tiêu.', 'success')
    return redirect(request.referrer or url_for('goals.manage_goals'))


@blueprint.route('/goals/<int:goal_id>/delete', methods=['POST'])
@login_required
def delete_goal(goal_id: int):
    user_goal = UserGoal.query.filter_by(user_id=current_user.user_id, user_goal_id=goal_id).first_or_404()
    db.session.delete(user_goal)
    db.session.commit()
    flash('Đã xóa mục tiêu học tập.', 'success')
    return redirect(request.referrer or url_for('goals.manage_goals'))
