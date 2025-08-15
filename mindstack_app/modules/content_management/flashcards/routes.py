# File: newmindstack/mindstack_app/modules/content_management/flashcards/routes.py
# Phiên bản: 4.2
# ĐÃ SỬA: Cập nhật hàm list_flashcard_sets để hỗ trợ tìm kiếm theo trường cụ thể.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.orm.attributes import flag_modified
from ..forms import FlashcardSetForm, FlashcardItemForm
from ....models import db, LearningContainer, LearningItem, ContainerContributor, User
import pandas as pd
import tempfile
import os
from ....utils.pagination import get_pagination_data
from ....utils.search import apply_search_filter

flashcards_bp = Blueprint('content_management_flashcards', __name__,
                            template_folder='../templates/flashcards')

@flashcards_bp.route('/flashcards/process_excel_info', methods=['POST'])
@login_required
def process_excel_info():
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
            current_app.logger.error(f"Lỗi khi xử lý sheet Info (Flashcard): {e}")
            return jsonify({'success': False, 'message': f'Lỗi đọc file Excel: {e}'}), 500
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
    return jsonify({'success': False, 'message': 'File không hợp lệ. Vui lòng chọn file .xlsx'}), 400

@flashcards_bp.route('/flashcards')
@login_required
def list_flashcard_sets():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)

    base_query = LearningContainer.query.filter_by(container_type='FLASHCARD_SET')

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
    flashcard_sets = pagination.items

    for set_item in flashcard_sets:
        set_item.item_count = db.session.query(LearningItem).filter_by(
            container_id=set_item.container_id,
            item_type='FLASHCARD'
        ).count()

    template_vars = {
        'flashcard_sets': flashcard_sets, 
        'pagination': pagination, 
        'search_query': search_query,
        'search_field': search_field
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_flashcard_sets_list.html', **template_vars)
    else:
        return render_template('flashcard_sets.html', **template_vars)

@flashcards_bp.route('/flashcards/add', methods=['GET', 'POST'])
@login_required
def add_flashcard_set():
    form = FlashcardSetForm()
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        temp_filepath = None
        try:
            new_set = LearningContainer(
                creator_user_id=current_user.user_id,
                container_type='FLASHCARD_SET',
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
                required_cols = ['front', 'back']
                if not all(col in df.columns for col in required_cols):
                    raise ValueError(f"File Excel (sheet 'Data') phải có các cột bắt buộc: {', '.join(required_cols)}.")
                items_added_count = 0
                for index, row in df.iterrows():
                    front_content = str(row['front']) if pd.notna(row['front']) else ''
                    back_content = str(row['back']) if pd.notna(row['back']) else ''
                    if front_content and back_content:
                        item_content = {'front': front_content, 'back': back_content}
                        optional_cols = ['front_audio_content', 'back_audio_content', 'front_img', 'back_img', 'ai_explanation']
                        for col in optional_cols:
                            if col in df.columns and pd.notna(row[col]):
                                item_content[col] = str(row[col])
                        new_item = LearningItem(
                            container_id=new_set.container_id,
                            item_type='FLASHCARD',
                            content=item_content,
                            order_in_container=index + 1
                        )
                        db.session.add(new_item)
                        items_added_count += 1
                flash_message = f'Bộ thẻ và {items_added_count} thẻ từ Excel đã được tạo thành công!'
                flash_category = 'success'
            else:
                flash_message = 'Bộ thẻ mới đã được tạo thành công!'
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
            return redirect(url_for('content_management.content_dashboard', tab='flashcards'))
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_flashcard_set_bare.html', form=form, title='Thêm Bộ thẻ ghi nhớ')
    return render_template('add_edit_flashcard_set.html', form=form, title='Thêm Bộ thẻ ghi nhớ')

@flashcards_bp.route('/flashcards/edit/<int:set_id>', methods=['GET', 'POST'])
@login_required
def edit_flashcard_set(set_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and \
       flashcard_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        abort(403)
    form = FlashcardSetForm(obj=flashcard_set)
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        temp_filepath = None
        try:
            flashcard_set.title = form.title.data
            flashcard_set.description = form.description.data
            flashcard_set.tags = form.tags.data
            flashcard_set.is_public = form.is_public.data
            flashcard_set.ai_settings = {'custom_prompt': form.ai_prompt.data} if form.ai_prompt.data else None
            if form.excel_file.data and form.excel_file.data.filename != '':
                excel_file = form.excel_file.data
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    excel_file.save(tmp_file.name)
                    temp_filepath = tmp_file.name
                df = pd.read_excel(temp_filepath, sheet_name='Data')
                required_cols = ['front', 'back']
                if not all(col in df.columns for col in required_cols):
                    raise ValueError(f"File Excel (sheet 'Data') phải có các cột bắt buộc: {', '.join(required_cols)}.")
                LearningItem.query.filter_by(container_id=set_id, item_type='FLASHCARD').delete()
                db.session.flush()
                for index, row in df.iterrows():
                    front_content = str(row['front']) if pd.notna(row['front']) else ''
                    back_content = str(row['back']) if pd.notna(row['back']) else ''
                    if front_content and back_content:
                        item_content = {'front': front_content, 'back': back_content}
                        optional_cols = ['front_audio_content', 'back_audio_content', 'front_img', 'back_img', 'ai_explanation']
                        for col in optional_cols:
                            if col in df.columns and pd.notna(row[col]):
                                item_content[col] = str(row[col])
                        new_item = LearningItem(
                            container_id=set_id,
                            item_type='FLASHCARD',
                            content=item_content,
                            order_in_container=index + 1
                        )
                        db.session.add(new_item)
                flash_message = 'Bộ thẻ và các thẻ từ Excel đã được cập nhật!'
                flash_category = 'success'
            else:
                flash_message = 'Bộ thẻ đã được cập nhật!'
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
            return redirect(url_for('content_management.content_dashboard', tab='flashcards'))
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_flashcard_set_bare.html', form=form, title='Chỉnh sửa Bộ thẻ ghi nhớ')
    return render_template('add_edit_flashcard_set.html', form=form, title='Chỉnh sửa Bộ thẻ ghi nhớ')

@flashcards_bp.route('/flashcards/delete/<int:set_id>', methods=['POST'])
@login_required
def delete_flashcard_set(set_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and flashcard_set.creator_user_id != current_user.user_id:
        abort(403)
    db.session.delete(flashcard_set)
    db.session.commit()
    flash('Bộ thẻ đã được xóa thành công!', 'success')
    return redirect(url_for('content_management.content_dashboard', tab='flashcards'))

@flashcards_bp.route('/flashcards/<int:set_id>/items')
@login_required
def list_flashcard_items(set_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    if not flashcard_set.is_public and \
       current_user.user_role != 'admin' and \
       flashcard_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id).first():
        abort(403)
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    base_query = LearningItem.query.filter_by(
        container_id=flashcard_set.container_id,
        item_type='FLASHCARD'
    )
    search_fields = [LearningItem.content['front'], LearningItem.content['back']]
    base_query = apply_search_filter(base_query, search_query, search_fields)
    pagination = get_pagination_data(base_query.order_by(LearningItem.order_in_container), page)
    flashcard_items = pagination.items
    can_edit = (current_user.user_role == 'admin' or \
       flashcard_set.creator_user_id == current_user.user_id or \
       ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first())
    return render_template('flashcard_items.html', flashcard_set=flashcard_set, flashcard_items=flashcard_items, can_edit=can_edit, pagination=pagination, search_query=search_query)

@flashcards_bp.route('/flashcards/<int:set_id>/items/add', methods=['GET', 'POST'])
@login_required
def add_flashcard_item(set_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and \
       flashcard_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        abort(403)
    form = FlashcardItemForm()
    if form.validate_on_submit():
        max_order = db.session.query(db.func.max(LearningItem.order_in_container)).filter_by(
            container_id=set_id,
            item_type='FLASHCARD'
        ).scalar()
        new_order = (max_order or 0) + 1
        new_item = LearningItem(
            container_id=set_id,
            item_type='FLASHCARD',
            content={
                'front': form.front.data, 'back': form.back.data,
                'front_audio_content': form.front_audio_content.data,
                'front_audio_url': form.front_audio_url.data,
                'back_audio_content': form.back_audio_content.data,
                'back_audio_url': form.back_audio_url.data,
                'front_img': form.front_img.data,
                'back_img': form.back_img.data,
            },
            order_in_container=new_order
        )
        db.session.add(new_item)
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Thẻ mới đã được thêm!'})
        else:
            flash('Thẻ mới đã được thêm!', 'success')
            return redirect(url_for('.list_flashcard_items', set_id=set_id))
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_flashcard_item_bare.html', form=form, flashcard_set=flashcard_set, title='Thêm Thẻ')
    return render_template('add_edit_flashcard_item.html', form=form, flashcard_set=flashcard_set, title='Thêm Thẻ')

@flashcards_bp.route('/flashcards/<int:set_id>/items/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_flashcard_item(set_id, item_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    flashcard_item = LearningItem.query.filter_by(item_id=item_id, container_id=set_id).first_or_404()
    if current_user.user_role != 'admin' and \
       flashcard_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        abort(403)
    form = FlashcardItemForm(obj=flashcard_item.content)
    if form.validate_on_submit():
        flashcard_item.content['front'] = form.front.data
        flashcard_item.content['back'] = form.back.data
        flashcard_item.content['front_audio_content'] = form.front_audio_content.data
        flashcard_item.content['front_audio_url'] = form.front_audio_url.data
        flashcard_item.content['back_audio_content'] = form.back_audio_content.data
        flashcard_item.content['back_audio_url'] = form.back_audio_url.data
        flashcard_item.content['front_img'] = form.front_img.data
        flashcard_item.content['back_img'] = form.back_img.data
        flag_modified(flashcard_item, "content")
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Thẻ đã được cập nhật!'})
        else:
            flash('Thẻ đã được cập nhật!', 'success')
            return redirect(url_for('.list_flashcard_items', set_id=set_id))
    if request.method == 'GET':
        form.front.data = flashcard_item.content.get('front')
        form.back.data = flashcard_item.content.get('back')
        form.front_audio_content.data = flashcard_item.content.get('front_audio_content')
        form.front_audio_url.data = flashcard_item.content.get('front_audio_url')
        form.back_audio_content.data = flashcard_item.content.get('back_audio_content')
        form.back_audio_url.data = flashcard_item.content.get('back_audio_url')
        form.front_img.data = flashcard_item.content.get('front_img')
        form.back_img.data = flashcard_item.content.get('back_img')
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_flashcard_item_bare.html', form=form, flashcard_set=flashcard_set, flashcard_item=flashcard_item, title='Sửa Thẻ')
    return render_template('add_edit_flashcard_item.html', form=form, flashcard_set=flashcard_set, flashcard_item=flashcard_item, title='Sửa Thẻ')

@flashcards_bp.route('/flashcards/<int:set_id>/items/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_flashcard_item(set_id, item_id):
    flashcard_set = LearningContainer.query.get_or_404(set_id)
    flashcard_item = LearningItem.query.filter_by(item_id=item_id, container_id=set_id).first_or_404()
    if current_user.user_role != 'admin' and \
       flashcard_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        abort(403)
    db.session.delete(flashcard_item)
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Thẻ đã được xóa.'})
    else:
        flash('Thẻ đã được xóa.', 'success')
        return redirect(url_for('.list_flashcard_items', set_id=set_id))
