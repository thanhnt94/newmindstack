# mindstack_app/modules/learning/course_learning/routes.py
# Phiên bản: 2.5
# MỤC ĐÍCH: Lấy dữ liệu ghi chú của người dùng cho bài học hiện tại.
# ĐÃ THÊM: Truy vấn model UserNote và truyền đối tượng 'note' ra template.

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from .algorithms import get_filtered_course_sets, get_lessons_for_course
from ....models import db, LearningContainer, LearningItem, CourseProgress, UserContainerState, ContainerContributor, UserNote
from sqlalchemy.sql import func

course_learning_bp = Blueprint('course_learning', __name__, template_folder='templates')


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

    if progress:
        progress.completion_percentage = int(percentage)
    else:
        progress = CourseProgress(
            user_id=current_user.user_id,
            item_id=lesson_id,
            completion_percentage=int(percentage)
        )
        db.session.add(progress)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Đã cập nhật tiến độ.'})

@course_learning_bp.route('/toggle_archive_course/<int:course_id>', methods=['POST'])
@login_required
def toggle_archive_course(course_id):
    """
    Mô tả: API endpoint để lưu trữ hoặc bỏ lưu trữ một khoá học.
    """
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

