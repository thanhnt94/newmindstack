# File: newmindstack/mindstack_app/modules/content_management/quizzes/routes.py
# Phiên bản: 3.30
# ĐÃ SỬA: Khắc phục UnboundLocalError: local variable 'file' referenced before assignment
#         bằng cách đảm bảo biến 'excel_file' được gán giá trị bên trong khối if kiểm tra file.
# ĐÃ SỬA: Khắc phục UnboundLocalError cho group_image_file và group_audio_file
#         bằng cách khởi tạo chúng ở đầu mỗi vòng lặp.
# ĐÃ SỬA: Cập nhật template_folder của Blueprint để phản ánh cấu trúc thư mục mới.
# ĐÃ SỬA: Bổ sung logic đọc và lưu trữ question_image_file và question_audio_file
#         vào content của LearningItem khi upload từ Excel.

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

@quizzes_bp.route('/quizzes/process_excel_info', methods=['POST'])
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

    Hàm này truy xuất các bộ Quiz mà người dùng hiện tại đã tạo hoặc đóng góp,
    áp dụng bộ lọc tìm kiếm và phân trang, sau đó hiển thị chúng.
    """
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)

    # Truy vấn cơ sở để lấy các bộ Quiz
    base_query = LearningContainer.query.filter_by(container_type='QUIZ_SET')
    
    # Lọc theo quyền sở hữu/đóng góp nếu không phải admin
    if current_user.user_role != 'admin':
        user_id = current_user.user_id
        created_sets_query = base_query.filter_by(creator_user_id=user_id)
        contributed_sets_query = base_query.join(ContainerContributor).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor'
        )
        base_query = created_sets_query.union(contributed_sets_query)
        
    # Ánh xạ các trường có thể tìm kiếm
    search_field_map = {
        'title': LearningContainer.title,
        'description': LearningContainer.description,
        'tags': LearningContainer.tags
    }
    
    # Áp dụng bộ lọc tìm kiếm
    base_query = apply_search_filter(base_query, search_query, search_field_map, search_field)

    # Lấy dữ liệu phân trang
    pagination = get_pagination_data(base_query.order_by(LearningContainer.created_at.desc()), page)
    quiz_sets = pagination.items
    
    # Đếm số lượng câu hỏi trong mỗi bộ
    for set_item in quiz_sets:
        set_item.item_count = db.session.query(LearningItem).filter_by(
            container_id=set_item.container_id,
            item_type='QUIZ_MCQ'
        ).count()

    # Các biến để truyền vào template
    template_vars = {
        'quiz_sets': quiz_sets, 
        'pagination': pagination, 
        'search_query': search_query,
        'search_field': search_field,
        'search_field_map': search_field_map # Truyền map để tạo dropdown cho template
    }

    # Trả về template phù hợp (ajax hoặc đầy đủ)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_quiz_sets_list.html', **template_vars)
    else:
        return render_template('quiz_sets.html', **template_vars)

@quizzes_bp.route('/quizzes/add', methods=['GET', 'POST'])
@login_required
def add_quiz_set():
    """
    Thêm một bộ Quiz mới.

    Hàm này xử lý việc tạo bộ Quiz, bao gồm cả việc nhập dữ liệu từ file Excel
    và thêm các câu hỏi liên quan.
    """
    form = QuizSetForm()
    if form.validate_on_submit():
        flash_message = ''
        flash_category = ''
        temp_filepath = None
        try:
            # Tạo bộ Quiz mới
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
            db.session.flush() # Lưu tạm thời để có container_id

            # Xử lý file Excel nếu có
            if form.excel_file.data and form.excel_file.data.filename != '':
                excel_file = form.excel_file.data # Đã di chuyển dòng này vào đây
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    excel_file.save(tmp_file.name)
                    temp_filepath = tmp_file.name
                df = pd.read_excel(temp_filepath, sheet_name='Data')
                group_cache = {}
                items_added_count = 0
                for index, row in df.iterrows():
                    # Khởi tạo các biến media của nhóm và passage_text ở đầu mỗi vòng lặp
                    # để tránh UnboundLocalError nếu các cột này không tồn tại hoặc rỗng
                    group_passage_text = None
                    group_audio_file = None
                    group_image_file = None

                    # Lấy thông tin passage_order để xác định nhóm
                    passage_order = str(row['passage_order']) if 'passage_order' in df.columns and pd.notna(row['passage_order']) else None
                    group_db_id = None
                    group_content = {}
                    group_type = ''

                    # Xử lý thông tin LearningGroup (nếu có)
                    if passage_order:
                        # Lấy các trường media cho LearningGroup
                        group_passage_text = str(row['passage_text']) if 'passage_text' in df.columns and pd.notna(row['passage_text']) else None
                        group_audio_file = str(row['group_audio_file']) if 'group_audio_file' in df.columns and pd.notna(row['group_audio_file']) else None
                        group_image_file = str(row['group_image_file']) if 'group_image_file' in df.columns and pd.notna(row['group_image_file']) else None
                        
                        group_key = None # Khóa để cache nhóm, có thể là passage_text hoặc tên file media nhóm
                        
                        if group_passage_text:
                            group_key = group_passage_text
                            group_content['passage_text'] = group_passage_text
                            group_type = 'PASSAGE'
                        
                        # Ưu tiên audio/image nếu có và là nhóm chính
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
                            db.session.flush() # Lưu tạm thời để lấy group_id
                            group_cache[group_key] = new_group.group_id
                            group_db_id = new_group.group_id
                        elif group_key: # Nếu nhóm đã có trong cache
                            group_db_id = group_cache[group_key]

                    # Đảm bảo có các trường cốt lõi cho câu hỏi
                    option_a = str(row['option_a']) if 'option_a' in df.columns and pd.notna(row['option_a']) else None
                    option_b = str(row['option_b']) if 'option_b' in df.columns and pd.notna(row['option_b']) else None
                    correct_answer = str(row['correct_answer_text']) if 'correct_answer_text' in df.columns and pd.notna(row['correct_answer_text']) else None
                    if not (option_a and option_b and correct_answer):
                        current_app.logger.warning(f"Bỏ qua hàng {index + 2} trong Excel: Thiếu thông tin cốt lõi (option_a, option_b, correct_answer_text).")
                        continue # Bỏ qua hàng nếu thiếu thông tin cốt lõi

                    question_text = str(row['question']) if 'question' in df.columns and pd.notna(row['question']) else ''
                    
                    # Lấy các trường media riêng cho LearningItem (câu hỏi con)
                    item_image_file = str(row['question_image_file']) if 'question_image_file' in df.columns and pd.notna(row['question_image_file']) else None
                    item_audio_file = str(row['question_audio_file']) if 'question_audio_file' in df.columns and pd.notna(row['question_audio_file']) else None

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
                        'passage_order': int(passage_order) if passage_order else None, # Đảm bảo lưu passage_order vào item content
                        'question_image_file': item_image_file, # THÊM VÀO: Lưu tên file ảnh của câu hỏi con
                        'question_audio_file': item_audio_file # THÊM VÀO: Lưu tên file audio của câu hỏi con
                    }

                    # Debug log: Kiểm tra các giá trị media trước khi lưu
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
            else: # Nếu không có file excel được tải lên
                flash_message = 'Bộ câu hỏi mới đã được tạo thành công!'
                flash_category = 'success'
            db.session.commit() # Lưu các thay đổi vào DB
        except Exception as e:
            db.session.rollback() # Hoàn tác nếu có lỗi
            current_app.logger.error(f"LỖI XẢY RA khi thêm bộ quiz hoặc xử lý Excel: {e}", exc_info=True)
            flash_message = f'Lỗi khi xử lý: {str(e)}'
            flash_category = 'danger'
        finally:
            # Xóa file tạm thời
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
        
        # Trả về phản hồi JSON hoặc chuyển hướng tùy theo yêu cầu
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': flash_category == 'success', 'message': flash_message})
        else:
            flash(flash_message, flash_category)
            return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
    
    # Xử lý lỗi form validation cho AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400
    
    # Render template cho modal hoặc trang đầy đủ
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_set_bare.html', form=form, title='Thêm Bộ câu hỏi mới')
    return render_template('add_edit_quiz_set.html', form=form, title='Thêm Bộ câu hỏi mới')

@quizzes_bp.route('/quizzes/edit/<int:set_id>', methods=['GET', 'POST'])
@login_required
def edit_quiz_set(set_id):
    """
    Chỉnh sửa một bộ Quiz hiện có.

    Hàm này cho phép chỉnh sửa thông tin của bộ Quiz.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    # Kiểm tra quyền chỉnh sửa
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403) # Không có quyền
    
    form = QuizSetForm(obj=quiz_set)
    if form.validate_on_submit():
        # Cập nhật thông tin bộ Quiz
        quiz_set.title = form.title.data
        quiz_set.description = form.description.data
        quiz_set.tags = form.tags.data
        quiz_set.is_public = form.is_public.data
        quiz_set.ai_settings = {'custom_prompt': form.ai_prompt.data} if form.ai_prompt.data else None
        db.session.commit() # Lưu thay đổi
        flash('Bộ câu hỏi đã được cập nhật!', 'success')
        return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
    
    # Render template cho modal hoặc trang đầy đủ
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_set_bare.html', form=form, title='Sửa Bộ câu hỏi', quiz_set=quiz_set)
    return render_template('add_edit_quiz_set.html', form=form, title='Sửa Bộ câu hỏi', quiz_set=quiz_set)

@quizzes_bp.route('/quizzes/delete/<int:set_id>', methods=['POST'])
@login_required
def delete_quiz_set(set_id):
    """
    Xóa một bộ Quiz.

    Hàm này cho phép xóa một bộ Quiz và các câu hỏi liên quan.
    Chỉ người tạo hoặc admin mới có quyền xóa.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    # Kiểm tra quyền xóa
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403) # Không có quyền
    
    db.session.delete(quiz_set)
    db.session.commit() # Lưu thay đổi
    
    flash('Bộ câu hỏi đã được xóa thành công!', 'success')
    return redirect(url_for('content_management.content_dashboard', tab='quizzes'))

@quizzes_bp.route('/quizzes/<int:set_id>/items')
@login_required
def list_quiz_items(set_id):
    """
    Hiển thị danh sách các câu hỏi trong một bộ Quiz cụ thể.

    Hàm này truy xuất các câu hỏi của một bộ Quiz, áp dụng bộ lọc tìm kiếm
    trên nội dung câu hỏi và phân trang, sau đó hiển thị chúng.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    # Kiểm tra quyền xem
    if not quiz_set.is_public and current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403) # Không có quyền
    
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str) # Lấy trường tìm kiếm từ request

    base_query = LearningItem.query.filter_by(container_id=quiz_set.container_id, item_type='QUIZ_MCQ')
    
    # Ánh xạ các trường có thể tìm kiếm cho Quiz Item
    # LearningItem.content là kiểu JSON, truy cập các khóa bằng cú pháp []
    item_search_field_map = {
        'question': LearningItem.content['question'],
        'option_a': LearningItem.content['options']['A'],
        'option_b': LearningItem.content['options']['B'],
        'option_c': LearningItem.content['options']['C'],
        'option_d': LearningItem.content['options']['D'],
        'correct_answer': LearningItem.content['correct_answer'],
        'guidance': LearningItem.content['explanation'], # Tên trường trong DB là 'explanation'
        'pre_question_text': LearningItem.content['pre_question_text'],
        'passage_text': LearningItem.content['passage_text'],
        'question_image_file': LearningItem.content['question_image_file'],
        'question_audio_file': LearningItem.content['question_audio_file']
    }

    # Áp dụng bộ lọc tìm kiếm với search_field_map đúng định dạng
    base_query = apply_search_filter(base_query, search_query, item_search_field_map, search_field)

    # Lấy dữ liệu phân trang
    pagination = get_pagination_data(base_query.order_by(LearningItem.order_in_container), page)
    quiz_items = pagination.items
    
    # Kiểm tra quyền chỉnh sửa
    can_edit = (current_user.user_role == 'admin' or quiz_set.creator_user_id == current_user.user_id)
    
    return render_template('quiz_items.html', 
                           quiz_set=quiz_set, 
                           quiz_items=quiz_items, 
                           can_edit=can_edit, 
                           pagination=pagination, 
                           search_query=search_query,
                           search_field=search_field, # Truyền trường tìm kiếm hiện tại
                           search_field_map=item_search_field_map # Truyền map để tạo dropdown cho template
                           )

@quizzes_bp.route('/quizzes/<int:set_id>/items/add', methods=['GET', 'POST'])
@login_required
def add_quiz_item(set_id):
    """
    Thêm một câu hỏi mới vào một bộ Quiz cụ thể.

    Hàm này xử lý việc thêm một câu hỏi mới vào một bộ Quiz hiện có.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    # Kiểm tra quyền thêm câu hỏi
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403) # Không có quyền
    
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
                'passage_order': form.passage_order.data,
                # Thêm các trường media từ form vào content
                'question_image_file': form.question_image_file.data,
                'question_audio_file': form.question_audio_file.data
            }
        )
        db.session.add(new_item)
        db.session.commit() # Lưu thay đổi
        flash('Câu hỏi mới đã được thêm!', 'success')
        return redirect(url_for('.list_quiz_items', set_id=set_id))
    
    # Render template cho modal hoặc trang đầy đủ
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_item_bare.html', form=form, quiz_set=quiz_set, title='Thêm Câu hỏi')
    return render_template('add_edit_quiz_item.html', form=form, quiz_set=quiz_set, title='Thêm Câu hỏi')

@quizzes_bp.route('/quizzes/<int:set_id>/items/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_quiz_item(set_id, item_id):
    """
    Chỉnh sửa một câu hỏi hiện có trong một bộ Quiz cụ thể.

    Hàm này xử lý việc cập nhật nội dung của một câu hỏi.
    """
    quiz_item = LearningItem.query.get_or_404(item_id)
    quiz_set = LearningContainer.query.get_or_404(set_id)
    # Kiểm tra quyền chỉnh sửa
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403) # Không có quyền
    
    form = QuizItemForm()
    if request.method == 'GET':
        # Populate form với dữ liệu hiện có từ JSON content
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
        form.question_image_file.data = quiz_item.content.get('question_image_file')
        form.question_audio_file.data = quiz_item.content.get('question_audio_file')

    if form.validate_on_submit():
        # Cập nhật nội dung thẻ
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
        # Cập nhật các trường media
        quiz_item.content['question_image_file'] = form.question_image_file.data
        quiz_item.content['question_audio_file'] = form.question_audio_file.data

        # Đánh dấu trường JSON đã thay đổi để SQLAlchemy lưu lại
        flag_modified(quiz_item, "content")
        db.session.commit() # Lưu thay đổi
        flash('Câu hỏi đã được cập nhật!', 'success')
        return redirect(url_for('.list_quiz_items', set_id=set_id))
    
    # Render template cho modal hoặc trang đầy đủ
    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_item_bare.html', form=form, quiz_set=quiz_set, quiz_item=quiz_item, title='Chỉnh sửa Câu hỏi')
    return render_template('add_edit_quiz_item.html', form=form, quiz_set=quiz_set, quiz_item=quiz_item, title='Chỉnh sửa Câu hỏi')

@quizzes_bp.route('/quizzes/<int:set_id>/items/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_quiz_item(set_id, item_id):
    """
    Xóa một câu hỏi khỏi một bộ Quiz cụ thể.

    Hàm này xử lý việc xóa một câu hỏi.
    """
    quiz_item = LearningItem.query.get_or_404(item_id)
    quiz_set = LearningContainer.query.get_or_404(set_id)
    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        abort(403) # Không có quyền
    
    db.session.delete(quiz_item)
    db.session.commit() # Lưu thay đổi
    
    flash('Câu hỏi đã được xóa.', 'success')
    return redirect(url_for('.list_quiz_items', set_id=set_id))