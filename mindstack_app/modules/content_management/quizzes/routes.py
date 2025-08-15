# File: newmindstack/mindstack_app/modules/content_management/quizzes/routes.py
# Phiên bản: 3.23
# ĐÃ SỬA: Cập nhật logic import Excel để lưu content của LearningGroup
#         với key là tên cột gốc từ file Excel (passage_text, question_audio_file...).

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.orm.attributes import flag_modified
from ..forms import QuizSetForm, QuizItemForm
from ....models import db, LearningContainer, LearningItem, LearningGroup, ContainerContributor, User
import pandas as pd
import tempfile
import os
from ....utils.pagination import get_pagination_data
from ....utils.search import apply_search_filter

quizzes_bp = Blueprint('content_management_quizzes', __name__,
                        template_folder='../templates/quizzes')

@quizzes_bp.route('/quizzes/process_excel_info', methods=['POST'])
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
            current_app.logger.error(f"Lỗi khi xử lý sheet Info: {e}")
            return jsonify({'success': False, 'message': f'Lỗi đọc file Excel: {e}'}), 500
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
    return jsonify({'success': False, 'message': 'File không hợp lệ. Vui lòng chọn file .xlsx'}), 400

@quizzes_bp.route('/quizzes')
@login_required
def list_quiz_sets():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    base_query = LearningContainer.query.filter_by(container_type='QUIZ_SET')
    if current_user.user_role != 'admin':
        user_id = current_user.user_id
        created_sets_query = base_query.filter_by(creator_user_id=user_id)
        contributed_sets_query = base_query.join(ContainerContributor).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor'
        )
        base_query = created_sets_query.union(contributed_sets_query)
    search_fields = [LearningContainer.title, LearningContainer.description, LearningContainer.tags]
    base_query = apply_search_filter(base_query, search_query, search_fields)
    pagination = get_pagination_data(base_query.order_by(LearningContainer.created_at.desc()), page)
    quiz_sets = pagination.items
    for set_item in quiz_sets:
        set_item.item_count = db.session.query(LearningItem).filter_by(
            container_id=set_item.container_id,
            item_type='QUIZ_MCQ'
        ).count()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_quiz_sets_list.html', quiz_sets=quiz_sets, pagination=pagination, search_query=search_query)
    else:
        return render_template('quiz_sets.html', quiz_sets=quiz_sets, pagination=pagination, search_query=search_query)

@quizzes_bp.route('/quizzes/add', methods=['GET', 'POST'])
@login_required
def add_quiz_set():
    form = QuizSetForm()
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
                
                group_cache = {}
                items_added_count = 0

                for index, row in df.iterrows():
                    passage_order = str(row['passage_order']) if 'passage_order' in df.columns and pd.notna(row['passage_order']) else None
                    group_db_id = None

                    if passage_order:
                        passage_text = str(row['passage_text']) if 'passage_text' in df.columns and pd.notna(row['passage_text']) else None
                        audio_file = str(row['question_audio_file']) if 'question_audio_file' in df.columns and pd.notna(row['question_audio_file']) else None
                        image_file = str(row['question_image_file']) if 'question_image_file' in df.columns and pd.notna(row['question_image_file']) else None
                        
                        group_key = None
                        group_content = {}
                        group_type = ''

                        # SỬA LOGIC LƯU CONTENT CHO GROUP TẠI ĐÂY
                        if passage_text:
                            group_key = passage_text
                            group_content['passage_text'] = passage_text
                            group_type = 'PASSAGE'
                        elif audio_file:
                            group_key = audio_file
                            group_content['question_audio_file'] = audio_file
                            group_type = 'AUDIO'
                        elif image_file:
                            group_key = image_file
                            group_content['question_image_file'] = image_file
                            group_type = 'IMAGE'

                        if group_key:
                            if group_key not in group_cache:
                                new_group = LearningGroup(
                                    container_id=new_set.container_id,
                                    group_type=group_type,
                                    content=group_content
                                )
                                db.session.add(new_group)
                                db.session.flush()
                                group_cache[group_key] = new_group.group_id
                                group_db_id = new_group.group_id
                            else:
                                group_db_id = group_cache[group_key]
                    
                    option_a = str(row['option_a']) if 'option_a' in df.columns and pd.notna(row['option_a']) else None
                    option_b = str(row['option_b']) if 'option_b' in df.columns and pd.notna(row['option_b']) else None
                    correct_answer = str(row['correct_answer_text']) if 'correct_answer_text' in df.columns and pd.notna(row['correct_answer_text']) else None

                    if not (option_a and option_b and correct_answer):
                        continue

                    question_text = str(row['question']) if 'question' in df.columns and pd.notna(row['question']) else ''
                    
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
                        'passage_order': passage_order,
                        'passage_text': str(row['passage_text']) if 'passage_text' in df.columns and pd.notna(row['passage_text']) else None
                    }
                    
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
            current_app.logger.error(f"LỖI XẢY RA: {e}", exc_info=True)
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
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    form = QuizSetForm(obj=quiz_set)
    if form.validate_on_submit():
        quiz_set.title = form.title.data
        quiz_set.description = form.description.data
        quiz_set.tags = form.tags.data
        quiz_set.is_public = form.is_public.data
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
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if not quiz_set.is_public and current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    base_query = LearningItem.query.filter_by(container_id=quiz_set.container_id, item_type='QUIZ_MCQ')
    search_fields = [LearningItem.content['question']]
    base_query = apply_search_filter(base_query, search_query, search_fields)
    pagination = get_pagination_data(base_query.order_by(LearningItem.order_in_container), page)
    quiz_items = pagination.items
    can_edit = (current_user.user_role == 'admin' or quiz_set.creator_user_id == current_user.user_id)
    return render_template('quiz_items.html', quiz_set=quiz_set, quiz_items=quiz_items, can_edit=can_edit, pagination=pagination, search_query=search_query)

@quizzes_bp.route('/quizzes/<int:set_id>/items/add', methods=['GET', 'POST'])
@login_required
def add_quiz_item(set_id):
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    form = QuizItemForm()
    if form.validate_on_submit():
        new_item = LearningItem(
            container_id=set_id,
            item_type='QUIZ_MCQ',
            content={
                'question': form.question.data,
                'options': {
                    'A': form.option_a.data, 'B': form.option_b.data,
                    'C': form.option_c.data, 'D': form.option_d.data
                },
                'correct_answer': form.correct_answer_text.data,
                'explanation': form.guidance.data,
                'pre_question_text': form.pre_question_text.data,
                'passage_text': form.passage_text.data,
                'passage_order': form.passage_order.data
            }
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
    quiz_item = LearningItem.query.get_or_404(item_id)
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    
    form = QuizItemForm()

    if request.method == 'GET':
        form.question.data = quiz_item.content.get('question')
        form.option_a.data = quiz_item.content.get('options', {}).get('A')
        form.option_b.data = quiz_item.content.get('options', {}).get('B')
        form.option_c.data = quiz_item.content.get('options', {}).get('C')
        form.option_d.data = quiz_item.content.get('options', {}).get('D')
        form.correct_answer_text.data = quiz_item.content.get('correct_answer')
        form.guidance.data = quiz_item.content.get('explanation')
        form.pre_question_text.data = quiz_item.content.get('pre_question_text')
        form.passage_text.data = quiz_item.content.get('passage_text')
        form.passage_order.data = quiz_item.content.get('passage_order')

    if form.validate_on_submit():
        quiz_item.content['question'] = form.question.data
        quiz_item.content['options']['A'] = form.option_a.data
        quiz_item.content['options']['B'] = form.option_b.data
        quiz_item.content['options']['C'] = form.option_c.data
        quiz_item.content['options']['D'] = form.option_d.data
        quiz_item.content['correct_answer'] = form.correct_answer_text.data
        quiz_item.content['explanation'] = form.guidance.data
        quiz_item.content['pre_question_text'] = form.pre_question_text.data
        quiz_item.content['passage_text'] = form.passage_text.data
        quiz_item.content['passage_order'] = form.passage_order.data
        
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
    quiz_item = LearningItem.query.get_or_404(item_id)
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403)
    db.session.delete(quiz_item)
    db.session.commit()
    flash('Câu hỏi đã được xóa.', 'success')
    return redirect(url_for('.list_quiz_items', set_id=set_id))
