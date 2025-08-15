# File: newmindstack/mindstack_app/modules/content_management/courses/routes.py
# Phiên bản: 6.8
# ĐÃ SỬA: Cập nhật hàm list_courses để hỗ trợ tìm kiếm theo trường cụ thể.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.orm.attributes import flag_modified
from ..forms import CourseForm, LessonForm
from ....models import db, LearningContainer, LearningItem, User, SystemSetting, ContainerContributor
from ....utils.pagination import get_pagination_data
from ....utils.search import apply_search_filter

courses_bp = Blueprint('content_management_courses', __name__,
                        template_folder='../templates/courses')

@courses_bp.before_request
@login_required 
def course_management_required():
    pass

@courses_bp.route('/')
@courses_bp.route('/sets')
def list_courses():
    """
    Hiển thị danh sách các khóa học, có hỗ trợ phân trang và tìm kiếm theo trường.
    """
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)

    base_query = LearningContainer.query.filter_by(container_type='COURSE')

    if current_user.user_role != 'admin':
        user_id = current_user.user_id
        created_courses_query = base_query.filter_by(creator_user_id=user_id)
        contributed_courses_query = base_query.join(ContainerContributor).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor'
        )
        base_query = created_courses_query.union(contributed_courses_query)

    search_field_map = {
        'title': LearningContainer.title,
        'description': LearningContainer.description,
        'tags': LearningContainer.tags
    }
    base_query = apply_search_filter(base_query, search_query, search_field_map, search_field)

    pagination = get_pagination_data(base_query.order_by(LearningContainer.created_at.desc()), page)
    courses = pagination.items

    for course_item in courses:
        course_item.item_count = db.session.query(LearningItem).filter_by(
            container_id=course_item.container_id,
            item_type='LESSON'
        ).count()

    template_vars = {
        'courses': courses, 
        'pagination': pagination, 
        'search_query': search_query,
        'search_field': search_field
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_courses_list.html', **template_vars)
    else:
        return render_template('courses.html', **template_vars)

@courses_bp.route('/sets/add', methods=['GET', 'POST'])
def add_course():
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
    course = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role != 'admin' and \
       course.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
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
    course = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role != 'admin' and course.creator_user_id != current_user.user_id:
        abort(403)
    
    LearningItem.query.filter_by(container_id=set_id).delete()
    db.session.delete(course)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Khóa học đã được xóa thành công!'})
    else:
        flash('Khóa học đã được xóa thành công!', 'success')
        return redirect(url_for('content_management.content_dashboard', tab='courses'))

@courses_bp.route('/sets/<int:set_id>/lessons')
def list_lessons(set_id):
    course = LearningContainer.query.get_or_404(set_id)

    if not course.is_public and \
       current_user.user_role != 'admin' and \
       course.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id).first():
        abort(403)
    
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)

    base_query = LearningItem.query.filter_by(
        container_id=set_id,
        item_type='LESSON'
    )

    if search_query:
        base_query = base_query.filter(LearningItem.content['title'].astext.ilike(f'%{search_query}%'))

    pagination = get_pagination_data(base_query.order_by(LearningItem.order_in_container), page)
    lessons = pagination.items

    can_edit = (current_user.user_role == 'admin' or \
       course.creator_user_id == current_user.user_id or \
       ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first())

    return render_template('lessons.html', 
                           course=course, 
                           lessons=lessons, 
                           can_edit=can_edit,
                           pagination=pagination,
                           search_query=search_query)

@courses_bp.route('/sets/<int:set_id>/lessons/add', methods=['GET', 'POST'])
def add_lesson(set_id):
    course = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role != 'admin' and \
       course.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
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
        
        flash('Bài học đã được thêm thành công!', 'success')
        return redirect(url_for('.list_lessons', set_id=set_id))

    return render_template('add_edit_lesson.html', form=form, title='Thêm Bài học mới', course=course)

@courses_bp.route('/sets/<int:set_id>/lessons/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_lesson(set_id, item_id):
    course = LearningContainer.query.get_or_404(set_id)
    lesson = LearningItem.query.get_or_404(item_id)

    if lesson.container_id != set_id or \
       (current_user.user_role != 'admin' and \
        course.creator_user_id != current_user.user_id and \
        not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first()):
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
        flag_modified(lesson, "content")
        
        db.session.commit()
        
        flash('Bài học đã được cập nhật thành công!', 'success')
        return redirect(url_for('.list_lessons', set_id=set_id))

    return render_template('add_edit_lesson.html', form=form, title='Sửa Bài học', course=course, lesson=lesson)

@courses_bp.route('/sets/<int:set_id>/lessons/delete/<int:item_id>', methods=['POST'])
def delete_lesson(set_id, item_id):
    course = LearningContainer.query.get_or_404(set_id)
    lesson = LearningItem.query.get_or_404(item_id)

    if lesson.container_id != set_id or \
       (current_user.user_role != 'admin' and \
        course.creator_user_id != current_user.user_id and \
        not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first()):
        abort(403)
    
    db.session.delete(lesson)
    db.session.commit()
    
    flash('Bài học đã được xóa thành công!', 'success')
    return redirect(url_for('.list_lessons', set_id=set_id))
