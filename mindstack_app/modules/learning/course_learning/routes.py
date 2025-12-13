# mindstack_app/modules/learning/course_learning/routes.py
# Phiên bản: 2.5
# MỤC ĐÍCH: Lấy dữ liệu ghi chú của người dùng cho bài học hiện tại.
# ĐÃ THÊM: Truy vấn model UserNote và truyền đối tượng 'note' ra template.

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy.sql import func

from .algorithms import get_filtered_course_sets, get_lessons_for_course
from ....models import (
    ContainerContributor,
    CourseProgress,
    LearningContainer,
    LearningItem,
    ScoreLog,
    User,
    UserContainerState,
    UserNote,
    db,
)
from mindstack_app.services.config_service import get_runtime_config
from mindstack_app.modules.gamification.services import ScoreService

course_learning_bp = Blueprint('course_learning', __name__, template_folder='templates')


def _get_score_value(key: str, default: int) -> int:
    """Fetch an integer score value from runtime config with fallback."""

    raw_value = get_runtime_config(key, default)
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default


@course_learning_bp.route('/course_learning_dashboard')
@login_required
def course_learning_dashboard():
    """
    Mô tả: Hiển thị trang dashboard chính cho việc học Course.
    """
    current_filter = request.args.get('filter', 'doing', type=str)
    return render_template('course_learning_dashboard.html', current_filter=current_filter)

@course_learning_bp.route('/get_course_sets_partial')
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
    
    return render_template('_course_sets_selection.html',
                           courses=pagination.items,
                           pagination=pagination,
                           search_query=search_query,
                           search_field=search_field,
                           current_filter=current_filter)

@course_learning_bp.route('/get_lesson_list_partial/<int:course_id>')
@login_required
def get_lesson_list_partial(course_id):
    """
    Mô tả: API endpoint để lấy danh sách bài học của một khoá học.
    """
    course = LearningContainer.query.get_or_404(course_id)
    if current_user.user_role == User.ROLE_FREE and course.creator_user_id != current_user.user_id:
        abort(403)
    lessons = get_lessons_for_course(current_user.user_id, course_id)
    
    return render_template('_lesson_selection.html', lessons=lessons, course=course)

@course_learning_bp.route('/course_session/<int:lesson_id>')
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
    
    progress = CourseProgress.query.filter_by(
        user_id=current_user.user_id,
        item_id=lesson_id
    ).first()
    
    current_percentage = progress.completion_percentage if progress else 0

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
    note = UserNote.query.filter_by(user_id=current_user.user_id, item_id=lesson.item_id).first()

    return render_template(
        'course_session.html', 
        lesson=lesson, 
        course=course, 
        current_percentage=current_percentage,
        can_edit=can_edit,
        note=note  # Truyền đối tượng ghi chú ra template
    )


@course_learning_bp.route('/update_lesson_progress/<int:lesson_id>', methods=['POST'])
@login_required
def update_lesson_progress(lesson_id):
    """
    Mô tả: API endpoint để cập nhật tiến độ hoàn thành của một bài học.
    """
    data = request.get_json()
    percentage = data.get('percentage')

    if percentage is None or not (0 <= int(percentage) <= 100):
        return jsonify({'success': False, 'message': 'Giá trị phần trăm không hợp lệ.'}), 400

    lesson = LearningItem.query.get_or_404(lesson_id)
    container = LearningContainer.query.get_or_404(lesson.container_id)

    if current_user.user_role == User.ROLE_FREE and container.creator_user_id != current_user.user_id:
        return jsonify({'success': False, 'message': 'Bạn không có quyền cập nhật khóa học này.'}), 403
    # Cập nhật last_accessed cho UserContainerState khi có tương tác
    user_container_state = UserContainerState.query.filter_by(
        user_id=current_user.user_id,
        container_id=lesson.container_id
    ).first()
    if not user_container_state:
        user_container_state = UserContainerState(user_id=current_user.user_id, container_id=lesson.container_id)
        db.session.add(user_container_state)
    user_container_state.last_accessed = func.now()

    progress = CourseProgress.query.filter_by(
        user_id=current_user.user_id,
        item_id=lesson_id
    ).first()

    previous_percentage = progress.completion_percentage if progress else 0

    if progress:
        progress.completion_percentage = int(percentage)
    else:
        progress = CourseProgress(
            user_id=current_user.user_id,
            item_id=lesson_id,
            completion_percentage=int(percentage)
        )
        db.session.add(progress)

    lesson_completed = previous_percentage < 100 and progress.completion_percentage >= 100

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
            completed_count = CourseProgress.query.filter(
                CourseProgress.user_id == current_user.user_id,
                CourseProgress.item_id.in_(lesson_ids),
                CourseProgress.completion_percentage >= 100,
            ).count()

            if completed_count == len(lesson_ids):
                already_logged = ScoreLog.query.filter_by(
                    user_id=current_user.user_id,
                    item_id=container.container_id,
                    item_type='COURSE',
                ).first()

                if not already_logged:
                    course_score = _get_score_value('COURSE_COMPLETION_SCORE', 50)
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

@course_learning_bp.route('/toggle_archive_course/<int:course_id>', methods=['POST'])
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

