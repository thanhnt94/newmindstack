# File: newmindstack/mindstack_app/modules/content_management/quizzes/routes.py
# Phiên bản: 3.12 (Đã sửa lỗi đếm câu hỏi và hỗ trợ modal cho edit item)
# Mục đích: Xử lý các route liên quan đến quản lý bộ câu hỏi (LearningContainer loại 'QUIZ_SET')
#           Bao gồm tạo, xem, chỉnh sửa, xóa bộ câu hỏi và các câu hỏi (LearningItem loại 'QUIZ_MCQ')
#           Áp dụng logic phân quyền để kiểm tra người dùng có quyền truy cập/chỉnh sửa hay không.
#           Bổ sung logic để phục vụ nội dung riêng cho yêu cầu AJAX từ dashboard tổng quan.
#           Đã sửa lỗi BuildError bằng cách cập nhật tên endpoint trong url_for.
#           Đã khắc phục ModuleNotFoundError bằng cách sửa đường dẫn import models.
#           ĐÃ SỬA: Chuyển hướng sau khi thêm/sửa/xóa về content_dashboard và chọn tab đúng.
#           ĐÃ SỬA: Điều chỉnh để trả về JSON cho các yêu cầu AJAX khi thêm/sửa/xóa bộ.
#           ĐÃ SỬA: Render template bare form cho yêu cầu GET từ modal, full form cho non-modal GET.
#           ĐÃ CẢI TIẾN: Logic xử lý upload file Excel, đọc các cột đầy đủ và tạo QuizItem từ đó.
#           ĐÃ THÊM: Log chi tiết để debug quá trình upload file Excel.
#           ĐÃ SỬA: Logic kiểm tra nội dung bắt buộc của câu hỏi để cho phép câu hỏi chỉ có media.
#           ĐÃ SỬA: Khởi tạo biến question_image_file và question_audio_file để tránh lỗi UndefinedVariable.
#           ĐÃ SỬA: Đếm số lượng câu hỏi chính xác và truyền vào template.
#           ĐÃ SỬA: Route edit_quiz_item hỗ trợ mở trong modal.

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from ..forms import QuizSetForm, QuizItemForm
from ....models import db, LearningContainer, LearningItem, ContainerContributor, User
import pandas as pd
import tempfile
import os

# Định nghĩa Blueprint cho quản lý bộ câu hỏi
quizzes_bp = Blueprint('content_management_quizzes', __name__,
                        template_folder='../templates/quizzes')

@quizzes_bp.route('/quizzes')
@login_required
def list_quiz_sets():
    """
    Hiển thị danh sách các bộ câu hỏi mà người dùng hiện tại có quyền truy cập.
    Admin có thể thấy tất cả các bộ câu hỏi.
    Người dùng thông thường chỉ thấy bộ câu hỏi do mình tạo hoặc được cấp quyền chỉnh sửa.
    Nếu yêu cầu là AJAX, chỉ trả về phần danh sách bộ câu hỏi.
    """
    quiz_sets = []
    if current_user.user_role == 'admin':
        quiz_sets = LearningContainer.query.filter_by(container_type='QUIZ_SET').all()
    else:
        user_id = current_user.user_id
        created_sets_query = LearningContainer.query.filter_by(
            creator_user_id=user_id,
            container_type='QUIZ_SET'
        )
        contributed_sets_query = LearningContainer.query.join(ContainerContributor).filter(
            ContainerContributor.user_id == user_id,
            ContainerContributor.permission_level == 'editor',
            LearningContainer.container_type == 'QUIZ_SET'
        )
        quiz_sets = created_sets_query.union(contributed_sets_query).all()

    # SỬA: Đếm số lượng item cho mỗi bộ câu hỏi
    for set_item in quiz_sets:
        set_item.item_count = db.session.query(LearningItem).filter_by(
            container_id=set_item.container_id,
            item_type='QUIZ_MCQ'
        ).count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_quiz_sets_list.html', quiz_sets=quiz_sets)
    else:
        return render_template('quiz_sets.html', quiz_sets=quiz_sets)

@quizzes_bp.route('/quizzes/add', methods=['GET', 'POST'])
@login_required
def add_quiz_set():
    """
    Thêm một bộ câu hỏi mới.
    Chỉ người dùng đã đăng nhập mới có thể thêm bộ câu hỏi.
    Người tạo bộ câu hỏi sẽ tự động là creator_user_id.
    """
    form = QuizSetForm()
    if form.validate_on_submit():
        current_app.logger.info("add_quiz_set: Form đã được gửi và xác thực thành công.")
        flash_message = ''
        flash_category = ''
        temp_filepath = None

        try:
            # Tạo bộ câu hỏi mới
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
            db.session.flush() # Lấy new_set.container_id trước khi commit
            current_app.logger.info(f"add_quiz_set: Đã tạo LearningContainer mới với ID: {new_set.container_id}")

            # Xử lý file Excel nếu có
            if form.excel_file.data and form.excel_file.data.filename != '':
                current_app.logger.info(f"add_quiz_set: Phát hiện file Excel: {form.excel_file.data.filename}")
                excel_file = form.excel_file.data
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    excel_file.save(tmp_file.name)
                    temp_filepath = tmp_file.name
                current_app.logger.info(f"add_quiz_set: Đã lưu file tạm thời tại: {temp_filepath}")

                # Đọc file Excel
                df = pd.read_excel(temp_filepath)
                current_app.logger.info(f"add_quiz_set: Đã đọc file Excel. Số hàng: {len(df)}. Cột: {df.columns.tolist()}")
                
                # Định nghĩa các cột cần thiết và tùy chọn từ cấu trúc Excel bạn cung cấp
                required_basic_cols = ['option_a', 'option_b', 'correct_answer_text'] # Các cột luôn cần
                
                # Kiểm tra các cột bắt buộc cơ bản
                if not all(col in df.columns for col in required_basic_cols):
                    missing_cols = [col for col in required_basic_cols if col not in df.columns]
                    raise ValueError(f"File Excel phải có các cột bắt buộc: {', '.join(required_basic_cols)}. Thiếu: {', '.join(missing_cols)}")
                current_app.logger.info("add_quiz_set: Các cột bắt buộc cơ bản đã được tìm thấy.")

                # Thêm các câu hỏi từ file Excel
                items_added_count = 0
                for index, row in df.iterrows():
                    # Khởi tạo các biến tùy chọn để tránh lỗi "not defined"
                    question_text = ''
                    question_image_file = ''
                    question_audio_file = ''

                    # Lấy các giá trị, đảm bảo là chuỗi và xử lý NaN
                    question_text = str(row['question']) if 'question' in df.columns and pd.notna(row['question']) else ''
                    option_a = str(row['option_a']) if pd.notna(row['option_a']) else ''
                    option_b = str(row['option_b']) if pd.notna(row['option_b']) else ''
                    correct_answer = str(row['correct_answer_text']) if pd.notna(row['correct_answer_text']) else ''
                    question_image_file = str(row['question_image_file']) if 'question_image_file' in df.columns and pd.notna(row['question_image_file']) else ''
                    question_audio_file = str(row['question_audio_file']) if 'question_audio_file' in df.columns and pd.notna(row['question_audio_file']) else ''

                    # SỬA LOGIC: Câu hỏi hợp lệ nếu có văn bản HOẶC hình ảnh HOẶC âm thanh
                    is_question_content_present = bool(question_text) or bool(question_image_file) or bool(question_audio_file)

                    if is_question_content_present and option_a and option_b and correct_answer:
                        item_content = {
                            'question': question_text, # Có thể là chuỗi rỗng nếu câu hỏi là media
                            'options': {
                                'A': option_a,
                                'B': option_b,
                                'C': str(row['option_c']) if 'option_c' in df.columns and pd.notna(row['option_c']) else None,
                                'D': str(row['option_d']) if 'option_d' in df.columns and pd.notna(row['option_d']) else None
                            },
                            'correct_answer': correct_answer,
                            'pre_question_text': str(row['pre_question_text']) if 'pre_question_text' in df.columns and pd.notna(row['pre_question_text']) else None,
                            'explanation': str(row['guidance']) if 'guidance' in df.columns and pd.notna(row['guidance']) else None,
                            'question_image_file': question_image_file if question_image_file else None,
                            'question_audio_file': question_audio_file if question_audio_file else None,
                            'passage_text': str(row['passage_text']) if 'passage_text' in df.columns and pd.notna(row['passage_text']) else None,
                            'passage_order': str(row['passage_order']) if 'passage_order' in df.columns and pd.notna(row['passage_order']) else None,
                        }

                        new_item = LearningItem(
                            container_id=new_set.container_id,
                            item_type='QUIZ_MCQ',
                            content=item_content,
                            order_in_container=index + 1
                        )
                        db.session.add(new_item)
                        items_added_count += 1
                        current_app.logger.info(f"add_quiz_set: Đã thêm câu hỏi từ hàng {index + 1}: Question: '{question_text[:50]}', Image: '{question_image_file}', Audio: '{question_audio_file}'")
                    else:
                        current_app.logger.warning(f"add_quiz_set: Bỏ qua hàng {index + 1} do thiếu nội dung bắt buộc (Câu hỏi, Lựa chọn A, Lựa chọn B, hoặc Đáp án đúng).")
                
                flash_message = f'Bộ câu hỏi và {items_added_count} câu hỏi từ Excel đã được tạo thành công!'
                flash_category = 'success'

            else: # Không có file Excel được tải lên
                current_app.logger.info("add_quiz_set: Không có file Excel được tải lên.")
                flash_message = 'Bộ câu hỏi mới đã được tạo thành công!'
                flash_category = 'success'
            
            db.session.commit()
            current_app.logger.info("add_quiz_set: Commit database thành công.")

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"add_quiz_set: Lỗi trong quá trình xử lý file Excel hoặc tạo bộ câu hỏi: {str(e)}", exc_info=True)
            flash_message = f'Lỗi khi xử lý file Excel hoặc tạo bộ câu hỏi: {str(e)}'
            flash_category = 'danger'
            # Nếu là AJAX, trả về lỗi
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': flash_message}), 400
            else:
                flash(flash_message, flash_category)
                return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
                current_app.logger.info(f"add_quiz_set: Đã xóa file tạm thời: {temp_filepath}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': flash_message})
        else:
            flash(flash_message, flash_category)
            return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
    
    if form.errors:
        current_app.logger.warning(f"add_quiz_set: Form không hợp lệ. Lỗi: {form.errors}")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_set_bare.html', form=form, title='Thêm Bộ câu hỏi mới')
    return render_template('add_edit_quiz_set.html', form=form, title='Thêm Bộ câu hỏi mới')

@quizzes_bp.route('/quizzes/edit/<int:set_id>', methods=['GET', 'POST'])
@login_required
def edit_quiz_set(set_id):
    """
    Chỉnh sửa thông tin bộ câu hỏi.
    Chỉ creator_user_id hoặc người dùng được cấp quyền 'editor' mới có thể chỉnh sửa.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role != 'admin' and \
       quiz_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền chỉnh sửa bộ câu hỏi này.'}), 403
        else:
            abort(403)

    form = QuizSetForm(obj=quiz_set)
    if form.validate_on_submit():
        current_app.logger.info(f"edit_quiz_set: Form đã được gửi và xác thực thành công cho set ID: {set_id}")
        flash_message = ''
        flash_category = ''
        temp_filepath = None

        try:
            quiz_set.title = form.title.data
            quiz_set.description = form.description.data
            quiz_set.tags = form.tags.data
            quiz_set.is_public = form.is_public.data
            quiz_set.ai_settings = {'custom_prompt': form.ai_prompt.data} if form.ai_prompt.data else None

            # Xử lý file Excel nếu có (chỉ khi chỉnh sửa, sẽ xóa cũ và thêm mới các item)
            if form.excel_file.data and form.excel_file.data.filename != '':
                current_app.logger.info(f"edit_quiz_set: Phát hiện file Excel: {form.excel_file.data.filename}")
                excel_file = form.excel_file.data
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                    excel_file.save(tmp_file.name)
                    temp_filepath = tmp_file.name
                current_app.logger.info(f"edit_quiz_set: Đã lưu file tạm thời tại: {temp_filepath}")

                df = pd.read_excel(temp_filepath)
                current_app.logger.info(f"edit_quiz_set: Đã đọc file Excel. Số hàng: {len(df)}. Cột: {df.columns.tolist()}")
                
                required_basic_cols = ['option_a', 'option_b', 'correct_answer_text']
                
                if not all(col in df.columns for col in required_basic_cols):
                    missing_cols = [col for col in required_basic_cols if col not in df.columns]
                    raise ValueError(f"File Excel phải có các cột bắt buộc: {', '.join(required_basic_cols)}. Thiếu: {', '.join(missing_cols)}")
                current_app.logger.info("edit_quiz_set: Các cột bắt buộc cơ bản đã được tìm thấy.")

                # Xóa tất cả các câu hỏi cũ của bộ này trước khi thêm mới từ Excel
                LearningItem.query.filter_by(container_id=set_id, item_type='QUIZ_MCQ').delete()
                db.session.flush()
                current_app.logger.info(f"edit_quiz_set: Đã xóa tất cả câu hỏi cũ cho set ID: {set_id}")

                items_added_count = 0
                for index, row in df.iterrows():
                    # Khởi tạo các biến tùy chọn để tránh lỗi "not defined"
                    question_text = ''
                    question_image_file = ''
                    question_audio_file = ''

                    question_text = str(row['question']) if 'question' in df.columns and pd.notna(row['question']) else ''
                    option_a = str(row['option_a']) if pd.notna(row['option_a']) else ''
                    option_b = str(row['option_b']) if pd.notna(row['option_b']) else ''
                    correct_answer = str(row['correct_answer_text']) if pd.notna(row['correct_answer_text']) else ''
                    question_image_file = str(row['question_image_file']) if 'question_image_file' in df.columns and pd.notna(row['question_image_file']) else ''
                    question_audio_file = str(row['question_audio_file']) if 'question_audio_file' in df.columns and pd.notna(row['question_audio_file']) else ''


                    is_question_content_present = bool(question_text) or bool(question_image_file) or bool(question_audio_file)

                    if is_question_content_present and option_a and option_b and correct_answer:
                        item_content = {
                            'question': question_text,
                            'options': {
                                'A': option_a,
                                'B': option_b,
                                'C': str(row['option_c']) if 'option_c' in df.columns and pd.notna(row['option_c']) else None,
                                'D': str(row['option_d']) if 'option_d' in df.columns and pd.notna(row['option_d']) else None
                            },
                            'correct_answer': correct_answer,
                            'pre_question_text': str(row['pre_question_text']) if 'pre_question_text' in df.columns and pd.notna(row['pre_question_text']) else None,
                            'explanation': str(row['guidance']) if 'guidance' in df.columns and pd.notna(row['guidance']) else None,
                            'question_image_file': question_image_file if question_image_file else None,
                            'question_audio_file': question_audio_file if question_audio_file else None,
                            'passage_text': str(row['passage_text']) if 'passage_text' in df.columns and pd.notna(row['passage_text']) else None,
                            'passage_order': str(row['passage_order']) if 'passage_order' in df.columns and pd.notna(row['passage_order']) else None,
                        }
                        new_item = LearningItem(
                            container_id=set_id,
                            item_type='QUIZ_MCQ',
                            content=item_content,
                            order_in_container=index + 1
                        )
                        db.session.add(new_item)
                        items_added_count += 1
                        current_app.logger.info(f"edit_quiz_set: Đã thêm câu hỏi từ hàng {index + 1}: Question: '{question_text[:50]}', Image: '{question_image_file}', Audio: '{question_audio_file}'")
                    else:
                        current_app.logger.warning(f"edit_quiz_set: Bỏ qua hàng {index + 1} do thiếu nội dung bắt buộc (Câu hỏi, Lựa chọn A, Lựa chọn B, hoặc Đáp án đúng).")
                
                flash_message = f'Bộ câu hỏi và {items_added_count} câu hỏi từ Excel đã được cập nhật thành công!'
                flash_category = 'success'

            else: # Không có file Excel được tải lên, chỉ cập nhật thông tin bộ câu hỏi
                current_app.logger.info("edit_quiz_set: Không có file Excel được tải lên, chỉ cập nhật thông tin bộ.")
                flash_message = 'Bộ câu hỏi đã được cập nhật thành công!'
                flash_category = 'success'

            db.session.commit()
            current_app.logger.info("edit_quiz_set: Commit database thành công.")

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"edit_quiz_set: Lỗi trong quá trình xử lý file Excel hoặc cập nhật bộ câu hỏi: {str(e)}", exc_info=True)
            flash_message = f'Lỗi khi xử lý file Excel hoặc cập nhật bộ câu hỏi: {str(e)}'
            flash_category = 'danger'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': flash_message}), 400
            else:
                flash(flash_message, flash_category)
                return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                os.remove(temp_filepath)
                current_app.logger.info(f"edit_quiz_set: Đã xóa file tạm thời: {temp_filepath}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': flash_message})
        else:
            flash(flash_message, flash_category)
            return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
    
    if form.errors:
        current_app.logger.warning(f"edit_quiz_set: Form không hợp lệ. Lỗi: {form.errors}")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_set_bare.html', form=form, title='Sửa Bộ câu hỏi', quiz_set=quiz_set)
    return render_template('add_edit_quiz_set.html', form=form, title='Sửa Bộ câu hỏi', quiz_set=quiz_set)

@quizzes_bp.route('/quizzes/delete/<int:set_id>', methods=['POST'])
@login_required
def delete_quiz_set(set_id):
    """
    Xóa một bộ câu hỏi.
    Chỉ creator_user_id hoặc admin mới có thể xóa bộ câu hỏi.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role != 'admin' and quiz_set.creator_user_id != current_user.user_id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền xóa bộ câu hỏi này.'}), 403
        else:
            flash('Bạn không có quyền xóa bộ câu hỏi này.', 'danger')
            abort(403)
    
    db.session.delete(quiz_set)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Bộ câu hỏi đã được xóa thành công!'})
    else:
        flash('Bộ câu hỏi đã được xóa thành công!', 'success')
        return redirect(url_for('content_management.content_dashboard', tab='quizzes'))

@quizzes_bp.route('/quizzes/<int:set_id>/items')
@login_required
def list_quiz_items(set_id):
    """
    Hiển thị danh sách các câu hỏi thuộc một bộ câu hỏi cụ thể.
    Người dùng cần có quyền xem bộ câu hỏi đó.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)

    if not quiz_set.is_public and \
       current_user.user_role != 'admin' and \
       quiz_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id).first():
        abort(403)

    quiz_items = LearningItem.query.filter_by(
        container_id=quiz_set.container_id,
        item_type='QUIZ_MCQ'
    ).order_by(LearningItem.order_in_container).all()

    can_edit = False
    if current_user.user_role == 'admin' or \
       quiz_set.creator_user_id == current_user.user_id or \
       ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        can_edit = True

    return render_template('quiz_items.html', quiz_set=quiz_set, quiz_items=quiz_items, can_edit=can_edit)

@quizzes_bp.route('/quizzes/<int:set_id>/items/add', methods=['GET', 'POST'])
@login_required
def add_quiz_item(set_id):
    """
    Thêm câu hỏi mới vào một bộ câu hỏi.
    Chỉ người tạo bộ câu hỏi hoặc người dùng được cấp quyền 'editor' mới có thể thêm.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)

    if current_user.user_role != 'admin' and \
       quiz_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền thêm câu hỏi vào bộ này.'}), 403
        else:
            abort(403)

    form = QuizItemForm()
    if form.validate_on_submit():
        max_order = db.session.query(db.func.max(LearningItem.order_in_container)).filter_by(
            container_id=set_id,
            item_type='QUIZ_MCQ'
        ).scalar()
        new_order = (max_order or 0) + 1

        new_item = LearningItem(
            container_id=set_id,
            item_type='QUIZ_MCQ',
            content={
                'question': form.question.data,
                'options': {
                    'A': form.option_a.data,
                    'B': form.option_b.data,
                    'C': form.option_c.data if form.option_c.data else None,
                    'D': form.option_d.data if form.option_d.data else None
                },
                'correct_answer': form.correct_answer_text.data,
                'pre_question_text': form.pre_question_text.data if form.pre_question_text.data else None,
                'explanation': form.guidance.data if form.guidance.data else None,
                'question_image_file': form.question_image_file.data if form.question_image_file.data else None,
                'question_audio_file': form.question_audio_file.data if form.question_audio_file.data else None,
                'passage_text': form.passage_text.data if form.passage_text.data else None,
                'passage_order': form.passage_order.data if form.passage_order.data else None,
            },
            order_in_container=new_order
        )
        db.session.add(new_item)
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Câu hỏi mới đã được thêm thành công!'})
        else:
            flash('Câu hỏi mới đã được thêm thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_item_bare.html', form=form, quiz_set=quiz_set, title='Thêm Câu hỏi')
    return render_template('add_edit_quiz_item.html', form=form, quiz_set=quiz_set, title='Thêm Câu hỏi')

@quizzes_bp.route('/quizzes/<int:set_id>/items/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_quiz_item(set_id, item_id):
    """
    Chỉnh sửa một câu hỏi cụ thể trong bộ câu hỏi.
    Chỉ người tạo bộ câu hỏi hoặc người dùng được cấp quyền 'editor' mới có thể chỉnh sửa.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    quiz_item = LearningItem.query.get_or_404(item_id)

    if current_user.user_role != 'admin' and \
       quiz_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền chỉnh sửa câu hỏi này.'}), 403
        else:
            abort(403)

    form = QuizItemForm(
        question=quiz_item.content.get('question', ''),
        pre_question_text=quiz_item.content.get('pre_question_text', ''),
        option_a=quiz_item.content.get('options', {}).get('A', ''),
        option_b=quiz_item.content.get('options', {}).get('B', ''),
        option_c=quiz_item.content.get('options', {}).get('C', ''),
        option_d=quiz_item.content.get('options', {}).get('D', ''),
        correct_answer_text=quiz_item.content.get('correct_answer', ''),
        guidance=quiz_item.content.get('explanation', ''),
        question_image_file=quiz_item.content.get('question_image_file', ''),
        question_audio_file=quiz_item.content.get('question_audio_file', ''),
        passage_text=quiz_item.content.get('passage_text', ''),
        passage_order=quiz_item.content.get('passage_order', '')
    )
    
    if form.validate_on_submit():
        quiz_item.content = {
            'question': form.question.data,
            'options': {
                'A': form.option_a.data,
                'B': form.option_b.data,
                'C': form.option_c.data if form.option_c.data else None,
                'D': form.option_d.data if form.option_d.data else None
            },
            'correct_answer': form.correct_answer_text.data,
            'pre_question_text': form.pre_question_text.data if form.pre_question_text.data else None,
            'explanation': form.guidance.data if form.guidance.data else None,
            'question_image_file': form.question_image_file.data if form.question_image_file.data else None,
            'question_audio_file': form.question_audio_file.data if form.question_audio_file.data else None,
            'passage_text': form.passage_text.data if form.passage_text.data else None,
            'passage_order': form.passage_order.data if form.passage_order.data else None,
        }
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Câu hỏi đã được cập nhật thành công!'})
        else:
            flash('Câu hỏi đã được cập nhật thành công!', 'success')
            return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        return jsonify({'success': False, 'errors': form.errors}), 400

    if request.method == 'GET' and request.args.get('is_modal') == 'true':
        return render_template('_add_edit_quiz_item_bare.html', form=form, quiz_set=quiz_set, quiz_item=quiz_item, title='Chỉnh sửa Câu hỏi')
    return render_template('add_edit_quiz_item.html', form=form, quiz_set=quiz_set, quiz_item=quiz_item, title='Chỉnh sửa Câu hỏi')

@quizzes_bp.route('/quizzes/<int:set_id>/items/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_quiz_item(set_id, item_id):
    """
    Xóa một câu hỏi cụ thể trong bộ câu hỏi.
    Chỉ người tạo bộ câu hỏi hoặc người dùng được cấp quyền 'editor' mới có thể xóa.
    """
    quiz_set = LearningContainer.query.get_or_404(set_id)
    quiz_item = LearningItem.query.get_or_404(item_id)

    if current_user.user_role != 'admin' and \
       quiz_set.creator_user_id != current_user.user_id and \
       not ContainerContributor.query.filter_by(container_id=set_id, user_id=current_user.user_id, permission_level='editor').first():
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Bạn không có quyền xóa câu hỏi này.'}), 403
        else:
            flash('Bạn không có quyền xóa câu hỏi này.', 'danger')
            abort(403)
    
    db.session.delete(quiz_item)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Câu hỏi đã được xóa thành công!'})
    else:
        flash('Câu hỏi đã được xóa thành công!', 'success')
        return redirect(url_for('content_management.content_dashboard', tab='quizzes'))
