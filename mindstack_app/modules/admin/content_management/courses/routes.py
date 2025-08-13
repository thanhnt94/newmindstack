# File: Mindstack/web/mindstack_app/modules/admin/content_management/courses/routes.py
# Version: 1.3 - Giải pháp cuối cùng cho lỗi circular import
# Mục đích: Xử lý các yêu cầu liên quan đến việc tạo, sửa, xóa Khóa học và Bài học (cho admin).

from flask import render_template, redirect, url_for, flash, request, abort, Blueprint # Import Blueprint
from flask_login import login_required, current_user
import json # Để xử lý trường JSON content
import bbcode # Cần cài đặt: pip install bbcode

# ĐỊNH NGHĨA BLUEPRINT NGAY TẠI ĐÂY
admin_courses_bp = Blueprint('admin_courses', __name__, template_folder='templates')

# Import các model và db instance từ cấp trên (đi lên 4 cấp)
from .....models import LearningContainer, LearningItem, User, SystemSetting
from .....db_instance import db
# Tái sử dụng forms từ my_content/courses
from ....my_content.courses.forms import CourseForm, LessonForm

# Middleware để đảm bảo người dùng đã đăng nhập và có quyền admin
@admin_courses_bp.before_request 
@login_required 
def admin_course_required():
    if not current_user.is_authenticated or current_user.user_role != 'admin':
        flash('Bạn không có quyền truy cập khu vực quản lý Khóa học của admin.', 'danger')
        abort(403) 

# --- ROUTES QUẢN LÝ KHÓA HỌC (LearningContainer) ---
# Admin có thể xem TẤT CẢ các Khóa học, không chỉ của mình
@admin_courses_bp.route('/')
@admin_courses_bp.route('/sets')
def list_admin_courses():
    courses = LearningContainer.query.filter_by(
        container_type='COURSE'
    ).all()
    # Lấy thông tin người tạo để hiển thị trong bảng
    users = User.query.all()
    user_map = {user.user_id: user.username for user in users}
    return render_template('admin_courses.html', courses=courses, user_map=user_map)

@admin_courses_bp.route('/sets/add', methods=['GET', 'POST'])
def add_admin_course():
    form = CourseForm()
    # Admin có thể gán Khóa học cho người dùng khác
    # Thêm trường để chọn creator_user_id vào form nếu muốn admin gán
    # For simplicity, let's assume admin creates for themselves or a default user for now
    # Or we can add a SelectField for creator_user_id if needed.
    
    # Lấy danh sách người dùng để admin có thể chọn người tạo
    users = User.query.all()
    # form.creator = SelectField('Người tạo', choices=[(str(u.user_id), u.username) for u in users], validators=[DataRequired()])

    if form.validate_on_submit():
        ai_settings = {}
        if form.ai_prompt.data:
            ai_settings['custom_prompt'] = form.ai_prompt.data

        # Admin tạo Khóa học, mặc định là admin là người tạo, hoặc có thể chọn từ form
        creator_id = current_user.user_id # Mặc định admin là người tạo
        # if hasattr(form, 'creator') and form.creator.data:
        #     creator_id = int(form.creator.data)

        new_course = LearningContainer(
            creator_user_id=creator_id,
            container_type='COURSE',
            title=form.title.data,
            description=form.description.data,
            tags=form.tags.data,
            is_public=form.is_public.data,
            ai_settings=ai_settings if ai_settings else None
        )
        db.session.add(new_course)
        db.session.commit()
        flash('Khóa học đã được thêm thành công (Admin)!', 'success')
        return redirect(url_for('admin_courses.list_admin_courses'))
            
    return render_template('add_edit_admin_course_set.html', form=form, title='Thêm Khóa học mới (Admin)')

@admin_courses_bp.route('/sets/edit/<int:set_id>', methods=['GET', 'POST'])
def edit_admin_course(set_id):
    course = LearningContainer.query.get_or_404(set_id)

    form = CourseForm(obj=course)
    # Lấy danh sách người dùng để admin có thể chọn người tạo
    users = User.query.all()
    # form.creator = SelectField('Người tạo', choices=[(str(u.user_id), u.username) for u in users], validators=[DataRequired()])

    # Điền dữ liệu AI prompt và creator vào form khi GET request
    if request.method == 'GET':
        if course.ai_settings and 'custom_prompt' in course.ai_settings:
            form.ai_prompt.data = course.ai_settings['custom_prompt']
        # if hasattr(form, 'creator'):
        #     form.creator.data = str(course.creator_user_id)

    if form.validate_on_submit():
        ai_settings = {}
        if form.ai_prompt.data:
            ai_settings['custom_prompt'] = form.ai_prompt.data
        
        course.title = form.title.data
        course.description = form.description.data
        course.tags = form.tags.data
        course.is_public = form.is_public.data
        course.ai_settings = ai_settings if ai_settings else None
        # if hasattr(form, 'creator'):
        #     course.creator_user_id = int(form.creator.data)

        db.session.commit()
        flash('Thông tin khóa học đã được cập nhật (Admin)!', 'success')
        return redirect(url_for('admin_courses.list_admin_courses'))

    return render_template('add_edit_admin_course_set.html', form=form, title='Sửa Khóa học (Admin)', course=course)

@admin_courses_bp.route('/sets/delete/<int:set_id>', methods=['POST'])
def delete_admin_course(set_id):
    course = LearningContainer.query.get_or_404(set_id)
    
    # Admin có quyền xóa bất kỳ Khóa học nào
    # if course.creator_user_id != current_user.user_id: # Không cần kiểm tra này cho admin
    #    flash('Bạn không có quyền xóa khóa học này.', 'danger')
    #    abort(403)
    
    # Xóa tất cả các bài học con trước
    LearningItem.query.filter_by(container_id=set_id).delete()
    db.session.delete(course)
    db.session.commit()
    flash('Khóa học đã được xóa thành công (Admin)!', 'success')
    return redirect(url_for('admin_courses.list_admin_courses'))

# --- ROUTES QUẢN LÝ BÀI HỌC (LearningItem) TRONG KHÓA HỌC ---
# Admin có quyền xem TẤT CẢ các bài học trong khóa học, không chỉ của mình
@admin_courses_bp.route('/sets/<int:set_id>/lessons')
def list_admin_lessons(set_id):
    course = LearningContainer.query.get_or_404(set_id)
    # Admin có quyền xem khóa học này
    # if course.creator_user_id != current_user.user_id: # Không cần kiểm tra này cho admin
    #    flash('Bạn không có quyền xem khóa học này.', 'danger')
    #    abort(403)
    
    lessons = LearningItem.query.filter_by(
        container_id=set_id,
        item_type='LESSON'
    ).order_by(LearningItem.order_in_container).all() 

    return render_template('admin_lessons.html', course=course, lessons=lessons)

@admin_courses_bp.route('/sets/<int:set_id>/lessons/add', methods=['GET', 'POST'])
def add_admin_lesson(set_id):
    course = LearningContainer.query.get_or_404(set_id)
    # Admin có quyền thêm bài học vào khóa học này
    # if course.creator_user_id != current_user.user_id: # Không cần kiểm tra này cho admin
    #    flash('Bạn không có quyền thêm bài học vào khóa học này.', 'danger')
    #    abort(403)

    form = LessonForm()
    if form.validate_on_submit():
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
            order_in_container=LearningItem.query.filter_by(container_id=set_id).count() 
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Bài học đã được thêm thành công (Admin)!', 'success')
        return redirect(url_for('admin_courses.list_admin_lessons', set_id=set_id))
    
    return render_template('add_edit_admin_lesson.html', form=form, title='Thêm Bài học mới (Admin)', course=course)

@admin_courses_bp.route('/sets/<int:set_id>/lessons/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_admin_lesson(set_id, item_id):
    course = LearningContainer.query.get_or_404(set_id)
    lesson = LearningItem.query.get_or_404(item_id)

    # Đảm bảo bài học thuộc khóa học
    if lesson.container_id != set_id:
        flash('Bài học không thuộc khóa học này.', 'danger')
        abort(403)
    # Admin có quyền chỉnh sửa bài học này
    # if course.creator_user_id != current_user.user_id: # Không cần kiểm tra này cho admin
    #    flash('Bạn không có quyền chỉnh sửa bài học này.', 'danger')
    #    abort(403)

    form = LessonForm(obj=lesson)
    
    # Điền dữ liệu từ JSON content vào form khi GET request
    if request.method == 'GET':
        if lesson.content:
            form.title.data = lesson.content.get('title', '')
            form.bbcode_content.data = lesson.content.get('bbcode_content', '')
            form.lesson_audio_url.data = lesson.content.get('lesson_audio_url', '')
            form.lesson_image_url.data = lesson.content.get('lesson_image_url', '')
            form.ai_explanation.data = lesson.ai_explanation # Điền dữ liệu giải thích AI

    if form.validate_on_submit():
        # Cập nhật dữ liệu vào JSON content
        lesson.content['title'] = form.title.data
        lesson.content['bbcode_content'] = form.bbcode_content.data
        lesson.content['lesson_audio_url'] = form.lesson_audio_url.data if form.lesson_audio_url.data else None
        lesson.content['lesson_image_url'] = form.lesson_image_url.data if form.lesson_image_url.data else None
        # ai_prompt cấp item có thể được cập nhật vào đây nếu có trường trong form
        # lesson.content['ai_prompt'] = form.ai_prompt.data if form.ai_prompt.data else None
        
        # ai_explanation không được sửa trực tiếp qua form này
        # lesson.ai_explanation = form.ai_explanation.data # KHÔNG NÊN LÀM VẬY NẾU CHỈ ĐỂ HIỂN THỊ

        db.session.commit()
        flash('Bài học đã được cập nhật thành công (Admin)!', 'success')
        return redirect(url_for('admin_courses.list_admin_lessons', set_id=set_id))

    return render_template('add_edit_admin_lesson.html', form=form, title='Sửa Bài học (Admin)', course=course, lesson=lesson)

@admin_courses_bp.route('/sets/<int:set_id>/lessons/delete/<int:item_id>', methods=['POST'])
def delete_admin_lesson(set_id, item_id):
    course = LearningContainer.query.get_or_404(set_id)
    lesson = LearningItem.query.get_or_404(item_id)

    if lesson.container_id != set_id:
        flash('Bài học không thuộc khóa học này.', 'danger')
        abort(403)
    # Admin có quyền xóa bài học này
    # if course.creator_user_id != current_user.user_id: # Không cần kiểm tra này cho admin
    #    flash('Bạn không có quyền xóa bài học này.', 'danger')
    #    abort(403)
    
    db.session.delete(lesson)
    db.session.commit()
    flash('Bài học đã được xóa thành công (Admin)!', 'success')
    return redirect(url_for('admin_courses.list_admin_lessons', set_id=set_id))
