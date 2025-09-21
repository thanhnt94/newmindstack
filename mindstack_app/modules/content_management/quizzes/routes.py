# File: newmindstack/mindstack_app/modules/content_management/quizzes/routes.py
# Phiên bản: 3.36
# MỤC ĐÍCH: Tích hợp quyền chỉnh sửa vào QuizSession.
# ĐÃ SỬA: Sửa đổi route list_quiz_items để hiển thị đúng nút Sửa.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.orm.attributes import flag_modified
from ..forms import QuizSetForm, QuizItemForm
from ....models import db, LearningContainer, LearningItem, LearningGroup, ContainerContributor, User
import pandas as pd
import tempfile
import os
from ....modules.shared.utils.pagination import get_pagination_data
from ....modules.shared.utils.search import apply_search_filter

quizzes_bp = Blueprint('content_management_quizzes', __name__,
                        template_folder='templates') # Đã cập nhật đường dẫn template


def _apply_is_public_restrictions(form):
    """Disable public toggle for free users and ensure value stays False."""
    if hasattr(form, 'is_public') and current_user.user_role == 'free':
        form.is_public.data = False
        existing_render_kw = dict(form.is_public.render_kw or {})
        existing_render_kw['disabled'] = True
        form.is_public.render_kw = existing_render_kw

def _process_relative_url(url):
    """
    Mô tả: Tiền xử lý URL tương đối, thêm 'uploads/' nếu cần.
    Args:
        url (str): URL ban đầu.
    Returns:
        str: URL đã được tiền xử lý.
    """
    if url and not url.startswith(('http://', 'https://', '/')):
        return f'uploads/{url}'
    return url

@quizzes_bp.route('/quizzes/process_excel_info', methods=['POST'])
@login_required
def process_excel_info():
    """
    Xử lý file Excel được tải lên để trích xuất thông tin từ sheet 'Info'.
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
            current_app.logger.error(f"Lỗi khi xử lý sheet Info: {e}")
            return jsonify({'success': False, 'message': f'Lỗi đọc file Excel: {e}'}), 500
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
    return jsonify({'success': False, 'message': 'File không hợp lệ. Vui lòng chọn file .xlsx'}), 400

@quizzes_bp.route('/quizzes')
@login_required
def list_quiz_sets():
    """
    Hiển thị danh sách các bộ Quiz.
    """
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)

    base_query = LearningContainer.query.filter_by(container_type='QUIZ_SET')
    
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
    
    filtered_query = apply_search_filter(base_query, search_query, search_field_map, search_field)

    pagination = get_pagination_data(filtered_query.order_by(LearningContainer.created_at.desc()), page)
    quiz_sets = pagination.items
    
    for set_item in quiz_sets:
        set_item.item_count = db.session.query(LearningItem).filter_by(
            container_id=set_item.container_id,
            item_type='QUIZ_MCQ'
        ).count()

    template_vars = {
        'quiz_sets': quiz_sets, 
        'pagination': pagination, 
        'search_query': search_query,
        'search_field': search_field,
        'search_field_map': search_field_map
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_quiz_sets_list.html', **template_vars)
    else:
        return render_template('quiz_sets.html', **template_vars)

@quizzes_bp.route('/quizzes/add', methods=['GET', 'POST'])
@login_required
def add_quiz_set():
    """
    Thêm một bộ Quiz mới.
    """
    form = QuizSetForm()
    _apply_is_public_restrictions(form)
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        temp_filepath = None
        try:
            new_set = LearningContainer(
                creator_user_id=current_user.user_id,
                container_type='QUIZ_SET',
                title=form.title.data,
                description=form.description.data,
                tags=form.tags.data,
                is_public=False if current_user.user_role == 'free' else form.is_public.data,
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
                group_cache = {}
                items_added_count = 0
                for index, row in df.iterrows():
                    group_passage_text = None
                    group_audio_file = None
                    group_image_file = None

                    passage_order = str(row['passage_order']) if 'passage_order' in df.columns and pd.notna(row['passage_order']) else None
                    group_db_id = None
                    group_content = {}
                    group_type = ''

                    if passage_order:
                        group_passage_text = str(row['passage_text']) if 'passage_text' in df.columns and pd.notna(row['passage_text']) else None
                        group_audio_file = str(row['group_audio_file']) if 'group_audio_file' in df.columns and pd.notna(row['group_audio_file']) else None
                        group_image_file = str(row['group_image_file']) if 'group_image_file' in df.columns and pd.notna(row['group_image_file']) else None
                        
                        group_key = None
                        if group_passage_text:
                            group_key = group_passage_text
                            group_content['passage_text'] = group_passage_text
                            group_type = 'PASSAGE'
                        
                        if group_audio_file:
                            group_key = group_audio_file
                            group_content['question_audio_file'] = group_audio_file
                            group_type = 'AUDIO'
                        
                        if group_image_file:
                            group_key = group_image_file
                            group_content['question_image_file'] = group_image_file
                            group_type = 'IMAGE'

                        if group_key and group_key not in group_cache:
                            new_group = LearningGroup(
                                container_id=new_set.container_id,
                                group_type=group_type,
                                content=group_content
                            )
                            db.session.add(new_group)
                            db.session.flush()
                            group_cache[group_key] = new_group.group_id
                            group_db_id = new_group.group_id
                        elif group_key:
                            group_db_id = group_cache[group_key]

                    option_a = str(row['option_a']) if 'option_a' in df.columns and pd.notna(row['option_a']) else None
                    option_b = str(row['option_b']) if 'option_b' in df.columns and pd.notna(row['option_b']) else None
                    correct_answer = str(row['correct_answer_text']) if 'correct_answer_text' in df.columns and pd.notna(row['correct_answer_text']) else None
                    if not (option_a and option_b and correct_answer):
                        current_app.logger.warning(f"Bỏ qua hàng {index + 2} trong Excel: Thiếu thông tin cốt lõi (option_a, option_b, correct_answer_text).")
                        continue

                    question_text = str(row['question']) if 'question' in df.columns and pd.notna(row['question']) else ''
                    
                    item_image_file = str(row['question_image_file']) if 'question_image_file' in df.columns and pd.notna(row['question_image_file']) else None
                    item_audio_file = str(row['question_audio_file']) if 'question_audio_file' in df.columns and pd.notna(row['question_audio_file']) else None
                    
                    item_ai_prompt = str(row['ai_prompt']) if 'ai_prompt' in df.columns and pd.notna(row['ai_prompt']) else None

                    item_content = {
                        'question': question_text,
                        'options': {
                            'A': option_a, 'B': option_b,
                            'C': str(row['option_c']) if 'option_c' in df.columns and pd.notna(row['option_c']) else None,
                            'D': str(row['option_d']) if 'option_d' in df.columns and pd.notna(row['option_d']) else None
                        },
                        'correct_answer': correct_answer,
                        'explanation': str(row['guidance']) if 'guidance' in df.columns and pd.notna(row['guidance']) else None,
                        'pre_question_text': str(row['pre_question_text']) if 'pre_question_text' in df.columns and pd.notna(row['pre_question_text']) else None,
                        'passage_text': str(row['passage_text']) if 'passage_text' in df.columns and pd.notna(row['passage_text']) else None,
                        'passage_order': int(passage_order) if passage_order else None,
                        'question_image_file': item_image_file,
                        'question_audio_file': item_audio_file,
                    }
                    if item_ai_prompt:
                        item_content['ai_prompt'] = item_ai_prompt

                    current_app.logger.debug(f"Hàng {index + 2}: Item Image: '{item_image_file}', Item Audio: '{item_audio_file}'")
                    current_app.logger.debug(f"Hàng {index + 2}: Group Image: '{group_image_file}', Group Audio: '{group_audio_file}'")

                    new_item = LearningItem(
                        container_id=new_set.container_id,
                        group_id=group_db_id,
                        item_type='QUIZ_MCQ',
                        content=item_content,
                        order_in_container=int(passage_order) if passage_order else index + 1
                    )
                    db.session.add(new_item)
                    items_added_count += 1
                flash_message = f'Bộ câu hỏi và {items_added_count} câu hỏi từ Excel đã được tạo thành công!'
                flash_category = 'success'
            else:
                flash_message = 'Bộ câu hỏi mới đã được tạo thành công!'
                flash_category = 'success'
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"LỖI XẢY RA khi thêm bộ quiz hoặc xử lý Excel: {e}", exc_info=True)
            flash_message = f'Lỗi khi xử lý: {str(e)}'
            flash_category = 'danger'
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': flash_category == 'success', 'message': flash_message})
        else:
            flash(flash_message, flash_category)
            return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400
    
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_set_bare.html', form=form, title='Thêm Bộ câu hỏi mới')
    return render_template('add_edit_quiz_set.html', form=form, title='Thêm Bộ câu hỏi mới')

@quizzes_bp.route('/quizzes/edit/<int:set_id>', methods=['GET', 'POST'])
@login_required
def edit_quiz_set(set_id):
    """
    Chỉnh sửa một bộ Quiz hiện có.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    
    form = QuizSetForm(obj=quiz_set)
    _apply_is_public_restrictions(form)
    if form.validate_on_submit():
        quiz_set.title = form.title.data
        quiz_set.description = form.description.data
        quiz_set.tags = form.tags.data
        quiz_set.is_public = False if current_user.user_role == 'free' else form.is_public.data
        quiz_set.ai_settings = {'custom_prompt': form.ai_prompt.data} if form.ai_prompt.data else None
        db.session.commit()
        flash('Bộ câu hỏi đã được cập nhật!', 'success')
        return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
    
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_set_bare.html', form=form, title='Sửa Bộ câu hỏi', quiz_set=quiz_set)
    return render_template('add_edit_quiz_set.html', form=form, title='Sửa Bộ câu hỏi', quiz_set=quiz_set)

@quizzes_bp.route('/quizzes/delete/<int:set_id>', methods=['POST'])
@login_required
def delete_quiz_set(set_id):
    """
    Xóa một bộ Quiz.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    
    db.session.delete(quiz_set)
    db.session.commit()
    
    flash('Bộ câu hỏi đã được xóa thành công!', 'success')
    return redirect(url_for('content_management.content_dashboard', tab='quizzes'))

@quizzes_bp.route('/quizzes/<int:set_id>/items')
@login_required
def list_quiz_items(set_id):
    """
    Hiển thị danh sách các câu hỏi trong một bộ Quiz cụ thể.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if not quiz_set.is_public and current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)

    base_query = LearningItem.query.filter_by(container_id=quiz_set.container_id, item_type='QUIZ_MCQ')
    
    item_search_field_map = {
        'question': LearningItem.content['question'],
        'option_a': LearningItem.content['options']['A'],
        'option_b': LearningItem.content['options']['B'],
        'option_c': LearningItem.content['options']['C'],
        'option_d': LearningItem.content['options']['D'],
        'correct_answer': LearningItem.content['correct_answer'],
        'guidance': LearningItem.content['explanation'],
        'pre_question_text': LearningItem.content['pre_question_text'],
        'passage_text': LearningItem.content['passage_text'],
        'question_image_file': LearningItem.content['question_image_file'],
        'question_audio_file': LearningItem.content['question_audio_file'],
        'ai_prompt': LearningItem.content['ai_prompt']
    }

    base_query = apply_search_filter(base_query, search_query, item_search_field_map, search_field)

    pagination = get_pagination_data(base_query.order_by(LearningItem.order_in_container), page)
    quiz_items = pagination.items
    
    can_edit = (current_user.user_role == 'admin' or quiz_set.creator_user_id == current_user.user_id)
    
    return render_template('quiz_items.html', 
                           quiz_set=quiz_set, 
                           quiz_items=quiz_items, 
                           can_edit=can_edit, 
                           pagination=pagination, 
                           search_query=search_query,
                           search_field=search_field,
                           search_field_map=item_search_field_map
                           )

@quizzes_bp.route('/quizzes/<int:set_id>/items/add', methods=['GET', 'POST'])
@login_required
def add_quiz_item(set_id):
    """
    Thêm một câu hỏi mới vào một bộ Quiz cụ thể.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    
    form = QuizItemForm()
    if form.validate_on_submit():
        new_order = form.order_in_container.data
        
        if new_order is not None:
            db.session.query(LearningItem).filter(
                LearningItem.container_id == set_id,
                LearningItem.item_type == 'QUIZ_MCQ',
                LearningItem.order_in_container >= new_order
            ).update({
                LearningItem.order_in_container: LearningItem.order_in_container + 1
            })
        else:
            max_order = db.session.query(db.func.max(LearningItem.order_in_container)).filter_by(
                container_id=set_id,
                item_type='QUIZ_MCQ'
            ).scalar()
            new_order = (max_order or 0) + 1
        
        content_dict = {
            'question': form.question.data,
            'options': {
                'A': form.option_a.data, 'B': form.option_b.data,
                'C': form.option_c.data, 'D': form.option_d.data
            },
            'correct_answer': form.correct_answer_text.data,
            'explanation': form.guidance.data,
            'pre_question_text': form.pre_question_text.data,
            'passage_text': form.passage_text.data,
            'passage_order': form.passage_order.data,
            'question_image_file': _process_relative_url(form.question_image_file.data),
            'question_audio_file': _process_relative_url(form.question_audio_file.data)
        }
        if form.ai_prompt.data:
            content_dict['ai_prompt'] = form.ai_prompt.data

        new_item = LearningItem(
            container_id=set_id,
            group_id=None,
            item_type='QUIZ_MCQ',
            content=content_dict,
            order_in_container=new_order
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Câu hỏi mới đã được thêm!', 'success')
        return redirect(url_for('.list_quiz_items', set_id=set_id))
    
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_item_bare.html', form=form, quiz_set=quiz_set, title='Thêm Câu hỏi')
    return render_template('add_edit_quiz_item.html', form=form, quiz_set=quiz_set, title='Thêm Câu hỏi')

@quizzes_bp.route('/quizzes/<int:set_id>/items/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_quiz_item(set_id, item_id):
    """
    Chỉnh sửa một câu hỏi hiện có trong một bộ Quiz cụ thể.
    """
    quiz_item = LearningItem.query.get_or_404(item_id)
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    
    form = QuizItemForm()
    if request.method == 'GET':
        form.question.data = quiz_item.content.get('question')
        form.pre_question_text.data = quiz_item.content.get('pre_question_text')
        form.option_a.data = quiz_item.content.get('options', {}).get('A')
        form.option_b.data = quiz_item.content.get('options', {}).get('B')
        form.option_c.data = quiz_item.content.get('options', {}).get('C')
        form.option_d.data = quiz_item.content.get('options', {}).get('D')
        form.correct_answer_text.data = quiz_item.content.get('correct_answer')
        form.guidance.data = quiz_item.content.get('explanation')
        form.question_image_file.data = quiz_item.content.get('question_image_file')
        form.question_audio_file.data = quiz_item.content.get('question_audio_file')
        form.passage_text.data = quiz_item.content.get('passage_text')
        form.passage_order.data = quiz_item.content.get('passage_order')
        form.ai_explanation.data = quiz_item.ai_explanation
        form.ai_prompt.data = quiz_item.content.get('ai_prompt')
        form.order_in_container.data = quiz_item.order_in_container

    if form.validate_on_submit():
        old_order = quiz_item.order_in_container
        new_order = form.order_in_container.data
        
        if new_order is not None and new_order != old_order:
            if new_order > old_order:
                db.session.query(LearningItem).filter(
                    LearningItem.container_id == set_id,
                    LearningItem.item_type == 'QUIZ_MCQ',
                    LearningItem.order_in_container > old_order,
                    LearningItem.order_in_container <= new_order
                ).update({
                    LearningItem.order_in_container: LearningItem.order_in_container - 1
                })
            else:
                db.session.query(LearningItem).filter(
                    LearningItem.container_id == set_id,
                    LearningItem.item_type == 'QUIZ_MCQ',
                    LearningItem.order_in_container >= new_order,
                    LearningItem.order_in_container < old_order
                ).update({
                    LearningItem.order_in_container: LearningItem.order_in_container + 1
                })
            quiz_item.order_in_container = new_order
        
        quiz_item.content['question'] = form.question.data
        quiz_item.content['pre_question_text'] = form.pre_question_text.data
        quiz_item.content['options']['A'] = form.option_a.data
        quiz_item.content['options']['B'] = form.option_b.data
        quiz_item.content['options']['C'] = form.option_c.data
        quiz_item.content['options']['D'] = form.option_d.data
        quiz_item.content['correct_answer'] = form.correct_answer_text.data
        quiz_item.content['explanation'] = form.guidance.data
        quiz_item.content['question_image_file'] = _process_relative_url(form.question_image_file.data)
        quiz_item.content['question_audio_file'] = _process_relative_url(form.question_audio_file.data)
        quiz_item.content['passage_text'] = form.passage_text.data
        quiz_item.content['passage_order'] = form.passage_order.data
        quiz_item.ai_explanation = form.ai_explanation.data
        
        if form.ai_prompt.data:
            quiz_item.content['ai_prompt'] = form.ai_prompt.data
        elif 'ai_prompt' in quiz_item.content:
            del quiz_item.content['ai_prompt']

        flag_modified(quiz_item, "content")
        db.session.commit()
        flash('Câu hỏi đã được cập nhật!', 'success')
        return redirect(url_for('.list_quiz_items', set_id=set_id))
    
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_item_bare.html', form=form, quiz_set=quiz_set, quiz_item=quiz_item, title='Chỉnh sửa Câu hỏi')
    return render_template('add_edit_quiz_item.html', form=form, quiz_set=quiz_set, quiz_item=quiz_item, title='Chỉnh sửa Câu hỏi')

@quizzes_bp.route('/quizzes/<int:set_id>/items/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_quiz_item(set_id, item_id):
    """
    Xóa một câu hỏi khỏi một bộ Quiz cụ thể.
    """
    quiz_item = LearningItem.query.get_or_404(item_id)
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    
    db.session.delete(quiz_item)
    db.session.commit()
    
    flash('Câu hỏi đã được xóa.', 'success')
    return redirect(url_for('.list_quiz_items', set_id=set_id))
