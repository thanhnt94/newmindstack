# File: Mindstack/web/mindstack_app/modules/admin/content_management/quizzes/routes.py
# Version: 1.1 - Đã sửa lỗi "row is not defined" trong add/edit item
# Mục đích: Xử lý các yêu cầu liên quan đến việc tạo, sửa, xóa bộ và câu hỏi Quiz (cho admin).

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import json
import pandas as pd # Cần cài đặt: pip install pandas openpyxl

# Import Blueprint từ __init__.py của module này
from . import admin_quizzes_bp 

# Import các model và db instance từ cấp trên (đi lên 4 cấp)
from .....models import LearningContainer, LearningItem, User, SystemSetting
from .....db_instance import db
# Tái sử dụng forms từ my_content/quizzes
from ....my_content.quizzes.forms import QuizSetForm, QuizItemForm

# Cấu hình thư mục upload (tương tự như my_content/quizzes)
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', '..', '..', 'static', 'uploads')
ALLOWED_EXTENSIONS = {'xlsx'}

# Đảm bảo thư mục upload tồn tại
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Middleware để đảm bảo người dùng đã đăng nhập và có quyền admin
@admin_quizzes_bp.before_request
@login_required 
def admin_quiz_required():
    if not current_user.is_authenticated or current_user.user_role != 'admin':
        flash('Bạn không có quyền truy cập khu vực quản lý Quiz của admin.', 'danger')
        abort(403) 

# --- ROUTES QUẢN LÝ BỘ QUIZ (LearningContainer) ---
# Admin có thể xem TẤT CẢ các bộ Quiz, không chỉ của mình
@admin_quizzes_bp.route('/')
@admin_quizzes_bp.route('/sets')
def list_admin_quiz_sets():
    quiz_sets = LearningContainer.query.filter_by(
        container_type='QUIZ_SET'
    ).all()
    # Lấy thông tin người tạo để hiển thị trong bảng
    users = User.query.all()
    user_map = {user.user_id: user.username for user in users}
    return render_template('admin_quiz_sets.html', quiz_sets=quiz_sets, user_map=user_map)

@admin_quizzes_bp.route('/sets/add', methods=['GET', 'POST'])
def add_admin_quiz_set():
    form = QuizSetForm()
    # Admin có thể gán bộ Quiz cho người dùng khác
    # Thêm trường để chọn creator_user_id vào form nếu muốn admin gán
    # For simplicity, let's assume admin creates for themselves or a default user for now
    # Or we can add a SelectField for creator_user_id if needed.
    
    # Lấy danh sách người dùng để admin có thể chọn người tạo
    users = User.query.all()
    # form.creator = SelectField('Người tạo', choices=[(str(u.user_id), u.username) for u in users], validators=[DataRequired()])

    if form.validate_on_submit():
        ai_settings = {}
        if form.ai_prompt.data:
            ai_settings['custom_prompt'] = form.ai_prompt.data

        # Admin tạo bộ Quiz, mặc định là admin là người tạo, hoặc có thể chọn từ form
        creator_id = current_user.user_id # Mặc định admin là người tạo
        # if hasattr(form, 'creator') and form.creator.data:
        #     creator_id = int(form.creator.data)

        # Xử lý upload file Excel
        if form.excel_file.data and allowed_file(form.excel_file.data.filename):
            filename = secure_filename(form.excel_file.data.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            form.excel_file.data.save(filepath)

            try:
                df = pd.read_excel(filepath)
                required_cols = ['question', 'option_a', 'option_b', 'correct_answer_text']
                if not all(col in df.columns for col in required_cols):
                    flash('File Excel phải có ít nhất các cột "question", "option_a", "option_b", "correct_answer_text".', 'danger')
                    os.remove(filepath)
                    return render_template('add_edit_admin_quiz_set.html', form=form, title='Thêm Bộ Quiz mới (Admin)')

                new_set = LearningContainer(
                    creator_user_id=creator_id,
                    container_type='QUIZ_SET',
                    title=form.title.data,
                    description=form.description.data,
                    tags=form.tags.data,
                    is_public=form.is_public.data,
                    ai_settings=ai_settings if ai_settings else None
                )
                db.session.add(new_set)
                db.session.flush() 

                for index, row in df.iterrows():
                    item_content = {
                        "pre_question_text": str(row['pre_question_text']) if 'pre_question_text' in row else None,
                        "question": str(row['question']) if 'question' in row else '',
                        "option_a": str(row['option_a']) if 'option_a' in row else '',
                        "option_b": str(row['option_b']) if 'option_b' in row else '',
                        "option_c": str(row['option_c']) if 'option_c' in row else None,
                        "option_d": str(row['option_d']) if 'option_d' in row else None,
                        "correct_answer_text": str(row['correct_answer_text']) if 'correct_answer_text' in row else '',
                        "guidance": str(row['guidance']) if 'guidance' in row else None,
                        "question_image_file": str(row['question_image_file']) if 'question_image_file' in row else None,
                        "question_audio_file": str(row['question_audio_file']) if 'question_audio_file' in row else None,
                        "passage_text": str(row['passage_text']) if 'passage_text' in row else None,
                        "passage_order": str(row['passage_order']) if 'passage_order' in row else None,
                        "ai_prompt": str(row['ai_prompt']) if 'ai_prompt' in row else None
                    }
                    ai_explanation_data = str(row['ai_explanation']) if 'ai_explanation' in row else None

                    new_item = LearningItem(
                        container_id=new_set.container_id,
                        item_type='QUIZ_MCQ',
                        content=item_content,
                        order_in_container=index,
                        ai_explanation=ai_explanation_data if ai_explanation_data != 'None' else None
                    )
                    db.session.add(new_item)
                
                db.session.commit()
                flash('Bộ Quiz và các câu hỏi đã được thêm thành công từ file Excel (Admin)!', 'success')
                os.remove(filepath)
                return redirect(url_for('admin_quizzes.list_admin_quiz_sets'))

            except Exception as e:
                db.session.rollback()
                flash(f'Lỗi khi xử lý file Excel (Admin): {e}', 'danger')
                os.remove(filepath)
                return render_template('add_edit_admin_quiz_set.html', form=form, title='Thêm Bộ Quiz mới (Admin)')
        
        else: # Không có file Excel hoặc file không hợp lệ, chỉ tạo bộ Quiz rỗng
            new_set = LearningContainer(
                creator_user_id=creator_id,
                container_type='QUIZ_SET',
                title=form.title.data,
                description=form.description.data,
                tags=form.tags.data,
                is_public=form.is_public.data,
                ai_settings=ai_settings if ai_settings else None
            )
            db.session.add(new_set)
            db.session.commit()
            flash('Bộ Quiz đã được thêm thành công (Admin)!', 'success')
            return redirect(url_for('admin_quizzes.list_admin_quiz_sets'))
            
    return render_template('add_edit_admin_quiz_set.html', form=form, title='Thêm Bộ Quiz mới (Admin)')

@admin_quizzes_bp.route('/sets/edit/<int:set_id>', methods=['GET', 'POST'])
def edit_admin_quiz_set(set_id):
    quiz_set = LearningContainer.query.get_or_404(set_id)

    form = QuizSetForm(obj=quiz_set)
    # Lấy danh sách người dùng để admin có thể chọn người tạo
    users = User.query.all()
    # form.creator = SelectField('Người tạo', choices=[(str(u.user_id), u.username) for u in users], validators=[DataRequired()])

    # Điền dữ liệu AI prompt và creator vào form khi GET request
    if request.method == 'GET':
        if quiz_set.ai_settings and 'custom_prompt' in quiz_set.ai_settings:
            form.ai_prompt.data = quiz_set.ai_settings['custom_prompt']
        # if hasattr(form, 'creator'):
        #     form.creator.data = str(quiz_set.creator_user_id)

    if form.validate_on_submit():
        ai_settings = {}
        if form.ai_prompt.data:
            ai_settings['custom_prompt'] = form.ai_prompt.data
        
        quiz_set.title = form.title.data
        quiz_set.description = form.description.data
        quiz_set.tags = form.tags.data
        quiz_set.is_public = form.is_public.data
        quiz_set.ai_settings = ai_settings if ai_settings else None
        # if hasattr(form, 'creator'):
        #     quiz_set.creator_user_id = int(form.creator.data)

        # Xử lý upload file Excel (nếu có file mới, sẽ cập nhật các câu hỏi hiện có hoặc thêm mới)
        if form.excel_file.data and allowed_file(form.excel_file.data.filename):
            filename = secure_filename(form.excel_file.data.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            form.excel_file.data.save(filepath)

            try:
                df = pd.read_excel(filepath)
                required_cols = ['question', 'option_a', 'option_b', 'correct_answer_text']
                if not all(col in df.columns for col in required_cols):
                    flash('File Excel phải có ít nhất các cột "question", "option_a", "option_b", "correct_answer_text".', 'danger')
                    os.remove(filepath)
                    return render_template('add_edit_admin_quiz_set.html', form=form, title='Sửa Bộ Quiz (Admin)', quiz_set=quiz_set)

                # Xóa tất cả các câu hỏi hiện có trong bộ này trước khi thêm câu hỏi mới từ Excel
                LearningItem.query.filter_by(container_id=quiz_set.container_id).delete()
                db.session.flush()

                for index, row in df.iterrows():
                    item_content = {
                        "pre_question_text": str(row['pre_question_text']) if 'pre_question_text' in row else None,
                        "question": str(row['question']) if 'question' in row else '',
                        "option_a": str(row['option_a']) if 'option_a' in row else '',
                        "option_b": str(row['option_b']) if 'option_b' in row else '',
                        "option_c": str(row['option_c']) if 'option_c' in row else None,
                        "option_d": str(row['option_d']) if 'option_d' in row else None,
                        "correct_answer_text": str(row['correct_answer_text']) if 'correct_answer_text' in row else '',
                        "guidance": str(row['guidance']) if 'guidance' in row else None,
                        "question_image_file": str(row['question_image_file']) if 'question_image_file' in row else None,
                        "question_audio_file": str(row['question_audio_file']) if 'question_audio_file' in row else None,
                        "passage_text": str(row['passage_text']) if 'passage_text' in row else None,
                        "passage_order": str(row['passage_order']) if 'passage_order' in row else None,
                        "ai_prompt": str(row['ai_prompt']) if 'ai_prompt' in row else None
                    }
                    ai_explanation_data = str(row['ai_explanation']) if 'ai_explanation' in row else None

                    new_item = LearningItem(
                        container_id=quiz_set.container_id,
                        item_type='QUIZ_MCQ',
                        content=item_content,
                        order_in_container=index,
                        ai_explanation=ai_explanation_data if ai_explanation_data != 'None' else None
                    )
                    db.session.add(new_item)
                
                db.session.commit()
                flash('Bộ Quiz và các câu hỏi đã được cập nhật từ file Excel (Admin)!', 'success')
                os.remove(filepath)
                return redirect(url_for('admin_quizzes.list_admin_quiz_sets'))

            except Exception as e:
                db.session.rollback()
                flash(f'Lỗi khi xử lý file Excel (Admin): {e}', 'danger')
                os.remove(filepath)
                return render_template('add_edit_admin_quiz_set.html', form=form, title='Sửa Bộ Quiz (Admin)', quiz_set=quiz_set)
        
        else: # Không có file Excel mới, chỉ cập nhật thông tin bộ Quiz
            db.session.commit()
            flash('Thông tin bộ Quiz đã được cập nhật (Admin)!', 'success')
            return redirect(url_for('admin_quizzes.list_admin_quiz_sets'))

    return render_template('add_edit_admin_quiz_set.html', form=form, title='Sửa Bộ Quiz (Admin)', quiz_set=quiz_set)

@admin_quizzes_bp.route('/sets/delete/<int:set_id>', methods=['POST'])
def delete_admin_quiz_set(set_id):
    quiz_set = LearningContainer.query.get_or_404(set_id)
    
    # Admin có quyền xóa bất kỳ bộ Quiz nào
    # if quiz_set.creator_user_id != current_user.user_id: # Không cần kiểm tra này cho admin
    #    flash('Bạn không có quyền xóa bộ Quiz này.', 'danger')
    #    abort(403)
    
    # Xóa tất cả các câu hỏi con trước
    LearningItem.query.filter_by(container_id=set_id).delete()
    db.session.delete(quiz_set)
    db.session.commit()
    flash('Bộ Quiz đã được xóa thành công (Admin)!', 'success')
    return redirect(url_for('admin_quizzes.list_admin_quiz_sets'))

# --- ROUTES QUẢN LÝ CÂU HỎI QUIZ (LearningItem) TRONG BỘ ---
# Admin có thể xem TẤT CẢ các câu hỏi trong bộ, không chỉ của mình
@admin_quizzes_bp.route('/sets/<int:set_id>/items')
def list_admin_quiz_items(set_id):
    quiz_set = LearningContainer.query.get_or_404(set_id)
    # Admin có quyền xem bộ Quiz này
    # if quiz_set.creator_user_id != current_user.user_id: # Không cần kiểm tra này cho admin
    #    flash('Bạn không có quyền xem bộ Quiz này.', 'danger')
    #    abort(403)
    
    quiz_items = LearningItem.query.filter_by(
        container_id=set_id,
        item_type='QUIZ_MCQ' # Hoặc các loại quiz khác
    ).order_by(LearningItem.order_in_container).all() 

    return render_template('admin_quiz_items.html', quiz_set=quiz_set, quiz_items=quiz_items)

@admin_quizzes_bp.route('/sets/<int:set_id>/items/add', methods=['GET', 'POST'])
def add_admin_quiz_item(set_id):
    quiz_set = LearningContainer.query.get_or_404(set_id)
    # Admin có quyền thêm câu hỏi vào bộ Quiz này
    # if quiz_set.creator_user_id != current_user.user_id: # Không cần kiểm tra này cho admin
    #    flash('Bạn không có quyền thêm câu hỏi vào bộ Quiz này.', 'danger')
    #    abort(403)

    form = QuizItemForm()
    if form.validate_on_submit():
        item_content = {
            "pre_question_text": form.pre_question_text.data if form.pre_question_text.data else None,
            "question": form.question.data,
            "option_a": form.option_a.data,
            "option_b": form.option_b.data,
            "option_c": form.option_c.data if form.option_c.data else None,
            "option_d": form.option_d.data if form.option_d.data else None,
            "correct_answer_text": form.correct_answer_text.data,
            "guidance": form.guidance.data if form.guidance.data else None,
            "question_image_file": form.question_image_file.data if form.question_image_file.data else None,
            "question_audio_file": form.question_audio_file.data if form.question_audio_file.data else None,
            "passage_text": form.passage_text.data if form.passage_text.data else None,
            "passage_order": form.passage_order.data if form.passage_order.data else None,
            # FIXED: Use form.ai_prompt.data instead of row['ai_prompt']
            "ai_prompt": form.ai_prompt.data if form.ai_prompt.data else None
        }
        # FIXED: ai_explanation_data should come from form, not row
        ai_explanation_data = form.ai_explanation.data if form.ai_explanation.data else None

        new_item = LearningItem(
            container_id=set_id,
            item_type='QUIZ_MCQ', # Loại câu hỏi trắc nghiệm
            content=item_content,
            order_in_container=LearningItem.query.filter_by(container_id=set_id).count() 
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Câu hỏi Quiz đã được thêm thành công (Admin)!', 'success')
        return redirect(url_for('admin_quizzes.list_admin_quiz_items', set_id=set_id))
    
    return render_template('add_edit_admin_quiz_item.html', form=form, title='Thêm Câu hỏi Quiz mới (Admin)', quiz_set=quiz_set)

@admin_quizzes_bp.route('/sets/<int:set_id>/items/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_admin_quiz_item(set_id, item_id):
    quiz_set = LearningContainer.query.get_or_404(set_id)
    quiz_item = LearningItem.query.get_or_404(item_id)

    # Đảm bảo câu hỏi thuộc bộ Quiz
    if quiz_item.container_id != set_id:
        flash('Câu hỏi không thuộc bộ Quiz này.', 'danger')
        abort(403)
    # Admin có quyền chỉnh sửa câu hỏi này
    # if quiz_set.creator_user_id != current_user.user_id: # Không cần kiểm tra này cho admin
    #    flash('Bạn không có quyền chỉnh sửa câu hỏi này.', 'danger')
    #    abort(403)

    form = QuizItemForm(obj=quiz_item)
    
    # Điền dữ liệu từ JSON content vào form khi GET request
    if request.method == 'GET':
        if quiz_item.content:
            form.pre_question_text.data = quiz_item.content.get('pre_question_text', '')
            form.question.data = quiz_item.content.get('question', '')
            form.option_a.data = quiz_item.content.get('option_a', '')
            form.option_b.data = quiz_item.content.get('option_b', '')
            form.option_c.data = quiz_item.content.get('option_c', '')
            form.option_d.data = quiz_item.content.get('option_d', '')
            form.correct_answer_text.data = quiz_item.content.get('correct_answer_text', '')
            form.guidance.data = quiz_item.content.get('guidance', '')
            form.question_image_file.data = quiz_item.content.get('question_image_file', '')
            form.question_audio_file.data = quiz_item.content.get('question_audio_file', '')
            form.passage_text.data = quiz_item.content.get('passage_text', '')
            form.passage_order.data = quiz_item.content.get('passage_order', '')
            form.ai_explanation.data = quiz_item.ai_explanation # Điền dữ liệu giải thích AI

    if form.validate_on_submit():
        # Cập nhật dữ liệu vào JSON content
        quiz_item.content['pre_question_text'] = form.pre_question_text.data if form.pre_question_text.data else None
        quiz_item.content['question'] = form.question.data
        quiz_item.content['option_a'] = form.option_a.data
        quiz_item.content['option_b'] = form.option_b.data
        quiz_item.content['option_c'] = form.option_c.data if form.option_c.data else None
        quiz_item.content['option_d'] = form.option_d.data if form.option_d.data else None
        quiz_item.content['correct_answer_text'] = form.correct_answer_text.data
        quiz_item.content['guidance'] = form.guidance.data if form.guidance.data else None
        quiz_item.content['question_image_file'] = form.question_image_file.data if form.question_image_file.data else None
        quiz_item.content['question_audio_file'] = form.question_audio_file.data if form.question_audio_file.data else None
        quiz_item.content['passage_text'] = form.passage_text.data if form.passage_text.data else None
        quiz_item.content['passage_order'] = form.passage_order.data if form.passage_order.data else None
        # FIXED: Use form.ai_prompt.data instead of row['ai_prompt']
        quiz_item.content['ai_prompt'] = form.ai_prompt.data if form.ai_prompt.data else None
        
        # ai_explanation không được sửa trực tiếp qua form này
        # quiz_item.ai_explanation = form.ai_explanation.data # KHÔNG NÊN LÀM VẬY NẾU CHỈ ĐỂ HIỂN THỊ

        db.session.commit()
        flash('Câu hỏi Quiz đã được cập nhật thành công (Admin)!', 'success')
        return redirect(url_for('admin_quizzes.list_admin_quiz_items', set_id=set_id))

    return render_template('add_edit_admin_quiz_item.html', form=form, title='Sửa Câu hỏi Quiz (Admin)', quiz_set=quiz_set, quiz_item=quiz_item)

@admin_quizzes_bp.route('/sets/<int:set_id>/items/delete/<int:item_id>', methods=['POST'])
def delete_admin_quiz_item(set_id, item_id):
    quiz_set = LearningContainer.query.get_or_404(set_id)
    quiz_item = LearningItem.query.get_or_404(item_id)

    if quiz_item.container_id != set_id:
        flash('Câu hỏi không thuộc bộ Quiz này.', 'danger')
        abort(403)
    # Admin có quyền xóa câu hỏi này
    # if quiz_set.creator_user_id != current_user.user_id: # Không cần kiểm tra này cho admin
    #    flash('Bạn không có quyền xóa câu hỏi này.', 'danger')
    #    abort(403)
    
    db.session.delete(quiz_item)
    db.session.commit()
    flash('Câu hỏi Quiz đã được xóa thành công (Admin)!', 'success')
    return redirect(url_for('admin_quizzes.list_admin_quiz_items', set_id=set_id))
