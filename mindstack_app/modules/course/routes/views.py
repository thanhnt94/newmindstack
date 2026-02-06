# mindstack_app/modules/learning/course/routes.py
# Phiên bản: 2.6
# MỤC ĐÍCH: Refactor to use ItemMemoryState (FSRS) instead of LearningProgress.

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, abort
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from sqlalchemy.sql import func

from ..logics.algorithms import get_filtered_course_sets, get_lessons_for_course
from mindstack_app.models import (
    ContainerContributor,
    LearningContainer,
    LearningItem,
    ScoreLog,
    User,
    UserContainerState,
    Note,
    db,
)
from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsInterface

from .. import blueprint

@blueprint.route('/course_learning_dashboard')
@login_required
def course_learning_dashboard():
    """
    Mô tả: Hiển thị trang dashboard chính cho việc học Course.
    """
    current_filter = request.args.get('filter', 'doing', type=str)
    return render_dynamic_template('modules/learning/course/course_learning_dashboard.html', current_filter=current_filter)

@blueprint.route('/get_course_sets_partial')
@login_required
def get_course_sets_partial():
    """
    Mô tả: API endpoint để lấy danh sách các khoá học dưới dạng HTML partial.
    """
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)

    pagination = get_filtered_course_sets(
        user_id=current_user.user_id,
        search_query=search_query,
        search_field=search_field,
        current_filter=current_filter,
        page=page
    )
    
    return render_dynamic_template('modules/learning/course/_course_sets_selection.html',
                           courses=pagination.items,
                           pagination=pagination,
                           search_query=search_query,
                           search_field=search_field,
                           current_filter=current_filter)

@blueprint.route('/get_lesson_list_partial/<int:course_id>')
@login_required
def get_lesson_list_partial(course_id):
    """
    Mô tả: API endpoint để lấy danh sách bài học của một khoá học.
    """
    course = LearningContainer.query.get_or_404(course_id)
    if current_user.user_role == User.ROLE_FREE and course.creator_user_id != current_user.user_id:
        abort(403)
    lessons = get_lessons_for_course(current_user.user_id, course_id)
    
    return render_dynamic_template('modules/learning/course/_lesson_selection.html', lessons=lessons, course=course)

@blueprint.route('/course_session/<int:lesson_id>')
@login_required
def course_session(lesson_id):
    """
    Mô tả: Hiển thị trang nội dung của một bài học cụ thể.
    """
    lesson = LearningItem.query.get_or_404(lesson_id)
    if lesson.item_type != 'LESSON':
        flash('Học liệu không phải là một bài học.', 'danger')
        return redirect(url_for('.course_learning_dashboard'))

    course = LearningContainer.query.get_or_404(lesson.container_id)
    if current_user.user_role == User.ROLE_FREE and course.creator_user_id != current_user.user_id:
        flash('Bạn không có quyền truy cập khóa học này.', 'danger')
        return redirect(url_for('.course_learning_dashboard'))
    
    # Get ItemMemoryState
    progress = FsrsInterface.get_item_state(current_user.user_id, lesson_id)
    
    data = progress.data or {} if progress else {}
    current_percentage = data.get('completion_percentage', 0)

    can_edit = (
        current_user.user_role == 'admin' or
        course.creator_user_id == current_user.user_id or
        ContainerContributor.query.filter_by(
            container_id=course.container_id,
            user_id=current_user.user_id,
            permission_level='editor'
        ).first() is not None
    )
    
    # THÊM MỚI: Lấy ghi chú của người dùng cho bài học này
    note = Note.query.filter_by(user_id=current_user.user_id, reference_type='item', reference_id=lesson.item_id).first()

    return render_dynamic_template('modules/learning/course/course_session.html', 
        lesson=lesson, 
        course=course, 
        current_percentage=current_percentage,
        can_edit=can_edit,
        note=note  # Truyền đối tượng ghi chú ra template
    )


@blueprint.route('/update_lesson_progress/<int:lesson_id>', methods=['POST'])
@login_required
def update_lesson_progress(lesson_id):
    """
    Mô tả: API endpoint để cập nhật tiến độ hoàn thành của một bài học.
    """
    data_in = request.get_json()
    percentage = data_in.get('percentage')

    if percentage is None or not (0 <= int(percentage) <= 100):
        return jsonify({'success': False, 'message': 'Giá trị phần trăm không hợp lệ.'}), 400

    lesson = LearningItem.query.get_or_404(lesson_id)
    container = LearningContainer.query.get_or_404(lesson.container_id)

    if current_user.user_role == User.ROLE_FREE and container.creator_user_id != current_user.user_id:
        return jsonify({'success': False, 'message': 'Bạn không có quyền cập nhật khóa học này.'}), 403
    
    # Cập nhật last_accessed cho UserContainerState
    user_container_state = UserContainerState.query.filter_by(
        user_id=current_user.user_id,
        container_id=lesson.container_id
    ).first()
    if not user_container_state:
        user_container_state = UserContainerState(user_id=current_user.user_id, container_id=lesson.container_id)
        db.session.add(user_container_state)
    user_container_state.last_accessed = func.now()

    # Get ItemMemoryState
    progress = FsrsInterface.get_item_state(current_user.user_id, lesson_id)
    previous_percentage = (progress.data or {}).get('completion_percentage', 0) if progress else 0

    # Update ItemMemoryState via Interface
    progress = FsrsInterface.save_lesson_progress(current_user.user_id, lesson_id, int(percentage))

    completion_pct = progress.data.get('completion_percentage', 0) if progress.data else 0
    lesson_completed = previous_percentage < 100 and completion_pct >= 100

    # REFAC: Removed legacy quiz_logic import
    # Helper is local in quiz_logic.py. I should use config service directly or reimplement helper.
    # Reimplementing helper for safety
    def _get_score_value_local(key, default):
        from mindstack_app.services.config_service import get_runtime_config
        try: return int(get_runtime_config(key, default))
        except: return default

    lesson_score = _get_score_value_local('LESSON_COMPLETION_SCORE', 10)

    if lesson_completed:
        if lesson_score:
            ScoreService.award_points(
                user_id=current_user.user_id,
                amount=lesson_score,
                reason='Lesson Completed',
                item_id=lesson.item_id,
                item_type='LESSON',
            )

        lesson_ids = [
            item.item_id
            for item in LearningItem.query.filter_by(container_id=container.container_id, item_type='LESSON').all()
        ]

        if lesson_ids:
            # Check completion using FsrsInterface (already implemented similar logic in get_course_container_stats)
            # But here we need specific IDs count. 
            # We can use a custom query helper or just delegate to Interface.
            # For now, let's stick to the Interface principle.
            # I'll use get_batch_memory_states and count locally or add a new method.
            # Actually, get_batch_memory_states is fine.
            states_map = FsrsInterface.get_batch_memory_states(current_user.user_id, lesson_ids)
            completed_count = sum(1 for p in states_map.values() if (p.data or {}).get('completion_percentage', 0) >= 100)

            if completed_count == len(lesson_ids):
                already_logged = ScoreLog.query.filter_by(
                    user_id=current_user.user_id,
                    item_id=container.container_id,
                    item_type='COURSE',
                ).first()

                if not already_logged:
                    course_score = _get_score_value_local('COURSE_COMPLETION_SCORE', 50)
                    if course_score:
                        ScoreService.award_points(
                            user_id=current_user.user_id,
                            amount=course_score,
                            reason='Course Completed',
                            item_id=container.container_id,
                            item_type='COURSE'
                        )

    db.session.commit()

    return jsonify({'success': True, 'message': 'Đã cập nhật tiến độ.'})

@blueprint.route('/toggle_archive_course/<int:course_id>', methods=['POST'])
@login_required
def toggle_archive_course(course_id):
    """
    Mô tả: API endpoint để lưu trữ hoặc bỏ lưu trữ một khoá học.
    """
    course = LearningContainer.query.get_or_404(course_id)
    if current_user.user_role == User.ROLE_FREE and course.creator_user_id != current_user.user_id:
        return jsonify({'success': False, 'message': 'Bạn không có quyền cập nhật khóa học này.'}), 403

    state = UserContainerState.query.filter_by(
        user_id=current_user.user_id,
        container_id=course_id
    ).first()

    if state:
        state.is_archived = not state.is_archived
    else:
        state = UserContainerState(
            user_id=current_user.user_id,
            container_id=course_id,
            is_archived=True
        )
        db.session.add(state)
    
    db.session.commit()
    
    message = "Đã lưu trữ khóa học." if state.is_archived else "Đã bỏ lưu trữ khóa học."
    return jsonify({'success': True, 'message': message, 'is_archived': state.is_archived})