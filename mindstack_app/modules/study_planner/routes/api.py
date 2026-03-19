"""
Study Planner API Routes
=========================
JSON API endpoints for creating, managing, and querying study plans.
"""

from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import date, datetime

from .. import study_planner_bp as blueprint
from ..services.planner_service import PlannerService


@blueprint.route('/api/create', methods=['POST'])
@login_required
def create_plan_api():
    """Create a new study plan."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ.'}), 400

    container_id = data.get('container_id')
    target_end_date_str = data.get('target_end_date')
    title = data.get('title')

    if not container_id or not target_end_date_str:
        return jsonify({'success': False, 'message': 'Thiếu container_id hoặc target_end_date.'}), 400

    try:
        target_end_date = date.fromisoformat(target_end_date_str)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Định dạng ngày không hợp lệ (YYYY-MM-DD).'}), 400

    try:
        plan = PlannerService.create_plan(
            user_id=current_user.user_id,
            container_id=int(container_id),
            target_end_date=target_end_date,
            title=title
        )
        return jsonify({
            'success': True,
            'message': 'Đã tạo kế hoạch học tập thành công!',
            'plan': plan.to_dict()
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"[PLANNER API] Error creating plan: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Lỗi hệ thống khi tạo kế hoạch.'}), 500


@blueprint.route('/api/status/<int:container_id>', methods=['GET'])
@login_required
def get_plan_status_api(container_id):
    """Get today's plan status for a container."""
    try:
        status = PlannerService.get_today_status(current_user.user_id, container_id)
        if not status:
            return jsonify({'success': True, 'has_plan': False})
        return jsonify({'success': True, 'has_plan': True, 'data': status})
    except Exception as e:
        current_app.logger.error(f"[PLANNER API] Error getting status: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Lỗi hệ thống.'}), 500


@blueprint.route('/api/update/<int:plan_id>', methods=['PUT'])
@login_required
def update_plan_api(plan_id):
    """Update the target end date of a plan."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ.'}), 400

    new_end_date_str = data.get('target_end_date')
    if not new_end_date_str:
        return jsonify({'success': False, 'message': 'Thiếu target_end_date.'}), 400

    try:
        new_end_date = date.fromisoformat(new_end_date_str)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Định dạng ngày không hợp lệ.'}), 400

    try:
        # Verify ownership
        plan = PlannerService.get_plan_by_id(plan_id)
        if not plan or plan.user_id != current_user.user_id:
            return jsonify({'success': False, 'message': 'Kế hoạch không tồn tại.'}), 404

        updated_plan = PlannerService.update_target_date(plan_id, new_end_date)
        return jsonify({
            'success': True,
            'message': 'Đã cập nhật ngày mục tiêu!',
            'plan': updated_plan.to_dict()
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"[PLANNER API] Error updating plan: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Lỗi hệ thống.'}), 500


@blueprint.route('/api/cancel/<int:plan_id>', methods=['DELETE'])
@login_required
def cancel_plan_api(plan_id):
    """Cancel an active plan."""
    try:
        plan = PlannerService.get_plan_by_id(plan_id)
        if not plan or plan.user_id != current_user.user_id:
            return jsonify({'success': False, 'message': 'Kế hoạch không tồn tại.'}), 404

        cancelled_plan = PlannerService.cancel_plan(plan_id)
        return jsonify({
            'success': True,
            'message': 'Đã hủy kế hoạch học tập.',
            'plan': cancelled_plan.to_dict()
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"[PLANNER API] Error cancelling plan: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Lỗi hệ thống.'}), 500


@blueprint.route('/api/history/<int:plan_id>', methods=['GET'])
@login_required
def get_plan_history_api(plan_id):
    """Get daily log history for a plan."""
    try:
        plan = PlannerService.get_plan_by_id(plan_id)
        if not plan or plan.user_id != current_user.user_id:
            return jsonify({'success': False, 'message': 'Kế hoạch không tồn tại.'}), 404

        logs = PlannerService.get_plan_history(plan_id)
        return jsonify({
            'success': True,
            'plan': plan.to_dict(),
            'logs': logs
        })
    except Exception as e:
        current_app.logger.error(f"[PLANNER API] Error getting history: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Lỗi hệ thống.'}), 500
