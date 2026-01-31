from flask import render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from mindstack_app.models import User, LearningContainer, LearningItem, db
from mindstack_app.utils.pagination import get_pagination_data
from mindstack_app.modules.content_management.forms import CourseForm, FlashcardSetForm, QuizSetForm
from mindstack_app.modules.content_management.services.kernel_service import ContentKernelService
from .. import blueprint

@blueprint.route('/content/', methods=['GET'])
@login_required
def content_dashboard():
    """
    Admin Content Dashboard.
    Overview of all content in the system.
    """
    if current_user.user_role != User.ROLE_ADMIN:
        flash('Permission denied', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    # Statistics
    stats = {
        'total_courses': LearningContainer.query.filter_by(container_type='COURSE').count(),
        'total_flashcards': LearningContainer.query.filter_by(container_type='FLASHCARD_SET').count(),
        'total_quizzes': LearningContainer.query.filter_by(container_type='QUIZ_SET').count(),
    }

    return render_template('admin/content/dashboard.html', stats=stats, active_page='content')

@blueprint.route('/content/list/<container_type>/', methods=['GET'])
@login_required
def list_content(container_type):
    if current_user.user_role != User.ROLE_ADMIN:
        flash('Permission denied', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    container_type = container_type.upper()
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '')

    query = LearningContainer.query.filter_by(container_type=container_type)
    
    if search:
        query = query.filter(LearningContainer.title.ilike(f'%{search}%'))

    pagination = get_pagination_data(query.order_by(LearningContainer.created_at.desc()), page)
    
    return render_template('admin/content/list.html', 
                           containers=pagination.items, 
                           pagination=pagination,
                           container_type=container_type,
                           active_page='content')

def _get_form_for_type(container_type):
    forms = {
        'COURSE': CourseForm,
        'FLASHCARD_SET': FlashcardSetForm,
        'QUIZ_SET': QuizSetForm
    }
    return forms.get(container_type.upper())

@blueprint.route('/content/edit/<int:container_id>', methods=['GET', 'POST'])
@login_required
def edit_content(container_id):
    if current_user.user_role != User.ROLE_ADMIN:
        flash('Permission denied', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    container = LearningContainer.query.get_or_404(container_id)
    form_class = _get_form_for_type(container.container_type)
    if not form_class:
        abort(404, description="Unknown container type")

    form = form_class(obj=container)
    
    if form.validate_on_submit():
        try:
            update_data = {
                'title': form.title.data,
                'description': getattr(form, 'description', None) and form.description.data,
                'cover_image': getattr(form, 'cover_image', None) and form.cover_image.data,
                'tags': getattr(form, 'tags', None) and form.tags.data,
                'is_public': getattr(form, 'is_public', None) and form.is_public.data,
                'ai_prompt': getattr(form, 'ai_prompt', None) and form.ai_prompt.data,
            }
            
            # Map media folders if present
            if hasattr(form, 'image_base_folder'):
                update_data['media_image_folder'] = form.image_base_folder.data
            if hasattr(form, 'audio_base_folder'):
                update_data['media_audio_folder'] = form.audio_base_folder.data

            ContentKernelService.update_container(container_id, **update_data)
            
            flash('Đã cập nhật thành công!', 'success')
            return redirect(url_for('admin.list_content', container_type=container.container_type.lower()))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi cập nhật: {str(e)}', 'danger')

    return render_template('admin/content/edit.html', form=form, container=container, active_page='content')