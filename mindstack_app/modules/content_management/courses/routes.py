# File: newmindstack/mindstack_app/modules/content_management/courses/routes.py
# Phiên bản: 4.1
# ĐÃ SỬA: Khắc phục lỗi ImportError bằng cách đổi tên import CourseSetForm thành CourseForm.
# ĐÃ SỬA: Cập nhật template_folder của Blueprint để phản ánh cấu trúc thư mục mới.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.orm.attributes import flag_modified
from ..forms import CourseForm, LessonForm # Đã sửa từ CourseSetForm thành CourseForm
from ....models import db, LearningContainer, LearningItem, ContainerContributor, User
import pandas as pd
import tempfile
import os
from ....utils.pagination import get_pagination_data
from ....utils.search import apply_search_filter

courses_bp = Blueprint('content_management_courses', __name__,
                       template_folder='templates') # Đã cập nhật đường dẫn template

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

    if current_user.user_role != 'admin':
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

    Hàm này xử lý việc tạo bộ Khóa học, bao gồm cả việc nhập dữ liệu từ file Excel
    và thêm các bài học liên quan.
    """
    form = CourseForm() # Đã sửa từ CourseSetForm
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        temp_filepath = None
        try:
            new_set = LearningContainer(
                creator_user_id=current_user.user_id,
                container_type='COURSE',
                title=form.title.data,
                description=form.description.data,
                tags=form.tags.data,
                is_public=form.is_public.data,
                ai_settings={'custom_prompt': form.ai_prompt.data} if form.ai_prompt.data else None
            )
            db.session.add(new_set)
            db.session.flush()
            if form.excel_file.data and form.excel_file.data.filename != '':
                excel_file = form.excel_file.data
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    excel_file.save(tmp_file.name)
                    temp_filepath = tmp_file.name
                df = pd.read_excel(temp_filepath, sheet_name='Data')
                required_cols = ['title', 'content']
                if not all(col in df.columns for col in required_cols):
                    raise ValueError(f"File Excel (sheet 'Data') phải có các cột bắt buộc: {', '.join(required_cols)}.")
                items_added_count = 0
                for index, row in df.iterrows():
                    title_content = str(row['title']) if pd.notna(row['title']) else ''
                    lesson_content = str(row['content']) if pd.notna(row['content']) else ''
                    if title_content and lesson_content:
                        item_content = {'title': title_content, 'content': lesson_content}
                        optional_cols = ['audio_content', 'audio_url', 'image_url', 'ai_explanation']
                        for col in optional_cols:
                            if col in df.columns and pd.notna(row[col]):
                                item_content[col] = str(row[col])
                        new_item = LearningItem(
                            container_id=new_set.container_id,
                            item_type='LESSON',
                            content=item_content,
                            order_in_container=index + 1
                        )
                        db.session.add(new_item)
                        items_added_count += 1
                flash_message = f'Bộ khóa học và {items_added_count} bài học từ Excel đã được tạo thành công!'
                flash_category = 'success'
            else:
                flash_message = 'Bộ khóa học mới đã được tạo thành công!'
                flash_category = 'success'
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash_message = f'Lỗi khi xử lý: {str(e)}'
            flash_category = 'danger'
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
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

    Hàm này cho phép chỉnh sửa thông tin của bộ Khóa học và cập nhật/thêm các bài học
    từ file Excel.
    """
    course_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and \
       course_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        abort(403)
    form = CourseForm(obj=course_set) # Đã sửa từ CourseSetForm
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        temp_filepath = None
        try:
            course_set.title = form.title.data
            course_set.description = form.description.data
            course_set.tags = form.tags.data
            course_set.is_public = form.is_public.data
            course_set.ai_settings = {'custom_prompt': form.ai_prompt.data} if form.ai_prompt.data else None
            if form.excel_file.data and form.excel_file.data.filename != '':
                excel_file = form.excel_file.data
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    excel_file.save(tmp_file.name)
                    temp_filepath = tmp_file.name
                df = pd.read_excel(temp_filepath, sheet_name='Data')
                required_cols = ['title', 'content']
                if not all(col in df.columns for col in required_cols):
                    raise ValueError(f"File Excel (sheet 'Data') phải có các cột bắt buộc: {', '.join(required_cols)}.")
                LearningItem.query.filter_by(container_id=set_id, item_type='LESSON').delete()
                db.session.flush()
                for index, row in df.iterrows():
                    title_content = str(row['title']) if pd.notna(row['title']) else ''
                    lesson_content = str(row['content']) if pd.notna(row['content']) else ''
                    if title_content and lesson_content:
                        item_content = {'title': title_content, 'content': lesson_content}
                        optional_cols = ['audio_content', 'audio_url', 'image_url', 'ai_explanation']
                        for col in optional_cols:
                            if col in df.columns and pd.notna(row[col]):
                                item_content[col] = str(row[col])
                        new_item = LearningItem(
                            container_id=set_id,
                            item_type='LESSON',
                            content=item_content,
                            order_in_container=index + 1
                        )
                        db.session.add(new_item)
                flash_message = 'Bộ khóa học và các bài học từ Excel đã được cập nhật!'
                flash_category = 'success'
            else:
                flash_message = 'Bộ khóa học đã được cập nhật!'
                flash_category = 'success'
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash_message = f'Lỗi khi xử lý: {str(e)}'
            flash_category = 'danger'
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
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

    Hàm này cho phép xóa một bộ Khóa học và các bài học liên quan.
    Chỉ người tạo hoặc admin mới có quyền xóa.
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

    Hàm này truy xuất các bài học của một bộ Khóa học, áp dụng bộ lọc tìm kiếm
    trên nội dung bài học và phân trang, sau đó hiển thị chúng.
    """
    course_set = LearningContainer.query.get_or_404(set_id)
    if not course_set.is_public and \
       current_user.user_role != 'admin' and \
       course_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id).first():
        abort(403)
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)

    base_query = LearningItem.query.filter_by(
        container_id=course_set.container_id,
        item_type='LESSON'
    )
    
    item_search_field_map = {
        'title': LearningItem.content['title'],
        'content': LearningItem.content['content'],
        'audio_content': LearningItem.content['audio_content'],
        'audio_url': LearningItem.content['audio_url'],
        'image_url': LearningItem.content['image_url']
    }

    base_query = apply_search_filter(base_query, search_query, item_search_field_map, search_field)

    pagination = get_pagination_data(base_query.order_by(LearningItem.order_in_container), page)
    lessons = pagination.items
    can_edit = (current_user.user_role == 'admin' or \
       course_set.creator_user_id == current_user.user_id or \
       ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first())
    return render_template('lessons.html', 
                           course_set=course_set, 
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

    Hàm này xử lý việc thêm một bài học mới vào một bộ Khóa học hiện có.
    """
    course_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and \
       course_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        abort(403)
    form = LessonForm()
    if form.validate_on_submit():
        max_order = db.session.query(db.func.max(LearningItem.order_in_container)).filter_by(
            container_id=set_id,
            item_type='LESSON'
        ).scalar()
        new_order = (max_order or 0) + 1
        new_item = LearningItem(
            container_id=set_id,
            item_type='LESSON',
            content={
                'title': form.title.data, 
                'content': form.content.data,
                'audio_content': form.audio_content.data,
                'audio_url': form.audio_url.data,
                'image_url': form.image_url.data,
            },
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

    Hàm này xử lý việc cập nhật nội dung của một bài học.
    """
    course_set = LearningContainer.query.get_or_404(set_id)
    lesson_item = LearningItem.query.filter_by(item_id=item_id, container_id=set_id).first_or_404()
    if current_user.user_role != 'admin' and \
       course_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        abort(403)
    form = LessonForm(obj=lesson_item.content)
    if form.validate_on_submit():
        lesson_item.content['title'] = form.title.data
        lesson_item.content['content'] = form.content.data
        lesson_item.content['audio_content'] = form.audio_content.data
        lesson_item.content['audio_url'] = form.audio_url.data
        lesson_item.content['image_url'] = form.image_url.data
        flag_modified(lesson_item, "content")
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Bài học đã được cập nhật!'})
        else:
            flash('Bài học đã được cập nhật!', 'success')
            return redirect(url_for('.list_lessons', set_id=set_id))
    if request.method == 'GET':
        form.title.data = lesson_item.content.get('title')
        form.content.data = lesson_item.content.get('content')
        form.audio_content.data = lesson_item.content.get('audio_content')
        form.audio_url.data = lesson_item.content.get('audio_url')
        form.image_url.data = lesson_item.content.get('image_url')
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('add_edit_lesson.html', form=form, course_set=course_set, lesson_item=lesson_item, title='Sửa Bài học')
    return render_template('add_edit_lesson.html', form=form, course_set=course_set, lesson_item=lesson_item, title='Sửa Bài học')

@courses_bp.route('/courses/<int:set_id>/lessons/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_lesson(set_id, item_id):
    """
    Xóa một bài học khỏi một bộ Khóa học cụ thể.

    Hàm này xử lý việc xóa một bài học.
    """
    course_set = LearningContainer.query.get_or_404(set_id)
    lesson_item = LearningItem.query.get_or_404(item_id)
    if current_user.user_role != 'admin' and \
       course_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        abort(403)
    db.session.delete(lesson_item)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Bài học đã được xóa.'})
    else:
        flash('Bài học đã được xóa.', 'success')
        return redirect(url_for('.list_lessons', set_id=set_id))

