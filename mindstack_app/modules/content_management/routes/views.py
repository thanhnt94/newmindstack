# File: mindstack_app/modules/content_management/routes/views.py
from flask import render_template, request, redirect, url_for, flash, abort, current_app, jsonify
import json
from mindstack_app.utils.template_helpers import render_dynamic_template
from mindstack_app.utils.db_session import safe_commit
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from mindstack_app.models import db, LearningContainer, LearningItem, ContainerContributor, User, LearningGroup
from ..services.kernel_service import ContentKernelService
from mindstack_app.utils.pagination import get_pagination_data
from mindstack_app.utils.search import apply_search_filter
from mindstack_app.services.config_service import get_runtime_config
from mindstack_app.core.config import Config
from mindstack_app.modules.vocab_flashcard.services.flashcard_config_service import FlashcardConfigService
from mindstack_app.modules.quiz.services.quiz_config_service import QuizConfigService

from .. import blueprint
from ..forms import ContributorForm, CourseForm, LessonForm, FlashcardSetForm, FlashcardItemForm, QuizSetForm, QuizItemForm
from ..services.management_service import ManagementService
from ..logics.validators import has_container_access
from ..config import ContentManagementModuleDefaultConfig

@blueprint.route('/')
@login_required
def content_dashboard():
    """Hiển thị dashboard tổng quan về nội dung."""
    return render_dynamic_template('modules/content_management/index.html')

@blueprint.route('/<container_type>')
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

    if current_user.user_role != User.ROLE_ADMIN:
        user_id = current_user.user_id
        if current_user.user_role == User.ROLE_FREE:
            base_query = base_query.filter_by(creator_user_id=user_id)
        else:
            created_query = base_query.filter_by(creator_user_id=user_id)
            contributed_query = base_query.join(ContainerContributor).filter(
                ContainerContributor.user_id == user_id,
                ContainerContributor.permission_level == 'editor'
            )
            base_query = created_query.union(contributed_query)

    search_field_map = {
        'title': LearningContainer.title,
        'description': LearningContainer.description,
        'tags': LearningContainer.tags
    }
    base_query = apply_search_filter(base_query, search_query, search_field_map, search_field)

    pagination = get_pagination_data(base_query.order_by(LearningContainer.created_at.desc()), page)
    containers = pagination.items

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
        'search_field_map': search_field_map,
        'flashcard_config': FlashcardConfigService.get_all(),
        'quiz_config': QuizConfigService.get_all()
    }

    templates = {
        'COURSE': ('courses.html', '_courses_list.html'),
        'FLASHCARD_SET': ('flashcard_sets.html', '_flashcard_sets_list.html'),
        'QUIZ_SET': ('quiz_sets.html', '_quiz_sets_list.html')
    }
    
    type_slug = ContentManagementModuleDefaultConfig.TYPE_SLUG_MAP.get(container_type.upper(), container_type.lower())
    full_tpl, partial_tpl = templates.get(container_type, ('index.html', '_list.html'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_dynamic_template(f'modules/content_management/{type_slug}/sets/{partial_tpl}', **template_vars)
    else:
        return render_dynamic_template(f'modules/content_management/{type_slug}/sets/{full_tpl}', **template_vars)

def _get_form_for_type(container_type):
    forms = {
        'COURSE': CourseForm,
        'FLASHCARD_SET': FlashcardSetForm,
        'QUIZ_SET': QuizSetForm
    }
    return forms.get(container_type.upper())

@blueprint.route('/<container_type>/add', methods=['GET', 'POST'])
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
                ai_prompt=getattr(form, 'ai_prompt', None) and form.ai_prompt.data,
                media_image_folder=getattr(form, 'image_base_folder', None) and form.image_base_folder.data,
                media_audio_folder=getattr(form, 'audio_base_folder', None) and form.audio_base_folder.data
            )
            
            message = f'Đã tạo {container_type.lower()} mới thành công!'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': message, 'container_id': container.container_id})
                
            flash(message, 'success')
            return redirect(url_for('content_management.content_dashboard', tab=container_type.lower()))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi tạo: {str(e)}', 'danger')

    templates = {
        'COURSE': 'add_edit_course_set.html',
        'FLASHCARD_SET': 'add_edit_flashcard_set.html',
        'QUIZ_SET': 'add_edit_quiz_set.html'
    }
    type_slug = ContentManagementModuleDefaultConfig.TYPE_SLUG_MAP.get(container_type.upper(), container_type.lower())
    template = templates.get(container_type, 'add_edit.html')
    
    return render_dynamic_template(f'modules/content_management/{type_slug}/sets/{template}', 
                                   form=form, 
                                   title=f'Thêm {container_type}',
                                   available_keys=['front', 'back'],
                                   flashcard_config=FlashcardConfigService.get_all(),
                                   quiz_config=QuizConfigService.get_all())

@blueprint.route('/edit/<int:container_id>', methods=['GET', 'POST'])
@login_required
def edit_container(container_id):
    """Unified route to edit any container."""
    container = LearningContainer.query.get_or_404(container_id)
    if not has_container_access(container_id, 'editor'):
        abort(403)
        
    form_class = _get_form_for_type(container.container_type)
    form = form_class(obj=container)
    
    # [FIX] Manually populate media folder fields, AI capabilities, and settings - ONLY ON GET
    if request.method == 'GET':
        if hasattr(form, 'image_base_folder'):
            form.image_base_folder.data = container.media_image_folder
        if hasattr(form, 'audio_base_folder'):
            form.audio_base_folder.data = container.media_audio_folder
            
        # Map ai_capabilities list ['flashcard', 'quiz'] to supports_xxx checkboxes
        if container.ai_capabilities and isinstance(container.ai_capabilities, list):
            for cap in container.ai_capabilities:
                field_name = f'supports_{cap}'
                if hasattr(form, field_name):
                    getattr(form, field_name).data = True
                    
        # [NEW] Map display settings from settings JSON to form fields
        if container.settings and isinstance(container.settings, dict):
            display_fields = ['display_front_align', 'display_back_align', 'display_force_bold_front', 'display_force_bold_back']
            for field in display_fields:
                if field in container.settings and hasattr(form, field):
                    getattr(form, field).data = container.settings[field]
                    
        # [FIX] Ensure settings are JSON stringified for JS consumption - ONLY ON GET
        if hasattr(form, 'settings') and container.settings:
            form.settings.data = json.dumps(container.settings, ensure_ascii=False)
    
    # [NEW] Get available keys for column pairing (from existing items)
    available_keys = ['front', 'back']
    first_item = LearningItem.query.filter_by(container_id=container_id).first()
    if first_item and first_item.content:
        available_keys = list(first_item.content.keys())
    
    if hasattr(form, 'is_public') and current_user.user_role == User.ROLE_FREE:
        form.is_public.data = False
        form.is_public.render_kw = {'disabled': 'disabled'}

    if form.validate_on_submit():
        try:
            # 1. Collect basic fields
            update_data = {
                'title': form.title.data,
                'description': getattr(form, 'description', None) and form.description.data,
                'cover_image': getattr(form, 'cover_image', None) and form.cover_image.data,
                'tags': getattr(form, 'tags', None) and form.tags.data,
                'is_public': form.is_public.data if hasattr(form, 'is_public') else container.is_public,
                'ai_prompt': getattr(form, 'ai_prompt', None) and form.ai_prompt.data,
                'media_image_folder': getattr(form, 'image_base_folder', None) and form.image_base_folder.data,
                'media_audio_folder': getattr(form, 'audio_base_folder', None) and form.audio_base_folder.data
            }
            
            # 2. Collect AI Capabilities (supports_xxx checkboxes)
            capabilities = []
            possible_caps = [
                'supports_flashcard', 'supports_quiz', 'supports_writing', 
                'supports_matching', 'supports_speed', 'supports_listening',
                'supports_pronunciation', 'supports_essay', 'supports_speaking'
            ]
            for cap_field in possible_caps:
                field_obj = getattr(form, cap_field, None)
                if field_obj and field_obj.data:
                    # Strip 'supports_' to get the actual capability key
                    capabilities.append(cap_field.replace('supports_', ''))
            
            update_data['ai_capabilities'] = capabilities
            
            # 3. Parse and save Settings (from HiddenField + Display Fields)
            final_settings = container.settings.copy() if (container.settings and isinstance(container.settings, dict)) else {}
            
            if hasattr(form, 'settings') and form.settings.data:
                try:
                    js_settings = json.loads(form.settings.data)
                    if isinstance(js_settings, dict):
                        final_settings.update(js_settings)
                except Exception as json_err:
                    current_app.logger.warning(f"Failed to parse settings JSON: {json_err}")
            
            # Inject Display Settings into final_settings
            display_fields = ['display_front_align', 'display_back_align', 'display_force_bold_front', 'display_force_bold_back']
            for field in display_fields:
                if hasattr(form, field):
                    final_settings[field] = getattr(form, field).data
                    
            update_data['settings'] = final_settings
            
            # 4. Perform update
            ContentKernelService.update_container(container_id, **update_data)
            
            message = 'Đã cập nhật thành công!'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': message})
                
            flash(message, 'success')
            return redirect(url_for('content_management.content_dashboard', tab=ContentManagementModuleDefaultConfig.TYPE_SLUG_MAP.get(container.container_type.upper(), container.container_type.lower())))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Update error: {e}", exc_info=True)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': str(e)}), 500
            flash(f'Lỗi khi cập nhật: {str(e)}', 'danger')

    # [NEW] Handle validation errors for AJAX requests
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False, 
            'message': 'Dữ liệu không hợp lệ. Vui lòng kiểm tra lại các trường đỏ.',
            'errors': form.errors
        }), 400

    templates = {
        'COURSE': 'add_edit_course_set.html',
        'FLASHCARD_SET': 'add_edit_flashcard_set.html',
        'QUIZ_SET': 'add_edit_quiz_set.html'
    }
    type_slug = ContentManagementModuleDefaultConfig.TYPE_SLUG_MAP.get(container.container_type.upper(), container.container_type.lower())
    template = templates.get(container.container_type, 'add_edit.html')
    
    return render_dynamic_template(f'modules/content_management/{type_slug}/sets/{template}', 
                                   form=form, 
                                   title='Chỉnh sửa', 
                                   container=container,
                                   set_id=container_id,
                                   available_keys=available_keys,
                                   flashcard_config=FlashcardConfigService.get_all(),
                                   quiz_config=QuizConfigService.get_all())

@blueprint.route('/container/<int:container_id>/update-settings', methods=['POST'])
@login_required
def update_container_settings(container_id):
    """
    Dedicated endpoint for updating only the settings JSON via AJAX.
    Used by the 'Save Config' button in the configuration tab.
    """
    if not has_container_access(container_id, 'editor'):
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
    data = request.get_json()
    if not data or 'settings' not in data:
        return jsonify({'success': False, 'message': 'Invalid data'}), 400
        
    try:
        container = LearningContainer.query.get_or_404(container_id)
        # Merge new settings with existing ones to avoid losing display settings
        new_settings = data['settings']
        current_settings = container.settings.copy() if container.settings else {}
        current_settings.update(new_settings)
        
        ContentKernelService.update_container(container_id, settings=current_settings)
        return jsonify({'success': True, 'message': 'Đã lưu cấu hình thành công!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500



@blueprint.route('/container/<int:container_id>/items')
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
    
    pagination = get_pagination_data(base_query.order_by(LearningItem.order_in_container, LearningItem.item_id), page)
    items = pagination.items
    
    template_vars = {
        'container': container,
        'items': items,
        'pagination': pagination,
        'search_query': search_query,
        'flashcard_config': FlashcardConfigService.get_all(),
        'quiz_config': QuizConfigService.get_all(),
        'can_edit': has_container_access(container_id, 'editor')
    }
    
    templates = {
        'COURSE': ('lessons.html', 'lessons.html'),
        'FLASHCARD_SET': ('flashcard_items.html', 'flashcard_items.html'),
        'QUIZ_SET': ('quiz_items.html', 'quiz_items.html')
    }
    
    context_keys = {
        'COURSE': 'course',
        'FLASHCARD_SET': 'flashcard_set',
        'QUIZ_SET': 'quiz_set'
    }
    template_vars[context_keys[container.container_type]] = container
    template_vars['lessons'] = items if container.container_type == 'COURSE' else []
    template_vars['flashcard_items'] = items if container.container_type == 'FLASHCARD_SET' else []
    template_vars['quiz_items'] = items if container.container_type == 'QUIZ_SET' else []

    type_slug = ContentManagementModuleDefaultConfig.TYPE_SLUG_MAP.get(container.container_type.upper(), container.container_type.lower())
    full_tpl, partial_tpl = templates.get(container.container_type, ('index.html', '_list.html'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_dynamic_template(f'modules/content_management/{type_slug}/items/{partial_tpl}', **template_vars)
    else:
        return render_dynamic_template(f'modules/content_management/{type_slug}/items/{full_tpl}', **template_vars)

@blueprint.route('/manage_contributors/<int:container_id>', methods=['GET', 'POST'])
@login_required
def manage_contributors(container_id):
    """Quản lý người đóng góp cho một LearningContainer cụ thể."""
    container = LearningContainer.query.get_or_404(container_id)
    if container.creator and container.creator.user_role == User.ROLE_FREE:
        abort(403)

    if current_user.user_role != 'admin' and container.creator_user_id != current_user.user_id:
        abort(403)

    form = ContributorForm()

    if form.validate_on_submit():
        username_to_add = (form.username.data or "").strip()
        permission_level = form.permission_level.data

        user_to_add = User.query.filter(func.lower(User.username) == username_to_add.lower()).first()

        if user_to_add:
            existing = ContainerContributor.query.filter_by(container_id=container_id, user_id=user_to_add.user_id).first()
            if existing:
                existing.permission_level = permission_level
                db.session.commit()
                flash(f'Cấp độ quyền của {user_to_add.username} đã được cập nhật.', 'info')
            else:
                new_c = ContainerContributor(container_id=container_id, user_id=user_to_add.user_id, permission_level=permission_level)
                db.session.add(new_c)
                db.session.commit()
                flash(f'{user_to_add.username} đã được thêm làm người đóng góp!', 'success')
        
        return redirect(url_for('content_management.manage_contributors', container_id=container_id))

    contributors = db.session.query(ContainerContributor, User).join(User).filter(ContainerContributor.container_id == container_id).all()
    eligible_usernames = User.query.filter(~User.user_role.in_((User.ROLE_FREE, User.ROLE_ANONYMOUS))).order_by(User.username.asc()).with_entities(User.username).all()
    username_suggestions = [u for (u,) in eligible_usernames]

    return render_dynamic_template('modules/content_management/manage_contributors.html',
                           container=container,
                           contributors=contributors,
                           form=form,
                           username_suggestions=username_suggestions)

@blueprint.route('/container/<int:container_id>/add_item', methods=['GET', 'POST'])
@login_required
def add_item(container_id):
    """Unified route to add an item (Lesson or Quiz) to a container."""
    container = LearningContainer.query.get_or_404(container_id)
    if not has_container_access(container_id, 'editor'):
        abort(403)
        
    if container.container_type == 'FLASHCARD_SET':
        return redirect(url_for('.add_flashcard_item', set_id=container_id))
        
    # Handle Course (Lesson) and Quiz
    form_map = {
        'COURSE': LessonForm,
        'QUIZ_SET': QuizItemForm
    }
    form_class = form_map.get(container.container_type)
    if not form_class:
        abort(404)
        
    form = form_class()
    if form.validate_on_submit():
        try:
            # Process content based on form type
            content = {}
            item_type = ''
            if container.container_type == 'COURSE':
                item_type = 'LESSON'
                content = {
                    'title': form.title.data,
                    'content_html': form.content_html.data,
                    'estimated_time': form.estimated_time.data
                }
            elif container.container_type == 'QUIZ_SET':
                item_type = 'QUIZ_MCQ'
                content = {
                    'question': form.question.data,
                    'pre_question_text': form.pre_question_text.data,
                    'option_a': form.option_a.data,
                    'option_b': form.option_b.data,
                    'option_c': form.option_c.data,
                    'option_d': form.option_d.data,
                    'correct_answer_text': form.correct_answer_text.data,
                    'guidance': form.guidance.data,
                    'question_image_file': form.question_image_file.data,
                    'question_audio_file': form.question_audio_file.data
                }
                
            ContentKernelService.create_item(
                container_id=container_id,
                item_type=item_type,
                content=content,
                order=form.order_in_container.data or 0,
                ai_explanation=getattr(form, 'ai_explanation', None) and form.ai_explanation.data
            )
            flash('Đã thêm nội dung mới!', 'success')
            return redirect(url_for('.list_items', container_id=container_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi thêm: {str(e)}', 'danger')

    templates = {
        'COURSE': 'modules/content_management/courses/lessons/add_edit_lesson.html',
        'QUIZ_SET': 'modules/content_management/quizzes/items/add_edit_quiz_item.html'
    }
    template = templates.get(container.container_type)
    
    return render_dynamic_template(template, 
                                   form=form, 
                                   container=container,
                                   title="Thêm mới")

@blueprint.route('/container/<int:container_id>/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(container_id, item_id):
    """Unified route to edit an item (Lesson or Quiz)."""
    container = LearningContainer.query.get_or_404(container_id)
    item = LearningItem.query.get_or_404(item_id)
    if item.container_id != container_id:
        abort(404)
        
    if not has_container_access(container_id, 'editor'):
        abort(403)
        
    if container.container_type == 'FLASHCARD_SET':
        return redirect(url_for('.edit_flashcard_item', set_id=container_id, item_id=item_id))
        
    form_map = {
        'COURSE': LessonForm,
        'QUIZ_SET': QuizItemForm
    }
    form_class = form_map.get(container.container_type)
    
    # Pre-populate form
    form_data = item.content.copy()
    form_data['order_in_container'] = item.order_in_container
    form_data['ai_explanation'] = item.ai_explanation
    
    form = form_class(data=form_data)
    
    if form.validate_on_submit():
        try:
            content = {}
            if container.container_type == 'COURSE':
                content = {
                    'title': form.title.data,
                    'content_html': form.content_html.data,
                    'estimated_time': form.estimated_time.data
                }
            elif container.container_type == 'QUIZ_SET':
                content = {
                    'question': form.question.data,
                    'pre_question_text': form.pre_question_text.data,
                    'option_a': form.option_a.data,
                    'option_b': form.option_b.data,
                    'option_c': form.option_c.data,
                    'option_d': form.option_d.data,
                    'correct_answer_text': form.correct_answer_text.data,
                    'guidance': form.guidance.data,
                    'question_image_file': form.question_image_file.data,
                    'question_audio_file': form.question_audio_file.data
                }
                
            ContentKernelService.update_item(
                item_id,
                content=content,
                order=form.order_in_container.data,
                ai_explanation=getattr(form, 'ai_explanation', None) and form.ai_explanation.data
            )
            flash('Đã cập nhật thành công!', 'success')
            return redirect(url_for('.list_items', container_id=container_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi cập nhật: {str(e)}', 'danger')

    templates = {
        'COURSE': 'modules/content_management/courses/lessons/add_edit_lesson.html',
        'QUIZ_SET': 'modules/content_management/quizzes/items/add_edit_quiz_item.html'
    }
    template = templates.get(container.container_type)
    
    return render_dynamic_template(template, 
                                   form=form, 
                                   container=container,
                                   item=item,
                                   title="Chỉnh sửa")

@blueprint.route('/item/<int:item_id>/delete_confirm', methods=['POST'])
@login_required
def delete_item(item_id):
    """Unified route to delete an item."""
    item = LearningItem.query.get_or_404(item_id)
    container_id = item.container_id
    if not has_container_access(container_id, 'editor'):
        abort(403)
        
    ContentKernelService.delete_item(item_id)
    flash("Đã xóa thành công.", "success")
    return redirect(url_for('.list_items', container_id=container_id))

@blueprint.route('/container/<int:container_id>/export-excel')
@login_required
def export_container_excel(container_id):
    """
    Export container data to Excel using the specialized engine.
    """
    from flask import send_file
    from ..engine.excel_exporter import ExcelExporter
    
    container = LearningContainer.query.get_or_404(container_id)
    if not has_container_access(container_id, 'viewer'):
        abort(403)

    output, filename = ExcelExporter.export_container(container)

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )



