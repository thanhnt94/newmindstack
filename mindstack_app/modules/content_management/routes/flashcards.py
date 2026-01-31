from flask import render_template, request, redirect, url_for, flash, abort, jsonify
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from mindstack_app.models import db, LearningContainer, LearningItem
from ..services.kernel_service import ContentKernelService
from ..forms import FlashcardItemForm
from ..logics.validators import has_container_access
from .. import blueprint

@blueprint.route('/flashcards/<int:set_id>/add', methods=['GET', 'POST'])
@login_required
def add_flashcard_item(set_id):
    container = LearningContainer.query.get_or_404(set_id)
    if not has_container_access(set_id, 'editor'):
        abort(403)
        
    form = FlashcardItemForm()
    if form.validate_on_submit():
        try:
            ContentKernelService.create_item(
                container_id=set_id,
                item_type='FLASHCARD',
                content={
                    'front': form.front.data,
                    'back': form.back.data,
                    'front_img': form.front_img.data,
                    'back_img': form.back_img.data,
                    'front_audio_content': form.front_audio_content.data,
                    'front_audio_url': form.front_audio_url.data,
                    'back_audio_content': form.back_audio_content.data,
                    'back_audio_url': form.back_audio_url.data
                },
                order=form.order_in_container.data or 0,
                ai_explanation=form.ai_explanation.data
            )
            flash('Đã thêm thẻ mới!', 'success')
            return redirect(url_for('content_management.list_items', container_id=set_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi thêm: {str(e)}', 'danger')
            
    return render_dynamic_template('pages/content_management/flashcards/items/add_edit_flashcard_item.html', 
                           form=form, 
                           container=container,
                           title="Thêm thẻ mới",
                           image_base_folder=container.media_image_folder,
                           audio_base_folder=container.media_audio_folder,
                           regenerate_audio_url=url_for('vocab_flashcard.flashcard_learning.regenerate_audio_from_content'))

@blueprint.route('/flashcards/process_excel_info', methods=['POST'])
@login_required
def process_excel_info():
    """
    Process uploaded Excel file to extract info/metadata (not full import yet).
    This is a stub implementation to fix BuildError.
    """
    # TODO: Implement actual Excel processing logic
    return jsonify({'success': False, 'message': 'Not implemented yet'}), 501

@blueprint.route('/flashcards/<int:set_id>/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_flashcard_item(set_id, item_id):
    item = LearningItem.query.get_or_404(item_id)
    if item.container_id != set_id:
        abort(404)
        
    if not has_container_access(set_id, 'editor'):
        abort(403)
        
    form = FlashcardItemForm(data={
        'front': item.content.get('front'),
        'back': item.content.get('back'),
        'front_img': item.content.get('front_img'),
        'back_img': item.content.get('back_img'),
        'front_audio_content': item.content.get('front_audio_content'),
        'front_audio_url': item.content.get('front_audio_url'),
        'back_audio_content': item.content.get('back_audio_content'),
        'back_audio_url': item.content.get('back_audio_url'),
        'ai_explanation': item.ai_explanation,
        'order_in_container': item.order_in_container
    })
    
    if form.validate_on_submit():
        try:
            ContentKernelService.update_item(
                item_id,
                content={
                    'front': form.front.data,
                    'back': form.back.data,
                    'front_img': form.front_img.data,
                    'back_img': form.back_img.data,
                    'front_audio_content': form.front_audio_content.data,
                    'front_audio_url': form.front_audio_url.data,
                    'back_audio_content': form.back_audio_content.data,
                    'back_audio_url': form.back_audio_url.data
                },
                order=form.order_in_container.data,
                ai_explanation=form.ai_explanation.data
            )
            flash('Đã cập nhật thẻ!', 'success')
            return redirect(url_for('content_management.list_items', container_id=set_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi cập nhật: {str(e)}', 'danger')

    # Resolve audio URLs for the player
    from mindstack_app.utils.media_paths import build_relative_media_path
    
    front_audio_url_resolved = ""
    if item.content.get('front_audio_url'):
        front_audio_url_resolved = url_for('media_uploads', filename=build_relative_media_path(item.content.get('front_audio_url'), item.container.media_audio_folder))

    back_audio_url_resolved = ""
    if item.content.get('back_audio_url'):
        back_audio_url_resolved = url_for('media_uploads', filename=build_relative_media_path(item.content.get('back_audio_url'), item.container.media_audio_folder))

    return render_dynamic_template('pages/content_management/flashcards/items/add_edit_flashcard_item.html', 
                           form=form, 
                           container=item.container,
                           flashcard_item=item,
                           front_audio_url_resolved=front_audio_url_resolved,
                           back_audio_url_resolved=back_audio_url_resolved,
                           image_base_folder=item.container.media_image_folder,
                           audio_base_folder=item.container.media_audio_folder,
                           title="Chỉnh sửa thẻ",
                           regenerate_audio_url=url_for('vocab_flashcard.flashcard_learning.regenerate_audio_from_content'))

@blueprint.route('/flashcards/<int:set_id>/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_flashcard_item(set_id, item_id):
    if not has_container_access(set_id, 'editor'):
        abort(403)
    ContentKernelService.delete_item(item_id)
    flash("Đã xóa thẻ.", "success")
    return redirect(url_for('content_management.list_items', container_id=set_id))
