# File: newmindstack/mindstack_app/modules/content_management/courses/routes.py
# Phiên bản: 6.6 (Đã tích hợp tiện ích phân trang và tìm kiếm từ utils)
# Mục đích: Xử lý các route liên quan đến quản lý khóa học (LearningContainer loại 'COURSE')
#           Bao gồm tạo, xem, chỉnh sửa, xóa khóa học và các bài học (LearningItem loại 'LESSON')
#           Đã tích hợp logic phân quyền mới (creator, admin, contributor).
#           Đã sửa đường dẫn import models.
#           Đã cập nhật tất cả các url_for theo cấu trúc Blueprint lồng nhau.
#           Đã giữ nguyên logic xử lý AI settings và BBCode content từ code gốc.
#           Đã kiểm tra lại để khắc phục lỗi HTTP 500.
#           ĐÃ SỬA: Chuyển hướng sau khi thêm/sửa/xóa về content_dashboard và chọn tab đúng.
#           ĐÃ SỬA: Điều chỉnh để trả về JSON cho các yêu cầu AJAX khi thêm/sửa/xóa bộ.
#           ĐÃ SỬA: Render template bare form cho yêu cầu GET từ modal, full form cho non-modal GET.
#           ĐÃ TÍCH HỢP: Phân trang và tìm kiếm sử dụng các hàm từ utils.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from ..forms import CourseForm, LessonForm
from ....models import db, LearningContainer, LearningItem, User, SystemSetting, ContainerContributor
from ....utils.pagination import get_pagination_data # THÊM: Import hàm phân trang
from ....utils.search import apply_search_filter # THÊM: Import hàm tìm kiếm

# Định nghĩa Blueprint cho quản lý khóa học
courses_bp = Blueprint('content_management_courses', __name__,
                        template_folder='../templates/courses')

# Middleware để đảm bảo người dùng đã đăng nhập cho toàn bộ Blueprint courses
@courses_bp.before_request
@login_required 
def course_management_required():
    """
    Middleware để đảm bảo người dùng đã đăng nhập trước khi truy cập các route trong Blueprint này.
    """
    pass

# --- ROUTES QUẢN LÝ KHÓA HỌC (LearningContainer) ---

@courses_bp.route('/')
@courses_bp.route('/sets')
def list_courses():
    """
    Hiển thị danh sách các khóa học mà người dùng hiện tại có quyền truy cập,
    có hỗ trợ phân trang và tìm kiếm.
    Admin có thể thấy tất cả các khóa học.
    Người dùng thông thường chỉ thấy khóa học do mình tạo hoặc được cấp quyền chỉnh sửa.
    Nếu yêu cầu là AJAX, chỉ trả về phần danh sách khóa học.
    """
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)

    base_query = LearningContainer.query.filter_by(container_type='COURSE')

    if current_user.user_role != 'admin':
        user_id = current_user.user_id
        created_courses_query = base_query.filter_by(creator_user_id=user_id)
        contributed_courses_query = base_query.join(ContainerContributor).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor'
        )
        base_query = created_courses_query.union(contributed_courses_query)

    # Áp dụng tìm kiếm
    search_fields = [LearningContainer.title, LearningContainer.description, LearningContainer.tags]
    base_query = apply_search_filter(base_query, search_query, search_fields)

    # Phân trang
    pagination = get_pagination_data(base_query.order_by(LearningContainer.created_at.desc()), page)
    courses = pagination.items

    # Đếm số lượng item cho mỗi khóa học
    for course_item in courses:
        course_item.item_count = db.session.query(LearningItem).filter_by(
            container_id=course_item.container_id,
            item_type='LESSON'
        ).count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_courses_list.html', courses=courses, pagination=pagination, search_query=search_query)
    else:
        return render_template('courses.html', courses=courses, pagination=pagination, search_query=search_query)

@courses_bp.route('/sets/add', methods=['GET', 'POST'])
def add_course():
    """
    Thêm một khóa học mới.
    Chỉ người dùng đã đăng nhập mới có thể thêm khóa học.
    Người tạo khóa học sẽ tự động là creator_user_id.
    """
    form = CourseForm()
    if form.validate_on_submit():
        ai_settings = {}
        if form.ai_prompt.data:
            ai_settings['custom_prompt'] = form.ai_prompt.data

        new_course = LearningContainer(
            creator_user_id=current_user.user_id,
            container_type='COURSE',
            title=form.title.data,
            description=form.description.data,
            tags=form.tags.data,
            is_public=form.is_public.data,
            ai_settings=ai_settings if ai_settings else None
        )
        db.session.add(new_course)
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Khóa học đã được thêm thành công!'})
        else:
            flash('Khóa học đã được thêm thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='courses'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400
    
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_course_set_bare.html', form=form, title='Thêm Khóa học mới')
    return render_template('add_edit_course_set.html', form=form, title='Thêm Khóa học mới')

@courses_bp.route('/sets/edit/<int:set_id>', methods=['GET', 'POST'])
def edit_course(set_id):
    """
    Chỉnh sửa thông tin khóa học.
    Chỉ creator_user_id, admin hoặc người dùng được cấp quyền 'editor' mới có thể chỉnh sửa.
    """
    course = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role != 'admin' and \
       course.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền chỉnh sửa khóa học này.'}), 403
        else:
            flash('Bạn không có quyền chỉnh sửa khóa học này.', 'danger')
            abort(403)

    form = CourseForm(obj=course)
    
    if request.method == 'GET' and course.ai_settings and 'custom_prompt' in course.ai_settings:
        form.ai_prompt.data = course.ai_settings['custom_prompt']

    if form.validate_on_submit():
        ai_settings = {}
        if form.ai_prompt.data:
            ai_settings['custom_prompt'] = form.ai_prompt.data
        
        course.title = form.title.data
        course.description = form.description.data
        course.tags = form.tags.data
        course.is_public = form.is_public.data
        course.ai_settings = ai_settings if ai_settings else None

        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Thông tin khóa học đã được cập nhật!'})
        else:
            flash('Thông tin khóa học đã được cập nhật!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='courses'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_course_set_bare.html', form=form, title='Sửa Khóa học', course=course)
    return render_template('add_edit_course_set.html', form=form, title='Sửa Khóa học', course=course)

@courses_bp.route('/sets/delete/<int:set_id>', methods=['POST'])
def delete_course(set_id):
    """
    Xóa một khóa học.
    Chỉ creator_user_id hoặc admin mới có thể xóa khóa học.
    """
    course = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role != 'admin' and course.creator_user_id != current_user.user_id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền xóa khóa học này.'}), 403
        else:
            flash('Bạn không có quyền xóa khóa học này.', 'danger')
            abort(403)
    
    LearningItem.query.filter_by(container_id=set_id).delete()
    db.session.delete(course)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Khóa học đã được xóa thành công!'})
    else:
        flash('Khóa học đã được xóa thành công!', 'success')
        return redirect(url_for('content_management.content_dashboard', tab='courses'))

# --- ROUTES QUẢN LÝ BÀI HỌC (LearningItem) TRONG KHÓA HỌC ---

@courses_bp.route('/sets/<int:set_id>/lessons')
def list_lessons(set_id):
    """
    Hiển thị danh sách các bài học thuộc một khóa học cụ thể.
    Người dùng cần có quyền xem khóa học đó (public, creator, hoặc contributor).
    """
    course = LearningContainer.query.get_or_404(set_id)

    if not course.is_public and \
       current_user.user_role != 'admin' and \
       course.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id).first():
        flash('Bạn không có quyền xem khóa học này.', 'danger')
        abort(403)
    
    lessons = LearningItem.query.filter_by(
        container_id=set_id,
        item_type='LESSON'
    ).order_by(LearningItem.order_in_container).all() 

    can_edit = False
    if current_user.user_role == 'admin' or \
       course.creator_user_id == current_user.user_id or \
       ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        can_edit = True

    return render_template('lessons.html', course=course, lessons=lessons, can_edit=can_edit)

@courses_bp.route('/sets/<int:set_id>/lessons/add', methods=['GET', 'POST'])
def add_lesson(set_id):
    """
    Thêm bài học mới vào một khóa học.
    Chỉ creator_user_id, admin hoặc người dùng được cấp quyền 'editor' mới có thể thêm.
    """
    course = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role != 'admin' and \
       course.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền thêm bài học vào khóa học này.'}), 403
        else:
            flash('Bạn không có quyền thêm bài học vào khóa học này.', 'danger')
            abort(403)

    form = LessonForm()
    if form.validate_on_submit():
        item_content = {
            "title": form.title.data,
            "bbcode_content": form.bbcode_content.data,
            "lesson_audio_url": form.lesson_audio_url.data if form.lesson_audio_url.data else None,
            "lesson_image_url": form.lesson_image_url.data if form.lesson_image_url.data else None,
        }
        new_item = LearningItem(
            container_id=set_id,
            item_type='LESSON',
            content=item_content,
            order_in_container=LearningItem.query.filter_by(container_id=set_id, item_type='LESSON').count()
        )
        db.session.add(new_item)
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Bài học đã được thêm thành công!'})
        else:
            flash('Bài học đã được thêm thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='courses'))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_lesson_bare.html', form=form, title='Thêm Bài học mới', course=course)
    return render_template('add_edit_lesson.html', form=form, title='Thêm Bài học mới', course=course)

@courses_bp.route('/sets/<int:set_id>/lessons/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_lesson(set_id, item_id):
    """
    Chỉnh sửa một bài học cụ thể trong khóa học.
    Chỉ creator_user_id, admin hoặc người dùng được cấp quyền 'editor' mới có thể chỉnh sửa.
    """
    course = LearningContainer.query.get_or_404(set_id)
    lesson = LearningItem.query.get_or_404(item_id)

    if lesson.container_id != set_id or \
       (current_user.user_role != 'admin' and \
        course.creator_user_id != current_user.user_id and \
        not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first()):
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền chỉnh sửa bài học này.'}), 403
        else:
            flash('Bạn không có quyền chỉnh sửa bài học này.', 'danger')
            abort(403)

    form = LessonForm(obj=lesson)
    
    if request.method == 'GET':
        if lesson.content:
            form.title.data = lesson.content.get('title', '')
            form.bbcode_content.data = lesson.content.get('bbcode_content', '')
            form.lesson_audio_url.data = lesson.content.get('lesson_audio_url', '')
            form.lesson_image_url.data = lesson.content.get('lesson_image_url', '')
            form.ai_explanation.data = lesson.ai_explanation

    if form.validate_on_submit():
        lesson.content['title'] = form.title.data
        lesson.content['bbcode_content'] = form.bbcode_content.data
        lesson.content['lesson_audio_url'] = form.lesson_audio_url.data if form.lesson_audio_url.data else None
        lesson.content['lesson_image_url'] = form.lesson_image_url.data if form.lesson_image_url.data else None
        
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Bài học đã được cập nhật thành công!'})
        else:
            flash('Bài học đã được cập nhật thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='courses'))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_lesson_bare.html', form=form, title='Sửa Bài học', course=course, lesson=lesson)
    return render_template('add_edit_lesson.html', form=form, title='Sửa Bài học', course=course, lesson=lesson)

@courses_bp.route('/sets/<int:set_id>/lessons/delete/<int:item_id>', methods=['POST'])
def delete_lesson(set_id, item_id):
    """
    Xóa một bài học cụ thể trong khóa học.
    Chỉ creator_user_id, admin hoặc người dùng được cấp quyền 'editor' mới có thể xóa.
    """
    course = LearningContainer.query.get_or_404(set_id)
    lesson = LearningItem.query.get_or_404(item_id)

    if lesson.container_id != set_id or \
       (current_user.user_role != 'admin' and \
        course.creator_user_id != current_user.user_id and \
        not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first()):
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền xóa bài học này.'}), 403
        else:
            flash('Bạn không có quyền xóa bài học này.', 'danger')
            abort(403)
    
    db.session.delete(lesson)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Bài học đã được xóa thành công!'})
    else:
        flash('Bài học đã được xóa thành công!', 'success')
        return redirect(url_for('content_management.content_dashboard', tab='courses'))
