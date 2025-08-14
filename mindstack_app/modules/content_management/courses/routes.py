# File: newmindstack/mindstack_app/modules/content_management/courses/routes.py
# Phiên bản: 6.4
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

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
import json # Để xử lý trường JSON content
import bbcode # Cần cài đặt: pip install bbcode
from sqlalchemy import or_ # Cần cho việc kết hợp truy vấn

# Import các model và db instance từ cấp trên
from ....models import db, LearningContainer, LearningItem, User, SystemSetting, ContainerContributor
from ..forms import CourseForm, LessonForm # Import form từ thư mục cha (content_management)

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
    Hiển thị danh sách các khóa học mà người dùng hiện tại có quyền truy cập.
    Admin có thể thấy tất cả các khóa học.
    Người dùng thông thường chỉ thấy khóa học do mình tạo hoặc được cấp quyền chỉnh sửa.
    Nếu yêu cầu là AJAX, chỉ trả về phần danh sách khóa học.
    """
    courses = []
    if current_user.user_role == 'admin':
        # Admin thấy tất cả các khóa học
        courses = LearningContainer.query.filter_by(container_type='COURSE').all()
    else:
        # Người dùng thường thấy khóa học của mình tạo hoặc được cấp quyền
        user_id = current_user.user_id
        
        # Lấy các container_id mà người dùng hiện tại là người tạo
        created_courses_query = LearningContainer.query.filter_by(
            creator_user_id=user_id,
            container_type='COURSE'
        )

        # Lấy các container_id mà người dùng hiện tại được cấp quyền chỉnh sửa
        contributed_courses_query = LearningContainer.query.join(ContainerContributor).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor',
            LearningContainer.container_type == 'COURSE'
        )
        
        # Kết hợp hai truy vấn để lấy danh sách các khóa học duy nhất
        courses = created_courses_query.union(contributed_courses_query).all()

    # Kiểm tra nếu đây là yêu cầu AJAX (từ content_dashboard)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Nếu là AJAX, chỉ render phần danh sách các khóa học
        return render_template('_courses_list.html', courses=courses)
    else:
        # Nếu không phải AJAX, render toàn bộ trang như bình thường
        return render_template('courses.html', courses=courses)

@courses_bp.route('/sets/add', methods=['GET', 'POST'])
def add_course():
    """
    Thêm một khóa học mới.
    Chỉ người dùng đã đăng nhập mới có thể thêm khóa học.
    Người tạo khóa học sẽ tự động là creator_user_id.
    """
    form = CourseForm()
    if form.validate_on_submit():
        # Xử lý AI settings từ form gốc
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
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest': # Đây là khi form được gửi qua AJAX
            return jsonify({'success': True, 'message': 'Khóa học đã được thêm thành công!'})
        else:
            flash('Khóa học đã được thêm thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='courses'))
    
    # ĐÃ SỬA: Trả về JSON chứa lỗi nếu là AJAX POST và form không hợp lệ
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400
    
    # ĐÃ SỬA: Nếu là GET request VÀ có tham số is_modal=true, render bare template
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_course_set_bare.html', form=form, title='Thêm Khóa học mới')
    # Nếu là GET request và không có is_modal=true (hoặc không phải AJAX), render full template
    return render_template('add_edit_course_set.html', form=form, title='Thêm Khóa học mới')

@courses_bp.route('/sets/edit/<int:set_id>', methods=['GET', 'POST'])
def edit_course(set_id):
    """
    Chỉnh sửa thông tin khóa học.
    Chỉ creator_user_id, admin hoặc người dùng được cấp quyền 'editor' mới có thể chỉnh sửa.
    """
    course = LearningContainer.query.get_or_404(set_id)

    # Kiểm tra quyền chỉnh sửa (từ code gốc + logic phân quyền mới)
    if current_user.user_role != 'admin' and \
       course.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại flash và abort
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền chỉnh sửa khóa học này.'}), 403
        else:
            flash('Bạn không có quyền chỉnh sửa khóa học này.', 'danger')
            abort(403)

    form = CourseForm(obj=course)
    
    # Điền dữ liệu AI prompt vào form khi GET request (từ code gốc)
    if request.method == 'GET' and course.ai_settings and 'custom_prompt' in course.ai_settings:
        form.ai_prompt.data = course.ai_settings['custom_prompt']

    if form.validate_on_submit():
        # Xử lý AI settings from original form
        ai_settings = {}
        if form.ai_prompt.data:
            ai_settings['custom_prompt'] = form.ai_prompt.data
        
        course.title = form.title.data
        course.description = form.description.data
        course.tags = form.tags.data
        course.is_public = form.is_public.data
        course.ai_settings = ai_settings if ai_settings else None

        db.session.commit()
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Thông tin khóa học đã được cập nhật!'})
        else:
            flash('Thông tin khóa học đã được cập nhật!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='courses'))
    
    # ĐÃ SỬA: Trả về JSON chứa lỗi nếu là AJAX POST và form không hợp lệ
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    # ĐÃ SỬA: Nếu là GET request VÀ có tham số is_modal=true, render bare template
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_course_set_bare.html', form=form, title='Sửa Khóa học', course=course)
    # Nếu là GET request và không có is_modal=true (hoặc không phải AJAX), render full template
    return render_template('add_edit_course_set.html', form=form, title='Sửa Khóa học', course=course)

@courses_bp.route('/sets/delete/<int:set_id>', methods=['POST'])
def delete_course(set_id):
    """
    Xóa một khóa học.
    Chỉ creator_user_id hoặc admin mới có thể xóa khóa học.
    """
    course = LearningContainer.query.get_or_404(set_id)

    # Kiểm tra quyền xóa (từ code gốc + logic phân quyền mới)
    # Hiện tại chỉ người tạo hoặc admin mới có quyền xóa hoàn toàn container.
    # Contributor có thể chỉ có quyền chỉnh sửa nội dung bên trong.
    if current_user.user_role != 'admin' and course.creator_user_id != current_user.user_id:
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại flash và abort
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền xóa khóa học này.'}), 403
        else:
            flash('Bạn không có quyền xóa khóa học này.', 'danger')
            abort(403)
    
    # Xóa tất cả các bài học con trước (từ code gốc)
    LearningItem.query.filter_by(container_id=set_id).delete()
    db.session.delete(course)
    db.session.commit()
    
    # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại redirect
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

    # Kiểm tra quyền xem khóa học (từ code gốc + logic phân quyền mới)
    if not course.is_public and \
       current_user.user_role != 'admin' and \
       course.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id).first():
        flash('Bạn không có quyền xem khóa học này.', 'danger')
        abort(403)
    
    # Lấy các bài học thuộc khóa học này (từ code gốc)
    lessons = LearningItem.query.filter_by(
        container_id=set_id,
        item_type='LESSON'
    ).order_by(LearningItem.order_in_container).all() 

    # Xác định quyền chỉnh sửa để truyền xuống template
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

    # Kiểm tra quyền thêm bài học (từ code gốc + logic phân quyền mới)
    if current_user.user_role != 'admin' and \
       course.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại flash và abort
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền thêm bài học vào khóa học này.'}), 403
        else:
            flash('Bạn không có quyền thêm bài học vào khóa học này.', 'danger')
            abort(403)

    form = LessonForm()
    if form.validate_on_submit():
        # Xử lý nội dung bài học từ form gốc
        item_content = {
            "title": form.title.data,
            "bbcode_content": form.bbcode_content.data,
            "lesson_audio_url": form.lesson_audio_url.data if form.lesson_audio_url.data else None,
            "lesson_image_url": form.lesson_image_url.data if form.lesson_image_url.data else None,
            # ai_prompt cấp item có thể được thêm vào đây nếu có trường trong form
            # "ai_prompt": form.ai_prompt.data if form.ai_prompt.data else None
        }
        new_item = LearningItem(
            container_id=set_id,
            item_type='LESSON',
            content=item_content,
            # Tính toán order_in_container theo cách của bạn
            order_in_container=LearningItem.query.filter_by(container_id=set_id, item_type='LESSON').count()
        )
        db.session.add(new_item)
        db.session.commit()
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Bài học đã được thêm thành công!'})
        else:
            flash('Bài học đã được thêm thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='courses')) # Vẫn redirect về dashboard chính

    # ĐÃ SỬA: Trả về JSON chứa lỗi nếu là AJAX POST và form không hợp lệ
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    # ĐÃ SỬA: Nếu là GET request VÀ có tham số is_modal=true, render bare template
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

    # Đảm bảo bài học thuộc khóa học và người dùng có quyền chỉnh sửa (từ code gốc + logic phân quyền mới)
    if lesson.container_id != set_id or \
       (current_user.user_role != 'admin' and \
        course.creator_user_id != current_user.user_id and \
        not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first()):
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại flash và abort
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền chỉnh sửa bài học này.'}), 403
        else:
            flash('Bạn không có quyền chỉnh sửa bài học này.', 'danger')
            abort(403)

    form = LessonForm(obj=lesson)
    
    # Điền dữ liệu từ JSON content vào form khi GET request (từ code gốc)
    if request.method == 'GET':
        if lesson.content:
            form.title.data = lesson.content.get('title', '')
            form.bbcode_content.data = lesson.content.get('bbcode_content', '')
            form.lesson_audio_url.data = lesson.content.get('lesson_audio_url', '')
            form.lesson_image_url.data = lesson.content.get('lesson_image_url', '')
            form.ai_explanation.data = lesson.ai_explanation # Điền dữ liệu giải thích AI

    if form.validate_on_submit():
        # Cập nhật dữ liệu vào JSON content (từ code gốc)
        lesson.content['title'] = form.title.data
        lesson.content['bbcode_content'] = form.bbcode_content.data
        lesson.content['lesson_audio_url'] = form.lesson_audio_url.data if form.lesson_audio_url.data else None
        lesson.content['lesson_image_url'] = form.lesson_image_url.data if form.lesson_image_url.data else None
        # ai_prompt cấp item có thể được cập nhật vào đây nếu có trường trong form
        # lesson.content['ai_prompt'] = form.ai_prompt.data if form.ai_prompt.data else None
        
        # ai_explanation không được sửa trực tiếp qua form này
        # lesson.ai_explanation = form.ai_explanation.data # KHÔNG NÊN LÀM VẬY NẾU CHỈ ĐỂ HIỂN THỊ

        db.session.commit()
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Bài học đã được cập nhật thành công!'})
        else:
            flash('Bài học đã được cập nhật thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='courses')) # Vẫn redirect về dashboard chính

    # ĐÃ SỬA: Trả về JSON chứa lỗi nếu là AJAX POST và form không hợp lệ
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    # ĐÃ SỬA: Nếu là GET request VÀ có tham số is_modal=true, render bare template
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

    # Kiểm tra quyền xóa (từ code gốc + logic phân quyền mới)
    if lesson.container_id != set_id or \
       (current_user.user_role != 'admin' and \
        course.creator_user_id != current_user.user_id and \
        not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first()):
        
        # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại flash và abort
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền xóa bài học này.'}), 403
        else:
            flash('Bạn không có quyền xóa bài học này.', 'danger')
            abort(403)
    
    db.session.delete(lesson)
    db.session.commit()
    
    # ĐÃ SỬA: Trả về JSON nếu là AJAX POST, ngược lại redirect
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Bài học đã được xóa thành công!'})
    else:
        flash('Bài học đã được xóa thành công!', 'success')
        return redirect(url_for('content_management.content_dashboard', tab='courses')) # Vẫn redirect về dashboard chính
