# mindstack_app/modules/content_management/courses/routes.py
# Phiên bản: 4.4
# MỤC ĐÍCH: Hỗ trợ sắp xếp lại thứ tự bài học (lesson) trong một khóa học.
# ĐÃ SỬA: Bổ sung logic vào add_lesson để chèn bài học vào vị trí cụ thể.
# ĐÃ SỬA: Bổ sung logic vào edit_lesson để thay đổi vị trí bài học và cập nhật lại thứ tự các bài học khác.
# ĐÃ SỬA: Cập nhật route list_lessons để sắp xếp theo order_in_container.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from sqlalchemy.orm.attributes import flag_modified
from ..forms import CourseForm, LessonForm # Đã sửa từ CourseSetForm
from ....models import db, LearningContainer, LearningItem, ContainerContributor, User
import pandas as pd
import tempfile
import os
from ....modules.shared.utils.pagination import get_pagination_data
from ....modules.shared.utils.search import apply_search_filter
from ....modules.shared.utils.html_sanitizer import sanitize_rich_text
from ....modules.shared.utils.bbcode_parser import bbcode_to_html

courses_bp = Blueprint('content_management_courses', __name__,
                       template_folder='templates') # Đã cập nhật đường dẫn template



def _has_editor_access(container_id):
    if current_user.user_role == User.ROLE_FREE:
        return False
    return ContainerContributor.query.filter_by(
        container_id=container_id,
        user_id=current_user.user_id,
        permission_level='editor'
    ).first() is not None

def _apply_is_public_restrictions(form):
    """Disable public toggle for free users and ensure value stays False."""
    if hasattr(form, 'is_public') and current_user.user_role == 'free':
        form.is_public.data = False
        existing_render_kw = dict(form.is_public.render_kw or {})
        existing_render_kw['disabled'] = True
        form.is_public.render_kw = existing_render_kw


@courses_bp.route('/courses/process_excel_info', methods=['POST'])
@login_required
def process_excel_info():
    """
    Xử lý file Excel được tải lên để trích xuất thông tin từ sheet 'Info'.

    Hàm này đọc một file Excel, tìm kiếm sheet có tên 'Info',
    và trích xuất dữ liệu từ đó, trả về dưới dạng JSON.
    """
    if 'excel_file' not in request.files:
        return jsonify({'success': False, 'message': 'Không tìm thấy file.'}), 400
    file = request.files['excel_file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Chưa chọn file nào.'}), 400
    if file and file.filename.endswith('.xlsx'):
        temp_filepath = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                file.save(tmp_file.name)
                temp_filepath = tmp_file.name
            df_info = pd.read_excel(temp_filepath, sheet_name='Info')
            info_data = df_info.set_index('Key')['Value'].dropna().to_dict()
            return jsonify({'success': True, 'data': info_data})
        except ValueError:
            return jsonify({'success': False, 'message': "Không tìm thấy sheet 'Info' trong file."})
        except Exception as e:
            current_app.logger.error(f"Lỗi khi xử lý sheet Info (Course): {e}")
            return jsonify({'success': False, 'message': f'Lỗi đọc file Excel: {e}'}), 500
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
    return jsonify({'success': False, 'message': 'File không hợp lệ. Vui lòng chọn file .xlsx'}), 400

@courses_bp.route('/courses')
@login_required
def list_course_sets():
    """
    Hiển thị danh sách các bộ Khóa học.

    Hàm này truy xuất các bộ Khóa học mà người dùng hiện tại đã tạo hoặc đóng góp,
    áp dụng bộ lọc tìm kiếm và phân trang, sau đó hiển thị chúng.
    """
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)

    base_query = LearningContainer.query.filter_by(container_type='COURSE')

    if current_user.user_role == User.ROLE_ADMIN:
        pass
    elif current_user.user_role == User.ROLE_FREE:
        base_query = base_query.filter_by(creator_user_id=current_user.user_id)
    else:
        user_id = current_user.user_id
        created_sets_query = base_query.filter_by(creator_user_id=user_id)
        contributed_sets_query = base_query.join(ContainerContributor).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor'
        )
        base_query = created_sets_query.union(contributed_sets_query)

    search_field_map = {
        'title': LearningContainer.title,
        'description': LearningContainer.description,
        'tags': LearningContainer.tags
    }
    base_query = apply_search_filter(base_query, search_query, search_field_map, search_field)

    pagination = get_pagination_data(base_query.order_by(LearningContainer.created_at.desc()), page)
    course_sets = pagination.items

    for set_item in course_sets:
        set_item.item_count = db.session.query(LearningItem).filter_by(
            container_id=set_item.container_id,
            item_type='LESSON'
        ).count()

        creator = getattr(set_item, 'creator', None)
        if creator:
            set_item.creator_display_name = creator.username
        else:
            set_item.creator_display_name = "Không xác định"

        editor_labels = []
        seen_user_ids = set()

        if creator:
            seen_user_ids.add(creator.user_id)
            editor_labels.append(creator.username)

        for contributor in getattr(set_item, 'contributors', []) or []:
            if contributor.permission_level != 'editor':
                continue
            contributor_user = getattr(contributor, 'user', None)
            if not contributor_user or contributor_user.user_id in seen_user_ids:
                continue

            editor_labels.append(contributor_user.username)
            seen_user_ids.add(contributor_user.user_id)

        if not editor_labels:
            editor_labels.append("Chưa có")

        set_item.editor_display_names = editor_labels

    template_vars = {
        'course_sets': course_sets, 
        'pagination': pagination, 
        'search_query': search_query,
        'search_field': search_field,
        'search_field_map': search_field_map
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_courses_list.html', **template_vars)
    else:
        return render_template('courses.html', **template_vars)

@courses_bp.route('/courses/add', methods=['GET', 'POST'])
@login_required
def add_course_set():
    """
    Thêm một bộ Khóa học mới.
    """
    form = CourseForm()
    _apply_is_public_restrictions(form)
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        try:
            ai_prompt_value = (form.ai_prompt.data or '').strip()
            new_set = LearningContainer(
                creator_user_id=current_user.user_id,
                container_type='COURSE',
                title=form.title.data,
                description=form.description.data,
                tags=form.tags.data,
                is_public=False if current_user.user_role == 'free' else form.is_public.data,
                ai_prompt=ai_prompt_value or None,
            )
            db.session.add(new_set)
            db.session.commit()
            flash_message = 'Bộ khóa học mới đã được tạo thành công!'
            flash_category = 'success'
        except Exception as e:
            db.session.rollback()
            flash_message = f'Lỗi khi xử lý: {str(e)}'
            flash_category = 'danger'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': flash_category == 'success', 'message': flash_message})
        else:
            flash(flash_message, flash_category)
            return redirect(url_for('content_management.content_dashboard', tab='courses'))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400
    
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_course_set_bare.html', form=form, title='Thêm Bộ khóa học mới')
    
    return render_template('add_edit_course_set.html', form=form, title='Thêm Bộ khóa học mới')


@courses_bp.route('/courses/edit/<int:set_id>', methods=['GET', 'POST'])
@login_required
def edit_course_set(set_id):
    """
    Chỉnh sửa một bộ Khóa học hiện có.
    """
    course_set = LearningContainer.query.get_or_404(set_id)
    if course_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)
        
    form = CourseForm(obj=course_set)
    _apply_is_public_restrictions(form)
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        try:
            course_set.title = form.title.data
            course_set.description = form.description.data
            course_set.tags = form.tags.data
            course_set.is_public = False if current_user.user_role == 'free' else form.is_public.data
            ai_prompt_value = (form.ai_prompt.data or '').strip()
            course_set.ai_prompt = ai_prompt_value or None
            db.session.commit()
            flash_message = 'Bộ khóa học đã được cập nhật!'
            flash_category = 'success'
        except Exception as e:
            db.session.rollback()
            flash_message = f'Lỗi khi xử lý: {str(e)}'
            flash_category = 'danger'
            
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': flash_category == 'success', 'message': flash_message})
        else:
            flash(flash_message, flash_category)
            return redirect(url_for('content_management.content_dashboard', tab='courses'))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400
    
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_course_set_bare.html', form=form, title='Chỉnh sửa Bộ khóa học')
    
    return render_template('add_edit_course_set.html', form=form, title='Chỉnh sửa Bộ khóa học')

@courses_bp.route('/courses/delete/<int:set_id>', methods=['POST'])
@login_required
def delete_course_set(set_id):
    """
    Xóa một bộ Khóa học.
    """
    course_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and course_set.creator_user_id != current_user.user_id:
        abort(403)
    db.session.delete(course_set)
    db.session.commit()
    flash('Bộ khóa học đã được xóa thành công!', 'success')
    return redirect(url_for('content_management.content_dashboard', tab='courses'))

@courses_bp.route('/courses/<int:set_id>/lessons')
@login_required
def list_lessons(set_id):
    """
    Hiển thị danh sách các bài học trong một bộ Khóa học cụ thể.
    """
    course = LearningContainer.query.get_or_404(set_id)
    if not course.is_public and course.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_ADMIN:
            pass
        elif current_user.user_role == User.ROLE_FREE or not _has_editor_access(set_id):
            abort(403)
        
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)

    base_query = LearningItem.query.filter_by(
        container_id=course.container_id,
        item_type='LESSON'
    )
    
    item_search_field_map = {
        'title': LearningItem.content['title'],
        'content': func.coalesce(LearningItem.content['content_html'], LearningItem.content['bbcode_content']),
    }

    base_query = apply_search_filter(base_query, search_query, item_search_field_map, search_field)

    # ĐÃ SỬA: Sắp xếp theo `order_in_container` thay vì ID
    pagination = get_pagination_data(base_query.order_by(LearningItem.order_in_container), page)
    lessons = pagination.items
    can_edit = (
        current_user.user_role == User.ROLE_ADMIN or
        course.creator_user_id == current_user.user_id or
        _has_editor_access(set_id)
    )
       
    return render_template('lessons.html', 
                           course=course, 
                           lessons=lessons, 
                           can_edit=can_edit, 
                           pagination=pagination, 
                           search_query=search_query,
                           search_field=search_field,
                           search_field_map=item_search_field_map
                           )

@courses_bp.route('/courses/<int:set_id>/lessons/add', methods=['GET', 'POST'])
@login_required
def add_lesson(set_id):
    """
    Thêm một bài học mới vào một bộ Khóa học cụ thể.
    """
    course_set = LearningContainer.query.get_or_404(set_id)
    if course_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)
        
    form = LessonForm()
    if form.validate_on_submit():
        # THÊM MỚI: Xử lý logic chèn bài học
        new_order = form.order_in_container.data
        
        if new_order is not None:
            # Cập nhật lại thứ tự của các bài học cũ
            db.session.query(LearningItem).filter(
                LearningItem.container_id == set_id,
                LearningItem.item_type == 'LESSON',
                LearningItem.order_in_container >= new_order
            ).update({
                LearningItem.order_in_container: LearningItem.order_in_container + 1
            })
        else:
            # Nếu không có thứ tự cụ thể, thêm vào cuối
            max_order = db.session.query(db.func.max(LearningItem.order_in_container)).filter_by(
                container_id=set_id,
                item_type='LESSON'
            ).scalar()
            new_order = (max_order or 0) + 1
        
        content_dict = {
            'title': form.title.data,
            'content_html': sanitize_rich_text(form.content_html.data),
            'estimated_time': form.estimated_time.data,
        }

        new_item = LearningItem(
            container_id=set_id,
            item_type='LESSON',
            content=content_dict,
            order_in_container=new_order
        )
        db.session.add(new_item)
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Bài học mới đã được thêm!'})
        else:
            flash('Bài học đã được thêm!', 'success')
            return redirect(url_for('.list_lessons', set_id=set_id))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400
        
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('add_edit_lesson.html', form=form, course_set=course_set, title='Thêm Bài học')
        
    return render_template('add_edit_lesson.html', form=form, course_set=course_set, title='Thêm Bài học')

@courses_bp.route('/courses/<int:set_id>/lessons/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_lesson(set_id, item_id):
    """
    Chỉnh sửa một bài học hiện có trong một bộ Khóa học cụ thể.
    """
    course_set = LearningContainer.query.get_or_404(set_id)
    lesson_item = LearningItem.query.filter_by(item_id=item_id, container_id=set_id).first_or_404()
    if course_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)
        
    form = LessonForm()
    if form.validate_on_submit():
        # Lấy thứ tự cũ và mới
        old_order = lesson_item.order_in_container
        new_order = form.order_in_container.data
        
        # Nếu thứ tự thay đổi, cập nhật lại các bài học khác
        if new_order is not None and new_order != old_order:
            if new_order > old_order:
                db.session.query(LearningItem).filter(
                    LearningItem.container_id == set_id,
                    LearningItem.item_type == 'LESSON',
                    LearningItem.order_in_container > old_order,
                    LearningItem.order_in_container <= new_order
                ).update({
                    LearningItem.order_in_container: LearningItem.order_in_container - 1
                })
            else: # new_order < old_order
                db.session.query(LearningItem).filter(
                    LearningItem.container_id == set_id,
                    LearningItem.item_type == 'LESSON',
                    LearningItem.order_in_container >= new_order,
                    LearningItem.order_in_container < old_order
                ).update({
                    LearningItem.order_in_container: LearningItem.order_in_container + 1
                })
            lesson_item.order_in_container = new_order
        
        lesson_item.content['title'] = form.title.data
        lesson_item.content['content_html'] = sanitize_rich_text(form.content_html.data)
        lesson_item.content.pop('bbcode_content', None)
        lesson_item.content['estimated_time'] = form.estimated_time.data
        flag_modified(lesson_item, "content")
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Bài học đã được cập nhật!'})
        else:
            flash('Bài học đã được cập nhật!', 'success')
            return redirect(url_for('.list_lessons', set_id=set_id))
            
    if request.method == 'GET':
        form.title.data = lesson_item.content.get('title')
        existing_html = lesson_item.content.get('content_html')
        if not existing_html:
            existing_html = bbcode_to_html(lesson_item.content.get('bbcode_content', ''))
        form.content_html.data = existing_html
        form.estimated_time.data = lesson_item.content.get('estimated_time')
        form.order_in_container.data = lesson_item.order_in_container
        
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('add_edit_lesson.html', form=form, course_set=course_set, lesson_item=lesson_item, title='Sửa Bài học')
        
    return render_template('add_edit_lesson.html', form=form, course_set=course_set, lesson_item=lesson_item, title='Sửa Bài học')

@courses_bp.route('/courses/<int:set_id>/lessons/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_lesson(set_id, item_id):
    """
    Xóa một bài học khỏi một bộ Khóa học cụ thể.
    """
    course_set = LearningContainer.query.get_or_404(set_id)
    lesson_item = LearningItem.query.get_or_404(item_id)
    if course_set.creator_user_id != current_user.user_id:
        if current_user.user_role == User.ROLE_FREE:
            abort(403)
        if current_user.user_role != User.ROLE_ADMIN and not _has_editor_access(set_id):
            abort(403)
        
    db.session.delete(lesson_item)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Bài học đã được xóa.'})
    else:
        flash('Bài học đã được xóa.', 'success')
        return redirect(url_for('.list_lessons', set_id=set_id))
