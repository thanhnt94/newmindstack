# File: newmindstack/mindstack_app/modules/content_management/routes.py
# Phiên bản: 2.2
# ĐÃ SỬA: Khắc phục lỗi 404 bằng cách loại bỏ url_prefix khi đăng ký các blueprint con.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, current_app
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from ...models import db, LearningContainer, ContainerContributor, User
from .forms import ContributorForm, CourseForm, LessonForm, FlashcardSetForm, FlashcardItemForm, QuizSetForm, QuizItemForm
from .services.management_service import ManagementService
from .logics.validators import has_container_access, can_create_public_content
from mindstack_app.services.content_kernel_service import ContentKernelService
from mindstack_app.core.error_handlers import error_response, success_response
from mindstack_app.utils.pagination import get_pagination_data
from mindstack_app.utils.search import apply_search_filter
from mindstack_app.utils.media_paths import build_relative_media_path

from werkzeug.utils import secure_filename
from uuid import uuid4
import os
from ...config import Config
from ...services.config_service import get_runtime_config

# Import legacy blueprints for now (to be removed once routes are ported)
from .courses.routes import courses_bp
from .flashcards.routes import flashcards_bp
from .quizzes.routes import quizzes_bp

# Định nghĩa Blueprint chính cho content_management
content_management_bp = Blueprint('content_management', __name__,
                                  template_folder='templates') # Vẫn giữ template_folder này cho các template chung

# Đăng ký các blueprint con
# ĐÃ SỬA: Loại bỏ url_prefix vì các routes con đã tự định nghĩa đường dẫn đầy đủ
content_management_bp.register_blueprint(courses_bp)
content_management_bp.register_blueprint(flashcards_bp)
content_management_bp.register_blueprint(quizzes_bp)


def _select_media_subdir(media_type: str) -> str:
    media_type = (media_type or 'file').lower()
    if media_type == 'image':
        return 'images'
    if media_type == 'media':
        return 'media'
    return 'files'


@content_management_bp.route('/media/upload', methods=['POST'])
@login_required
def upload_rich_text_media():
    """Tải file media sử dụng trong trình soạn thảo WYSIWYG."""

    if current_user.user_role == User.ROLE_FREE:
        return error_response('Tài khoản của bạn không có quyền tải media.', 'FORBIDDEN', 403)

    upload_root = get_runtime_config('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
    if not upload_root:
        current_app.logger.error('UPLOAD_FOLDER chưa được cấu hình.')
        return error_response('Máy chủ chưa cấu hình thư mục lưu trữ.', 'SERVER_ERROR', 500)

    if 'media_file' not in request.files:
        return error_response('Không tìm thấy file tải lên.', 'BAD_REQUEST', 400)

    file = request.files['media_file']
    if not file or file.filename == '':
        return error_response('Không có file nào được chọn.', 'BAD_REQUEST', 400)

    filename = secure_filename(file.filename)
    if not filename:
        return error_response('Tên file không hợp lệ.', 'BAD_REQUEST', 400)

    ext = os.path.splitext(filename)[1].lower()
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_RICH_TEXT_EXTENSIONS:
        return error_response(f'Định dạng file "{ext}" không được hỗ trợ.', 'BAD_REQUEST', 400)

    media_type = request.form.get('media_type', 'file')
    target_dir = os.path.join(upload_root, 'content', _select_media_subdir(media_type))
    os.makedirs(target_dir, exist_ok=True)

    base_name = os.path.splitext(filename)[0]
    candidate_name = f"{base_name}_{uuid4().hex[:8]}{ext}"
    candidate_path = os.path.join(target_dir, candidate_name)
    while os.path.exists(candidate_path):
        candidate_name = f"{base_name}_{uuid4().hex[:8]}{ext}"
        candidate_path = os.path.join(target_dir, candidate_name)

    try:
        file.save(candidate_path)
    except Exception as exc:  # pragma: no cover - phòng lỗi IO hiếm gặp
        current_app.logger.exception('Không thể lưu file media: %s', exc)
        return error_response('Không thể lưu file media trên máy chủ.', 'SERVER_ERROR', 500)

    relative_path = os.path.relpath(candidate_path, upload_root).replace('\\', '/')
    file_url = url_for('static', filename=relative_path, _external=False)

    return success_response(message='File uploaded successfully', data={'location': file_url, 'filename': candidate_name})


@content_management_bp.route('/cover/upload', methods=['POST'])
@login_required
def upload_cover_image():
    """Tải ảnh bìa cho Course/Set vào thư mục covers."""
    if 'cover_file' not in request.files:
        return error_response('Không tìm thấy file.', 'BAD_REQUEST', 400)
    
    file = request.files['cover_file']
    if not file or file.filename == '':
        return error_response('Chưa chọn file.', 'BAD_REQUEST', 400)

    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {'.jpg', '.jpeg', '.png', '.webp'}:
        return error_response('Định dạng ảnh không hỗ trợ.', 'BAD_REQUEST', 400)

    covers_root = current_app.config['COVERS_FOLDER']
    os.makedirs(covers_root, exist_ok=True)
    
    new_filename = f"cover_{uuid4().hex[:12]}{ext}"
    target_path = os.path.join(covers_root, new_filename)
    
    file.save(target_path)
    
    # Store relative path for DB: covers/filename
    db_path = f"covers/{new_filename}" 
    file_url = f"/media/{db_path}"
    
    return success_response(message='Đã tải ảnh bìa lên.', data={'url': file_url, 'db_path': db_path})


@content_management_bp.route('/')
@login_required
def content_dashboard():
    """
    Hiển thị dashboard tổng quan về nội dung.
    """
    return render_dynamic_template('pages/content_management/index.html')

# --- Unified Container Management ---

@content_management_bp.route('/<container_type>')
@login_required
def list_containers(container_type):
    """Unified listing for Courses, Flashcard Sets, and Quizzes."""
    container_type = container_type.upper()
    if container_type not in {'COURSE', 'FLASHCARD_SET', 'QUIZ_SET'}:
        abort(404)

    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)

    base_query = LearningContainer.query.filter_by(container_type=container_type)

    # Access control
    if current_user.user_role != User.ROLE_ADMIN:
        user_id = current_user.user_id
        if current_user.user_role == User.ROLE_FREE:
            base_query = base_query.filter_by(creator_user_id=user_id)
        else:
            # Paid users see their own and contributed sets
            created_query = base_query.filter_by(creator_user_id=user_id)
            contributed_query = base_query.join(ContainerContributor).filter(
                ContainerContributor.user_id == user_id,
                ContainerContributor.permission_level == 'editor'
            )
            base_query = created_query.union(contributed_query)

    # Search
    search_field_map = {
        'title': LearningContainer.title,
        'description': LearningContainer.description,
        'tags': LearningContainer.tags
    }
    base_query = apply_search_filter(base_query, search_query, search_field_map, search_field)

    pagination = get_pagination_data(base_query.order_by(LearningContainer.created_at.desc()), page)
    containers = pagination.items

    # Enrichment
    item_type_map = {'COURSE': 'LESSON', 'FLASHCARD_SET': 'FLASHCARD', 'QUIZ_SET': 'QUIZ_MCQ'}
    item_type = item_type_map.get(container_type)

    for c in containers:
        c.item_count = db.session.query(LearningItem).filter_by(
            container_id=c.container_id,
            item_type=item_type
        ).count()
        c.creator_display_name = c.creator.username if c.creator else "Unknown"

    template_vars = {
        'container_type': container_type,
        'containers': containers,
        'pagination': pagination,
        'search_query': search_query,
        'search_field': search_field,
        'search_field_map': search_field_map
    }

    # Template mapping
    templates = {
        'COURSE': ('courses.html', '_courses_list.html'),
        'FLASHCARD_SET': ('flashcard_sets.html', '_flashcard_sets_list.html'),
        'QUIZ_SET': ('quiz_sets.html', '_quiz_sets_list.html')
    }
    
    type_slug = container_type.lower().replace('_set', 's')
    full_tpl, partial_tpl = templates.get(container_type, ('index.html', '_list.html'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_dynamic_template(f'pages/content_management/{type_slug}/sets/{partial_tpl}', **template_vars)
    else:
        return render_dynamic_template(f'pages/content_management/{type_slug}/sets/{full_tpl}', **template_vars)

def _get_form_for_type(container_type):
    from .forms import CourseForm, FlashcardSetForm, QuizSetForm
    forms = {
        'COURSE': CourseForm,
        'FLASHCARD_SET': FlashcardSetForm,
        'QUIZ_SET': QuizSetForm
    }
    return forms.get(container_type.upper())

@content_management_bp.route('/<container_type>/add', methods=['GET', 'POST'])
@login_required
def add_container(container_type):
    """Unified route to add a new container."""
    container_type = container_type.upper()
    form_class = _get_form_for_type(container_type)
    if not form_class:
        abort(404)
        
    form = form_class()
    if hasattr(form, 'is_public') and current_user.user_role == User.ROLE_FREE:
        form.is_public.data = False
        form.is_public.render_kw = {'disabled': 'disabled'}

    if form.validate_on_submit():
        try:
            container = ContentKernelService.create_container(
                creator_id=current_user.user_id,
                container_type=container_type,
                title=form.title.data,
                description=getattr(form, 'description', None) and form.description.data,
                cover_image=getattr(form, 'cover_image', None) and form.cover_image.data,
                tags=getattr(form, 'tags', None) and form.tags.data,
                is_public=form.is_public.data if hasattr(form, 'is_public') else False,
                ai_prompt=getattr(form, 'ai_prompt', None) and form.ai_prompt.data
            )
            flash(f'Đã tạo {container_type.lower()} mới thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab=container_type.lower()))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi tạo: {str(e)}', 'danger')

    # Template mapping
    templates = {
        'COURSE': 'add_edit_course_set.html',
        'FLASHCARD_SET': 'add_edit_flashcard_set.html',
        'QUIZ_SET': 'add_edit_quiz_set.html'
    }
    type_slug = container_type.lower().replace('_set', 's')
    template = templates.get(container_type, 'add_edit.html')
    
    return render_dynamic_template(f'pages/content_management/{type_slug}/sets/{template}', form=form, title=f'Thêm {container_type}')

@content_management_bp.route('/edit/<int:container_id>', methods=['GET', 'POST'])
@login_required
def edit_container(container_id):
    """Unified route to edit any container."""
    container = LearningContainer.query.get_or_404(container_id)
    if not has_container_access(container_id, 'editor'):
        abort(403)
        
    form_class = _get_form_for_type(container.container_type)
    form = form_class(obj=container)
    
    if hasattr(form, 'is_public') and current_user.user_role == User.ROLE_FREE:
        form.is_public.data = False
        form.is_public.render_kw = {'disabled': 'disabled'}

    if form.validate_on_submit():
        try:
            ContentKernelService.update_container(
                container_id,
                title=form.title.data,
                description=getattr(form, 'description', None) and form.description.data,
                cover_image=getattr(form, 'cover_image', None) and form.cover_image.data,
                tags=getattr(form, 'tags', None) and form.tags.data,
                is_public=form.is_public.data if hasattr(form, 'is_public') else False,
                ai_prompt=getattr(form, 'ai_prompt', None) and form.ai_prompt.data
            )
            flash('Đã cập nhật thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab=container.container_type.lower()))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi cập nhật: {str(e)}', 'danger')

@content_management_bp.route('/container/<int:container_id>/delete', methods=['POST'])
@login_required
def delete_container_api(container_id):
    container = LearningContainer.query.get_or_404(container_id)
    if not has_container_access(container_id, 'editor'):
        abort(403)
    
    ContentKernelService.delete_container(container_id)
    return success_response(message="Xóa thành công", data={'container_id': container_id})

@content_management_bp.route('/item/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item_api(item_id):
    item = LearningItem.query.get_or_404(item_id)
    if not has_container_access(item.container_id, 'editor'):
        abort(403)
    
    container_id = item.container_id
    ContentKernelService.delete_item(item_id)
    return success_response(message="Xóa thành công", data={'item_id': item_id, 'container_id': container_id})

@content_management_bp.route('/item/<int:item_id>/move', methods=['POST'])
@login_required
def move_item(item_id):
    item = LearningItem.query.get_or_404(item_id)
    if not has_container_access(item.container_id, 'editor'):
        abort(403)
    
    target_container_id = request.form.get('target_set_id', type=int)
    if not target_container_id:
        return error_response("Thiếu target_set_id", "BAD_REQUEST", 400)
    
    if not has_container_access(target_container_id, 'editor'):
        return error_response("Không có quyền truy cập bộ đích", "FORBIDDEN", 403)
    
    # Simple move logic for now
    old_container_id = item.container_id
    item.container_id = target_container_id
    db.session.commit()
    
    return success_response(message="Di chuyển thành công", data={'item_id': item_id, 'old_container_id': old_container_id, 'new_container_id': target_container_id})


    # Template mapping
    templates = {
        'COURSE': 'add_edit_course_set.html',
        'FLASHCARD_SET': 'add_edit_flashcard_set.html',
        'QUIZ_SET': 'add_edit_quiz_set.html'
    }
    type_slug = container.container_type.lower().replace('_set', 's')
    template = templates.get(container.container_type, 'add_edit.html')
    
    return render_dynamic_template(f'pages/content_management/{type_slug}/sets/{template}', form=form, title='Chỉnh sửa', container=container)

@content_management_bp.route('/delete/<int:container_id>', methods=['POST'])
@login_required
def delete_container(container_id):
    """Unified route to delete any container."""
    container = LearningContainer.query.get_or_404(container_id)
    if container.creator_user_id != current_user.user_id and current_user.user_role != User.ROLE_ADMIN:
        abort(403)
        
    type_slug = container.container_type.lower()
    ContentKernelService.delete_container(container_id)
    flash('Đã xóa thành công!', 'success')
    return redirect(url_for('content_management.content_dashboard', tab=type_slug))

# --- Unified Item Management ---

@content_management_bp.route('/container/<int:container_id>/items')
@login_required
def list_items(container_id):
    """Unified listing of items within a container."""
    container = LearningContainer.query.get_or_404(container_id)
    if not has_container_access(container_id, 'viewer'):
        abort(403)
        
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    
    item_type_map = {'COURSE': 'LESSON', 'FLASHCARD_SET': 'FLASHCARD', 'QUIZ_SET': 'QUIZ_MCQ'}
    item_type = item_type_map.get(container.container_type)
    
    base_query = LearningItem.query.filter_by(container_id=container_id, item_type=item_type)
    
    if search_query:
        # Simplified search for now
        pass

    pagination = get_pagination_data(base_query.order_by(LearningItem.order_in_container, LearningItem.item_id), page)
    items = pagination.items
    
    template_vars = {
        'container': container,
        'items': items,
        'pagination': pagination,
        'search_query': search_query
    }
    
    # Template mapping
    templates = {
        'COURSE': ('lessons.html', 'lessons.html'), # Courses use same for both for now
        'FLASHCARD_SET': ('flashcard_items.html', 'flashcard_items.html'),
        'QUIZ_SET': ('quiz_items.html', 'quiz_items.html')
    }
    
    # Compatibility: templates expect 'flashcard_set' or 'course' or 'quiz_set'
    context_keys = {
        'COURSE': 'course',
        'FLASHCARD_SET': 'flashcard_set',
        'QUIZ_SET': 'quiz_set'
    }
    template_vars[context_keys[container.container_type]] = container
    template_vars['lessons'] = items if container.container_type == 'COURSE' else []
    template_vars['flashcard_items'] = items if container.container_type == 'FLASHCARD_SET' else []
    template_vars['quiz_items'] = items if container.container_type == 'QUIZ_SET' else []

    type_slug = container.container_type.lower().replace('_set', 's')
    full_tpl, partial_tpl = templates.get(container.container_type, ('index.html', '_list.html'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_dynamic_template(f'pages/content_management/{type_slug}/items/{partial_tpl}', **template_vars)
    else:
        return render_dynamic_template(f'pages/content_management/{type_slug}/items/{full_tpl}', **template_vars)

def _get_item_form_for_type(container_type):
    from .forms import LessonForm, FlashcardItemForm, QuizItemForm
    forms = {
        'COURSE': LessonForm,
        'FLASHCARD_SET': FlashcardItemForm,
        'QUIZ_SET': QuizItemForm
    }
    return forms.get(container_type.upper())

@content_management_bp.route('/container/<int:container_id>/items/add', methods=['GET', 'POST'])
@login_required
def add_item(container_id):
    """Unified route to add an item to a container."""
    container = LearningContainer.query.get_or_404(container_id)
    if not has_container_access(container_id, 'editor'):
        abort(403)
        
    form_class = _get_item_form_for_type(container.container_type)
    form = form_class()
    
    if form.validate_on_submit():
        content = {}
        if container.container_type == 'COURSE':
            content = {'title': form.title.data, 'content_html': form.content_html.data}
        elif container.container_type == 'FLASHCARD_SET':
            content = {
                'front': form.front.data, 
                'back': form.back.data,
                'front_audio_content': form.front_audio_content.data,
                'back_audio_content': form.back_audio_content.data,
                'front_img': form.front_img.data,
                'back_img': form.back_img.data
            }
        
        item_type_map = {'COURSE': 'LESSON', 'FLASHCARD_SET': 'FLASHCARD', 'QUIZ_SET': 'QUIZ_MCQ'}
        ManagementService.process_form_item(container_id, item_type_map[container.container_type], content)
        flash('Đã thêm mục mới!', 'success')
        return redirect(url_for('content_management.list_items', container_id=container_id))

    # Template mapping
    templates = {
        'COURSE': 'add_edit_lesson.html',
        'FLASHCARD_SET': 'add_edit_flashcard_item.html',
        'QUIZ_SET': 'add_edit_quiz_item.html'
    }
    type_slug = container.container_type.lower().replace('_set', 's')
    template = templates.get(container.container_type, 'add_edit.html')
    
    return render_dynamic_template(f'pages/content_management/{type_slug}/items/{template}', form=form, container=container, title='Thêm mục mới')

@content_management_bp.route('/item/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    """Unified route to edit any item."""
    item = LearningItem.query.get_or_404(item_id)
    container = item.container
    if not has_container_access(container.container_id, 'editor'):
        abort(403)
        
    form_class = _get_item_form_for_type(container.container_type)
    form = form_class(obj=item)
    
    if container.container_type == 'COURSE':
        form.title.data = item.content.get('title')
        form.content_html.data = item.content.get('content_html')
    elif container.container_type == 'FLASHCARD_SET':
        for field in ['front', 'back', 'front_audio_content', 'back_audio_content', 'front_img', 'back_img']:
            if hasattr(form, field):
                setattr(getattr(form, field), 'data', item.content.get(field))
    
    if form.validate_on_submit():
        content = {}
        if container.container_type == 'COURSE':
            content = {'title': form.title.data, 'content_html': form.content_html.data}
        elif container.container_type == 'FLASHCARD_SET':
            content = {
                'front': form.front.data, 
                'back': form.back.data,
                'front_audio_content': form.front_audio_content.data,
                'back_audio_content': form.back_audio_content.data,
                'front_img': form.front_img.data,
                'back_img': form.back_img.data
            }
            
        ManagementService.process_form_item(container.container_id, item.item_type, content, item_id=item_id)
        flash('Đã cập nhật thành công!', 'success')
        return redirect(url_for('content_management.list_items', container_id=container.container_id))

    # Template mapping
    templates = {
        'COURSE': 'add_edit_lesson.html',
        'FLASHCARD_SET': 'add_edit_flashcard_item.html',
        'QUIZ_SET': 'add_edit_quiz_item.html'
    }
    type_slug = container.container_type.lower().replace('_set', 's')
    template = templates.get(container.container_type, 'add_edit.html')
    
    return render_dynamic_template(f'pages/content_management/{type_slug}/items/{template}', form=form, container=container, item=item, title='Chỉnh sửa')

@content_management_bp.route('/item/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    """Unified route to delete any item."""
    item = LearningItem.query.get_or_404(item_id)
    container_id = item.container_id
    if not has_container_access(container_id, 'editor'):
        abort(403)
        
    ContentKernelService.delete_item(item_id)
    ManagementService.notify_content_change(item_id, 'deleted', container_id)
    flash('Đã xóa thành công!', 'success')
    return redirect(url_for('content_management.list_items', container_id=container_id))

@content_management_bp.route('/container/<int:container_id>/export')
@login_required
def export_container_excel(container_id):
    """Unified route to export container items to Excel."""
    from flask import send_file
    import io

    container = LearningContainer.query.get_or_404(container_id)
    if not has_container_access(container_id, 'viewer'):
        abort(403)
        
    item_type_map = {'COURSE': 'LESSON', 'FLASHCARD_SET': 'FLASHCARD', 'QUIZ_SET': 'QUIZ_MCQ'}
    item_type = item_type_map.get(container.container_type)
    
    items = LearningItem.query.filter_by(container_id=container_id, item_type=item_type)\
                             .order_by(LearningItem.order_in_container, LearningItem.item_id).all()
                             
    # Prepare data for Excel
    data = []
    for item in items:
        row = {'item_id': item.item_id, 'order_in_container': item.order_in_container}
        row.update(item.content or {})
        if item.custom_data:
            row.update(item.custom_data)
        data.append(row)
        
    df = pd.DataFrame(data)
    
    # Create Info sheet
    info_data = [
        ['title', container.title],
        ['description', container.description or ''],
        ['tags', container.tags or ''],
        ['container_type', container.container_type]
    ]
    
    if container.container_type == 'FLASHCARD_SET':
        folders = container.media_folders or {}
        info_data.append(['image_base_folder', folders.get('image', '')])
        info_data.append(['audio_base_folder', folders.get('audio', '')])
        
    df_info = pd.DataFrame(info_data, columns=['Key', 'Value'])
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
        df_info.to_excel(writer, index=False, sheet_name='Info')
        
    output.seek(0)
    filename = secure_filename(f"{container.title}_{container_id}.xlsx")
    
    return send_file(output, as_attachment=True, download_name=filename, 
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@content_management_bp.route('/container/<int:container_id>/import', methods=['GET', 'POST'])
@login_required
def import_container_excel(container_id):
    """Unified route to import container items from Excel."""
    container = LearningContainer.query.get_or_404(container_id)
    if not has_container_access(container_id, 'editor'):
        abort(403)
        
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            flash('Không tìm thấy file.', 'danger')
            return redirect(request.url)
            
        file = request.files['excel_file']
        if file.filename == '':
            flash('Chưa chọn file.', 'danger')
            return redirect(request.url)
            
        # Define column mapper based on type
        def get_mapper(c_type):
            from mindstack_app.utils.excel import get_cell_value
            if c_type == 'COURSE':
                def course_mapper(row, cols):
                    content = {
                        'title': get_cell_value(row, 'title', cols),
                        'content_html': get_cell_value(row, 'content_html', cols)
                    }
                    return content, None
                return course_mapper
            elif c_type == 'FLASHCARD_SET':
                def flashcard_mapper(row, cols):
                    content = {
                        'front': get_cell_value(row, 'front', cols),
                        'back': get_cell_value(row, 'back', cols)
                    }
                    # Handle optional URL fields
                    for f in ['front_img', 'back_img', 'front_audio_url', 'back_audio_url']:
                        val = get_cell_value(row, f, cols)
                        if val: content[f] = val
                    return content, ManagementService.build_custom_data(row, cols, {'front', 'back', 'front_img', 'back_img', 'front_audio_url', 'back_audio_url'})
                return flashcard_mapper
            return lambda r, c: ({}, None)

        item_type_map = {'COURSE': 'LESSON', 'FLASHCARD_SET': 'FLASHCARD', 'QUIZ_SET': 'QUIZ_MCQ'}
        item_type = item_type_map.get(container.container_type)
        
        try:
            stats = ManagementService.process_excel_import(
                container_id, item_type, file, get_mapper(container.container_type)
            )
            flash(f"Import thành công: {stats['created']} thêm mới, {stats['updated']} cập nhật, {stats['deleted']} xóa.", "success")
        except Exception as e:
            flash(f"Lỗi khi import: {str(e)}", "danger")
            
        return redirect(url_for('content_management.list_items', container_id=container_id))

    type_slug = container.container_type.lower().replace('_set', 's')
    return render_dynamic_template(f'pages/content_management/{type_slug}/excel/import_export.html', container=container)

@content_management_bp.route('/manage_contributors/<int:container_id>', methods=['GET', 'POST'])
@login_required
def manage_contributors(container_id):
    """
    Quản lý người đóng góp cho một LearningContainer cụ thể.
    """
    container = LearningContainer.query.get_or_404(container_id)
    creator = container.creator
    if creator and creator.user_role == User.ROLE_FREE:
        abort(403)

    if current_user.user_role != 'admin' and container.creator_user_id != current_user.user_id:
        abort(403)

    form = ContributorForm()

    if form.validate_on_submit():
        username_to_add = (form.username.data or "").strip()
        permission_level = form.permission_level.data

        if not username_to_add:
            flash('Vui lòng nhập tên người dùng.', 'danger')
            return redirect(url_for('content_management.manage_contributors', container_id=container_id))

        user_to_add = User.query.filter(func.lower(User.username) == username_to_add.lower()).first()

        if not user_to_add:
            flash(f'Không tìm thấy người dùng với tên: {username_to_add}.', 'danger')
        elif user_to_add.user_id == container.creator_user_id:
            flash('Không thể thêm chính người tạo làm người đóng góp.', 'warning')
        elif user_to_add.user_role in {User.ROLE_FREE, User.ROLE_ANONYMOUS}:
            flash('Không thể thêm tài khoản miễn phí hoặc ẩn danh làm người đóng góp.', 'danger')
        else:
            existing_contributor = ContainerContributor.query.filter_by(
                container_id=container_id,
                user_id=user_to_add.user_id
            ).first()

            if existing_contributor:
                existing_contributor.permission_level = permission_level
                db.session.commit()
                flash(f'Cấp độ quyền của {user_to_add.username} đã được cập nhật.', 'info')
            else:
                new_contributor = ContainerContributor(
                    container_id=container_id,
                    user_id=user_to_add.user_id,
                    permission_level=permission_level
                )
                db.session.add(new_contributor)
                db.session.commit()
                flash(f'{user_to_add.username} đã được thêm làm người đóng góp!', 'success')
        
        return redirect(url_for('content_management.manage_contributors', container_id=container_id))

    # Xử lý xóa người đóng góp (giữ nguyên logic cũ)
    if request.method == 'POST' and 'remove_contributor_id' in request.form:
        remove_id = request.form.get('remove_contributor_id')
        try:
            remove_id = int(remove_id)
            contributor_to_remove = ContainerContributor.query.filter_by(
                container_id=container_id,
                user_id=remove_id
            ).first()
            if contributor_to_remove:
                db.session.delete(contributor_to_remove)
                db.session.commit()
                flash(f'Người đóng góp đã bị xóa.', 'success')
            else:
                flash('Không tìm thấy người đóng góp này.', 'danger')
        except ValueError:
            flash('ID người đóng góp không hợp lệ.', 'danger')
        return redirect(url_for('content_management.manage_contributors', container_id=container_id))

    contributors = db.session.query(ContainerContributor, User).join(User).filter(
        ContainerContributor.container_id == container_id
    ).all()

    ineligible_roles = (User.ROLE_FREE, User.ROLE_ANONYMOUS)
    eligible_usernames = (
        User.query
        .filter(~User.user_role.in_(ineligible_roles))
        .order_by(User.username.asc())
        .with_entities(User.username)
        .all()
    )
    username_suggestions = [username for (username,) in eligible_usernames]

    return render_dynamic_template('pages/content_management/manage_contributors.html',
                           container=container,
                           contributors=contributors,
                           form=form,
                           username_suggestions=username_suggestions)

@content_management_bp.route('/api/contributors/<int:container_id>/add', methods=['POST'])
@login_required
def add_contributor_api(container_id):
    container = LearningContainer.query.get_or_404(container_id)
    if current_user.user_role != 'admin' and container.creator_user_id != current_user.user_id:
        return {'success': False, 'message': 'Permission denied'}, 403

    data = request.get_json() or {}
    username = (data.get('username') or "").strip()
    permission_level = data.get('permission_level', 'editor')

    if not username:
        return {'success': False, 'message': 'Vui lòng nhập tên người dùng'}, 400

    user_to_add = User.query.filter(func.lower(User.username) == username.lower()).first()

    if not user_to_add:
        return {'success': False, 'message': f'Không tìm thấy người dùng: {username}'}, 404
    if user_to_add.user_id == container.creator_user_id:
        return {'success': False, 'message': 'Không thể thêm người tạo'}, 400
    if user_to_add.user_role in {User.ROLE_FREE, User.ROLE_ANONYMOUS}:
        return {'success': False, 'message': 'Chỉ dành cho tài khoản trả phí'}, 400

    existing = ContainerContributor.query.filter_by(container_id=container_id, user_id=user_to_add.user_id).first()
    if existing:
        existing.permission_level = permission_level
        msg = f"Đã cập nhật quyền cho {user_to_add.username}"
    else:
        new_c = ContainerContributor(container_id=container_id, user_id=user_to_add.user_id, permission_level=permission_level)
        db.session.add(new_c)
        msg = f"Đã thêm {user_to_add.username}"
    
    db.session.commit()
    return {'success': True, 'message': msg, 'username': user_to_add.username, 'email': user_to_add.email, 'user_id': user_to_add.user_id}

@content_management_bp.route('/api/contributors/<int:container_id>/remove', methods=['POST'])
@login_required
def remove_contributor_api(container_id):
    container = LearningContainer.query.get_or_404(container_id)
    if current_user.user_role != 'admin' and container.creator_user_id != current_user.user_id:
        return {'success': False, 'message': 'Permission denied'}, 403

    data = request.get_json() or {}
    user_id = data.get('user_id')
    contributor = ContainerContributor.query.filter_by(container_id=container_id, user_id=user_id).first()
    if not contributor:
         return {'success': False, 'message': 'Không tìm thấy người đóng góp'}, 404

    db.session.delete(contributor)
    db.session.commit()
    return {'success': True, 'message': 'Đã xóa quyền'}

ALLOWED_RICH_TEXT_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp',
    '.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac',
    '.mp4', '.webm', '.mov', '.mkv', '.avi',
    '.pdf', '.docx', '.pptx', '.xlsx', '.zip', '.rar', '.txt'
}

