from flask import render_template, request, redirect, url_for, flash, abort, jsonify, current_app
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
            
    return render_dynamic_template('modules/content_management/flashcards/items/add_edit_flashcard_item.html', 
                           form=form, 
                           container=container,
                           title="Thêm thẻ mới",
                           image_base_folder=container.media_image_folder,
                           audio_base_folder=container.media_audio_folder,
                           regenerate_audio_url=url_for('vocab_flashcard.api_regenerate_audio_from_content'))

@blueprint.route('/flashcards/process_excel_info', methods=['POST'])
@login_required
def process_excel_info():
    """
    Process uploaded Excel file to extract info/metadata and analyze columns.
    """
    if 'excel_file' not in request.files:
         return jsonify({'success': False, 'message': 'Không tìm thấy file.'}), 400
         
    file = request.files['excel_file']
    if not file.filename:
        return jsonify({'success': False, 'message': 'Chưa chọn file.'}), 400

    try:
        import pandas as pd
        from ..logics.parsers import classify_columns, normalize_column_headers
        
        # Read Excel
        xls = pd.ExcelFile(file)
        sheet_names = xls.sheet_names
        
        # Determine Data Sheet
        data_sheet = sheet_names[0] # Default to first sheet
        if 'Data' in sheet_names: 
            data_sheet = 'Data'
            
        df = pd.read_excel(xls, sheet_name=data_sheet)
        raw_columns = [str(c).strip() for c in df.columns]

        # Metadata extraction from 'Info' sheet
        metadata = {}
        if 'Info' in sheet_names:
             try:
                 info_df = pd.read_excel(xls, sheet_name='Info')
                 # Try to find Key/Value pair columns case-insensitive
                 key_col = next((c for c in info_df.columns if str(c).lower() == 'key'), None)
                 val_col = next((c for c in info_df.columns if str(c).lower() == 'value'), None)
                 
                 if key_col and val_col:
                     for _, row in info_df.iterrows():
                         k = row[key_col]
                         v = row[val_col]
                         if pd.notna(k) and pd.notna(v):
                             metadata[str(k).strip()] = v
             except Exception as e:
                 current_app.logger.warning(f"Error reading Info sheet: {e}")

        # Normalize Columns
        mapping = normalize_column_headers(raw_columns)
        current_app.logger.info(f"Excel Column Mapping: {mapping}")
        df.rename(columns=mapping, inplace=True)
        columns = [str(c).strip() for c in df.columns]

        # Extended Standards for Quiz + Flashcards
        STANDARD_COLS = {
            'front', 'back', 'front_img', 'back_img', 'front_audio_url', 'back_audio_url', 
            'ai_explanation', 'image', 'audio', 'question', 'explanation', 
            'options', 'correct_answer', 'correct_option', 
            'pre_question_text', 'passage_text', 'audio_transcript',
            'option_a', 'option_b', 'option_c', 'option_d'
        }
        SYSTEM_COLS = {'item_id', 'action', 'container_id', 'order_in_container'}
        AI_COLS = {'ai_prompt'}

        # Smart Required Columns Detection
        required = ['front', 'back'] # Default Flashcard
        if 'question' in columns:
            required = ['question'] # Minimal Quiz Requirement
            # If strictly MCQ, maybe correct_answer? But let's be lenient for analysis
            if 'correct_answer' in columns:
                required.append('correct_answer')
        
        classification = classify_columns(columns, STANDARD_COLS, SYSTEM_COLS, AI_COLS, required_columns=required)
        
        return jsonify({
            'success': True,
            'message': 'Đã đọc thông tin từ file.',
            'data': {
                'data': metadata, 
                'column_analysis': {
                    'success': True,
                    'standard_columns': classification['standard'],
                    'missing_required': classification['missing_required'],
                    'all_columns': classification['all']
                }
            }
        })

    except Exception as e:
        current_app.logger.error(f"Excel Process Error: {e}")
        return jsonify({'success': False, 'message': f"Lỗi xử lý file: {str(e)}"}), 500

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

    return render_dynamic_template('modules/content_management/flashcards/items/add_edit_flashcard_item.html', 
                           form=form, 
                           container=item.container,
                           flashcard_item=item,
                           front_audio_url_resolved=front_audio_url_resolved,
                           back_audio_url_resolved=back_audio_url_resolved,
                           image_base_folder=item.container.media_image_folder,
                           audio_base_folder=item.container.media_audio_folder,
                           title="Chỉnh sửa thẻ",
                           regenerate_audio_url=url_for('vocab_flashcard.api_regenerate_audio_from_content'))

@blueprint.route('/flashcards/<int:set_id>/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_flashcard_item(set_id, item_id):
    if not has_container_access(set_id, 'editor'):
        abort(403)
    ContentKernelService.delete_item(item_id)
    flash("Đã xóa thẻ.", "success")
    return redirect(url_for('content_management.list_items', container_id=set_id))
