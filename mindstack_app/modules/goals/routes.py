"""Routes that manage personal learning goals."""

from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...db_instance import db
from ...models import LearningGoal
from ..shared.utils.pagination import get_pagination_data
from . import goals_bp
from .constants import GOAL_TYPE_CONFIG, PERIOD_LABELS
from .forms import LearningGoalForm
from .services import build_goal_progress, get_learning_activity


@goals_bp.route('/goals', methods=['GET', 'POST'])
@login_required
def manage_goals():
    """Allow users to review and create their personalised learning goals."""

    form = LearningGoalForm()
    form.goal_type.choices = [(key, config['label']) for key, config in GOAL_TYPE_CONFIG.items()]

    if form.validate_on_submit():
        selected_type = form.goal_type.data
        config = GOAL_TYPE_CONFIG.get(selected_type)
        if config is None:
            flash('Loại mục tiêu không hợp lệ.', 'error')
        else:
            goal = LearningGoal(
                user_id=current_user.user_id,
                goal_type=selected_type,
                period=form.period.data,
                target_value=form.target_value.data,
                title=form.title.data.strip() if form.title.data else config['label'],
                description=config['description'],
                start_date=form.start_date.data,
                due_date=form.due_date.data,
                notes=form.notes.data.strip() if form.notes.data else None,
            )
            db.session.add(goal)
            db.session.commit()
            flash('Đã lưu mục tiêu học tập mới!', 'success')
            return redirect(url_for('goals.manage_goals'))

    goals_query = (
        LearningGoal.query.filter(
            LearningGoal.user_id == current_user.user_id,
        )
        .order_by(LearningGoal.created_at.desc())
    )

    pagination = get_pagination_data(
        goals_query,
        request.args.get('page', type=int, default=1),
        per_page=6,
    )
    metrics = get_learning_activity(current_user.user_id)
    goal_progress = build_goal_progress(pagination.items, metrics)

    return render_template(
        'goals/manage.html',
        form=form,
        pagination=pagination,
        goal_progress=goal_progress,
        period_labels=PERIOD_LABELS,
        config=GOAL_TYPE_CONFIG,
    )


@goals_bp.route('/goals/<int:goal_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_goal(goal_id: int):
    goal = LearningGoal.query.filter_by(user_id=current_user.user_id, goal_id=goal_id).first_or_404()

    form = LearningGoalForm(obj=goal)
    form.goal_type.choices = [(key, config['label']) for key, config in GOAL_TYPE_CONFIG.items()]

    if form.validate_on_submit():
        config = GOAL_TYPE_CONFIG.get(form.goal_type.data)
        if config is None:
            flash('Loại mục tiêu không hợp lệ.', 'error')
        else:
            goal.goal_type = form.goal_type.data
            goal.period = form.period.data
            goal.target_value = form.target_value.data
            goal.title = form.title.data.strip() if form.title.data else config['label']
            goal.description = config['description']
            goal.start_date = form.start_date.data
            goal.due_date = form.due_date.data
            goal.notes = form.notes.data.strip() if form.notes.data else None
            db.session.commit()
            flash('Đã cập nhật mục tiêu học tập.', 'success')
            return redirect(url_for('goals.manage_goals'))

    return render_template(
        'goals/edit.html',
        form=form,
        goal=goal,
        period_labels=PERIOD_LABELS,
        config=GOAL_TYPE_CONFIG,
    )


@goals_bp.route('/goals/<int:goal_id>/toggle', methods=['POST'])
@login_required
def toggle_goal(goal_id: int):
    goal = LearningGoal.query.filter_by(user_id=current_user.user_id, goal_id=goal_id).first_or_404()
    goal.is_active = not goal.is_active
    db.session.commit()
    flash('Đã cập nhật trạng thái mục tiêu.', 'success')
    return redirect(request.referrer or url_for('goals.manage_goals'))


@goals_bp.route('/goals/<int:goal_id>/delete', methods=['POST'])
@login_required
def delete_goal(goal_id: int):
    goal = LearningGoal.query.filter_by(user_id=current_user.user_id, goal_id=goal_id).first_or_404()
    db.session.delete(goal)
    db.session.commit()
    flash('Đã xóa mục tiêu học tập.', 'success')
    return redirect(request.referrer or url_for('goals.manage_goals'))
